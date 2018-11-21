
from lib.iq_mixer_calibration import *
from lib.data_management import *

from lib2.fulaut.AnticrossingOracle import *
from lib2.fulaut.SpectrumOracle import *
from lib2.fulaut.ResonatorOracle import *
from lib2.fulaut.STSRunner import *
from lib2.fulaut.TTSRunner import *
from lib2.DispersiveRabiOscillations import DispersiveRabiOscillations
from lib2.DispersiveRamsey import DispersiveRamsey
from lib2.DispersiveDecay import DispersiveDecay
from lib2.MeasurementResult import *
from lib2.SingleToneSpectroscopy import *
from lib2.TwoToneSpectroscopy import *
from lib2.fulaut.qubit_spectra import transmon_spectrum
from lib2.LoggingServer import LoggingServer

from drivers.Tektronix_AWG5014 import *
from drivers.IQAWG import *

import pickle

from time import sleep

class MeasurementRunner():

    def __init__(self, sample_name, s_parameter):
        self._sample_name = sample_name
        self._s_parameter = s_parameter
        self._qubit_names = "I II III IV V VI".split(" ")
        self._res_limits = {}
        self._sts_runners = {}
        self._sts_fit_params = {}
        self._tts_runners = {}
        self._tts_results = {}
        self._tts_fit_params = {}
        self._exact_qubit_freqs = {}
        self._dro_results = {}
        self._dr_results = {}
        self._dd_results = {}

        self._ramsey_offset = 5e3
        # self._vna = Znb("ZNB")
        # self._exa = Agilent_EXA_N9010A("EXA")
        m = Measurement("", "", {"vna":"vna4", "sa":"exa",
                                 "exc_lo":"psg2", "cur_src":"yok6"})
        self._vna = m._vna
        self._sa = m._sa
        self._exc_lo = m._exc_lo
        self._cur_src = m._cur_src
        self._cur_src.set_status(1)

        self._awg = awg = Tektronix_AWG5014("TEK1")
        self._ro_awg = IQAWG(AWGChannel(awg, 3), AWGChannel(awg, 4))
        self._q_awg = IQAWG(AWGChannel(awg, 1), AWGChannel(awg, 2))
        self._launch_date = datetime.today()

        self._logger = LoggingServer.getInstance()

    def run(self, qubits_to_measure = [0,1,2,3,4,5]):

        self._logger.debug("Started measurement for qubits ##:"+str(qubits_to_measure))

        self._open_only_readout_mixer()

        ro = ResonatorOracle(self._vna, self._s_parameter, 3e6)
        scan_areas = ro.launch()[:6]

        for idx, res_limits in enumerate(scan_areas):
            if idx not in qubits_to_measure:
                continue

            qubit_name = self._qubit_names[idx]
            self._res_limits[qubit_name] = res_limits

            if qubit_name not in self._sts_fit_params.keys():

                STSR = STSRunner(self._sample_name,
                                 qubit_name,
                                 mean(res_limits),
                                 awgs =  {"q_awg":self._q_awg,
                                          "ro_awg":self._ro_awg})

                self._sts_runners[qubit_name] = STSR
                self._sts_fit_params[qubit_name], loss = STSR.run()

            if qubit_name not in self._tts_fit_params.keys():

                TTSR = TTSRunner(self._sample_name,
                                 qubit_name,
                                 STSR.get_scan_area(),
                                 self._sts_fit_params[qubit_name],
                                 awgs =  {"q_awg":self._q_awg,
                                          "ro_awg":self._ro_awg})
                self._tts_runners[qubit_name] = TTSR
                self._tts_fit_params[qubit_name] = TTSR.run()

            self._exact_qubit_freqs[qubit_name] = self._tts_fit_params[qubit_name][2]
            self._ro_cal = self._calibrate_readout(qubit_name)
            self._exc_cal = self._calibrate_excitation(qubit_name)

            q_freq = transmon_spectrum(*self._tts_fit_params[qubit_name])
            self._cur_src.set_current(self._tts_fit_params[qubit_name][1])


            self._perform_Rabi_oscillations(qubit_name)

            self._max_ramsey_delay = .5e3
            self._ramsey_offset = 5e6
            self._ramsey_nop = 201

            self._perform_Ramsey_oscillations(qubit_name)
            detected_ramsey_freq =\
                self._dr_results[qubit_name].get_ramsey_frequency()
            frequency_error = self._ramsey_offset - detected_ramsey_freq
            self._exact_qubit_freqs[qubit_name] -= frequency_error
            self._ramsey_offset = 0.5e6
            self._max_ramsey_delay = 1e4
            self._ramsey_nop = 201


            self._perform_Rabi_oscillations(qubit_name, True)
            self._perform_Ramsey_oscillations(qubit_name, True)
            self._perform_decay(qubit_name, True)


    def _perform_decay(self, qubit_name, save = False):

        DD = DispersiveDecay("%s-decay"%qubit_name,
                              self._sample_name,
                              vna="vna4",
                              ro_awg=self._ro_awg,
                              q_awg=self._q_awg,
                              q_lo='psg2')

        vna_parameters= {"bandwidth":10,
                         "freq_limits":self._res_limits[qubit_name],
                         "nop":100,
                         "averages":1}


        raadout_delays = linspace(0, 50000, 101)
        exc_frequency = self._exact_qubit_freqs[qubit_name]
        pi_pulse_duration =\
            self._dro_results[qubit_name].get_pi_pulse_duration()*1e3

        pulse_sequence_parameters = {"awg_trigger_reaction_delay":0,
                                     "readout_duration":5000,
                                     "repetition_period":100000,
                                     "pi_pulse_duration":pi_pulse_duration}

        ro_awg_params =  {"calibration":self._ro_cal}
        q_awg_params = {"calibration":self._exc_cal}

        DD.set_fixed_parameters(vna_parameters,
                                ro_awg_params,
                                q_awg_params,
                                exc_frequency,
                                pulse_sequence_parameters)
        DD.set_swept_parameters(raadout_delays)

        dd_result = DD.launch()
        self._dd_results[qubit_name] = dd_result
        if save:
            dd_result.save()

    def _perform_Ramsey_oscillations(self, qubit_name, save = False):

        DR = DispersiveRamsey("%s-ramsey"%qubit_name,
                              self._sample_name,
                              vna="vna4",
                              ro_awg=self._ro_awg,
                              q_awg=self._q_awg,
                              q_lo='psg2')

        vna_parameters= {"bandwidth":10,
                         "freq_limits":self._res_limits[qubit_name],
                         "nop":50,
                         "averages":1}

        ramsey_delays = linspace(0, self._max_ramsey_delay, self._ramsey_nop)
        exc_frequency = self._exact_qubit_freqs[qubit_name] - self._ramsey_offset
        pi_pulse_duration =\
            self._dro_results[qubit_name].get_pi_pulse_duration()*1e3

        pulse_sequence_parameters =\
                {"awg_trigger_reaction_delay":0,
                 "readout_duration":3e3,
                 "repetition_period":self._max_ramsey_delay+5e3,
                 "half_pi_pulse_duration":pi_pulse_duration/2}

        ro_awg_params =  {"calibration":self._ro_cal}
        q_awg_params = {"calibration":self._exc_cal}

        DR.set_fixed_parameters(vna_parameters,
                                ro_awg_params,
                                q_awg_params,
                                exc_frequency,
                                pulse_sequence_parameters)
        DR.set_swept_parameters(ramsey_delays)

        dr_result = DR.launch()
        self._dr_results[qubit_name] = dr_result
        if save:
            dr_result.save()

    def _perform_Rabi_oscillations(self, qubit_name, save = False):

        DRO = DispersiveRabiOscillations("%s-rabi"%qubit_name,
                                         self._sample_name,
                                         vna="vna4",
                                         q_lo='psg2',
                                         q_awg=self._q_awg,
                                         ro_awg=self._ro_awg,
                                         plot_update_interval=0.5)

        vna_parameters = {"bandwidth":10,
                          "freq_limits":self._res_limits[qubit_name],
                          "nop":20,
                          "averages":1}

        exc_frequency = self._exact_qubit_freqs[qubit_name]
        excitation_durations = linspace(0, 500, 251)
        rabi_sequence_parameters = {"awg_trigger_reaction_delay":0,
                                    "excitation_amplitude":1,
                                    "readout_duration":3000,
                                    "repetition_period":15000}

        ro_awg_params = {"calibration":self._ro_cal}
        q_awg_params = {"calibration":self._exc_cal}

        DRO.set_fixed_parameters(vna_parameters,
                                 ro_awg_params,
                                 q_awg_params,
                                 exc_frequency,
                                 rabi_sequence_parameters)
        DRO.set_swept_parameters(excitation_durations)
        DRO.set_ult_calib(False)

        dro_result = DRO.launch()
        self._dro_results[qubit_name] = dro_result
        if save:
            dro_result.save()


    def _set_vna_to_ro_lo(self):
        ro_lo = self._vna
        ro_lo.set_frequency = lambda x: ro_lo.set_freq_limits(x, x)
        ro_lo.set_output_state = lambda x: x
        ro_lo.set_nop(1)
        ro_lo.sweep_hold()
        ro_lo.sweep_single()


    def _calibrate_readout(self, qubit_name):

        ro_resonator_frequency = self._sts_fit_params[qubit_name][0]
        ro_resonator_frequency = round(ro_resonator_frequency/1e9, 2)*1e9
        if_frequency = 0e6
        lo_power=0
        ssb_power=-60
        waveform_resolution=1

        db = load_IQMX_calibration_database("CHGRO", 0)
        if db is not None:
            ro_cal =\
                db.get(frozenset(dict(lo_power=lo_power,
                                      ssb_power=ssb_power,
                                      lo_frequency=ro_resonator_frequency,
                                      if_frequency=if_frequency,
                                      waveform_resolution=waveform_resolution)\
                                      .items()))
            if ro_cal is not None:
                return ro_cal

        self._set_vna_to_ro_lo()

        ig = {"dc_offsets":(0.1, +0.1), "dc_offset_open":0.3}
        cal = IQCalibrator(self._ro_awg,
                           self._sa,
                           self._vna,
                           "CHGRO",
                           0,
                           sidebands_to_suppress=1)

        ro_cal = cal.calibrate(lo_frequency=ro_resonator_frequency,
                             if_frequency=if_frequency,
                             lo_power=lo_power,
                             ssb_power=ssb_power,
                             waveform_resolution=1,
                             iterations=3,
                             minimize_iterlimit=20,
                             sa_res_bandwidth=100,
                             initial_guess = ig)
        save_IQMX_calibration(ro_cal)
        return ro_cal

    def _calibrate_excitation(self, qubit_name):
        qubit_frequency = self._tts_fit_params[qubit_name][2]
        qubit_frequency = round(qubit_frequency/1e9/5,2)*5e9 # to 50 MHz
        if_frequency = 100e6
        lo_power = 14
        ssb_power = -20
        waveform_resolution = 1

        db = load_IQMX_calibration_database("CHGQ", 0)
        exc_cal =\
              db.get(frozenset(dict(lo_power=lo_power,
                                    ssb_power=ssb_power,
                                    lo_frequency=qubit_frequency+if_frequency,
                                    if_frequency=if_frequency,
                                    waveform_resolution=waveform_resolution)\
                                    .items()))
        if exc_cal is not None:
            return exc_cal

        ig = {"dc_offsets":(-0.017, -0.04),
              "if_amplitudes":(.1,.1),
              "if_phase":-pi*0.54}
        cal = IQCalibrator(self._q_awg,
                           self._sa,
                           self._exc_lo,
                           "CHGQ",
                           0,
                           sidebands_to_suppress=6)

        exc_cal = cal.calibrate(lo_frequency=qubit_frequency+if_frequency,
                             if_frequency=if_frequency,
                             lo_power=lo_power,
                             ssb_power=ssb_power,
                             waveform_resolution=waveform_resolution,
                             iterations=2,
                             minimize_iterlimit=20,
                             sa_res_bandwidth=500,
                             initial_guess = ig)
        save_IQMX_calibration(exc_cal)
        return exc_cal

    def _open_only_readout_mixer(self):
        self._ro_awg.output_continuous_IQ_waves(frequency=0, amplitudes=(0,0),
                relative_phase=0, offsets=(1,1), waveform_resolution=1)
        self._q_awg.output_continuous_IQ_waves(frequency=0, amplitudes=(0,0),
                relative_phase=0, offsets=(0,0), waveform_resolution=1)

    def _open_mixers(self):
        self._ro_awg.output_continuous_IQ_waves(frequency=0, amplitudes=(0,0),
                relative_phase=0, offsets=(1,1), waveform_resolution=1)
        self._q_awg.output_continuous_IQ_waves(frequency=0, amplitudes=(0,0),
                relative_phase=0, offsets=(1,1), waveform_resolution=1)

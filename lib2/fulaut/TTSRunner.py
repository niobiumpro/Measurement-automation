from lib2.TwoToneSpectroscopy import *
from lib2.fulaut.SpectrumOracle import *

from datetime import datetime

class TTSRunner():

    def __init__(self, sample_name, qubit_name, res_limits, fit_p0, awgs = None):

        self._sample_name = sample_name
        self._qubit_name = qubit_name
        self._res_limits = res_limits
        self._tts_name ="%s-two-tone"%qubit_name
        self._fit_p0 = fit_p0

        if awgs is not None:
            self._ro_awg = awgs["ro_awg"]
            self._q_awg = awgs["q_awg"]
            self._open_mixers()
            self._vna_power = -20
        else:
            self._vna_power = -50

        self._vna_parameters = {"bandwidth":200,
                                "freq_limits":self._res_limits,
                                "nop":20,
                                "power":self._vna_power,
                                "averages":1}

        self._mw_src_parameters = {"power":0}

        res_freq, g, period, sweet_spot, max_q_freq, d = self._fit_p0

        if res_freq>max_q_freq:
            mw_limits = (max_q_freq-1.5e9, res_freq-1e9)
        else:
            mw_limits = (res_freq-0.1e9, max_q_freq+1e9)

        self._mw_src_frequencies = linspace(*mw_limits, 101)
        center = sweet_spot
        self._currents = linspace(sweet_spot - period/8,
                                  sweet_spot + period/8,
                                  101)

        self._tts_result = None
        self._launch_datetime = datetime.today()


    def run(self):

        #Check if today's anticrossing is present

        known_results =\
            MeasurementResult.load(self._sample_name,
                                   self._tts_name,
                                   date=self._launch_datetime.strftime("%b %d %Y"),
                                   return_all=True)

        if known_results is not None:
            self._tts_result = known_results[-1]
        else:
            self._perform_TTS()

        so = SpectrumOracle("transmon",
                            self._tts_result,
                            self._fit_p0[2:])
        params = so.launch(plot=True)

        if known_results is None:
            print("Saving...", end="")
            self._tts_result.save()
        print("\n")

        return params


    def _perform_TTS(self):

        f_res, g, period, sweet_spot, max_q_freq, d =\
                                            self._fit_p0

        TTS = FluxTwoToneSpectroscopy("%s-two-tone"%self._qubit_name,
                                      self._sample_name,
                                      vna="vna4",
                                      mw_src="psg2",
                                      current_src="yok6")

        TTS.set_fixed_parameters(self._vna_parameters,
                                 self._mw_src_parameters,
                                 sweet_spot_current=mean(self._currents),
                                 adaptive=True)

        TTS.set_swept_parameters(self._mw_src_frequencies,
                                 current_values = self._currents)
        TTS._measurement_result._unwrap_phase = True

        self._tts_result = TTS.launch()


    def _open_mixers(self):
        self._ro_awg.output_continuous_IQ_waves(frequency=0,
                                                amplitudes=(0,0),
                                                relative_phase=0,
                                                offsets=(1,1),
                                                waveform_resolution=1)

        self._q_awg.output_continuous_IQ_waves(frequency=0,
                                               amplitudes=(0,0),
                                               relative_phase=0,
                                               offsets=(1,1),
                                               waveform_resolution=1)

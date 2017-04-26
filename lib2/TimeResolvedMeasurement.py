
from drivers.KeysightAWG import PulseBuilder
from lib2.Measurement import *
from lib2.MeasurementResult import *

class TimeResolvedMeasurementContext(ContextBase):

    def __init__(self, equipment = {}, pulse_sequence_parameters = {}, comment = ""):
        '''
        Parameters:
        -----------
        equipment: dict
            a dict containing dicts representing device parameters
        pulse_sequence_parameters: dict
            should contain all control parameters of the pulse sequence used in
            the measurement
        '''
        super().__init__(equipment, comment)
        self._pulse_sequence_parameters = pulse_sequence_parameters

    def get_pulse_sequence_parameters(self):
        return self._pulse_sequence_parameters

    def get_equipment(self):
        return self._equipment

    def to_string(self):
        return "Equipment with parameters:\n"+str(self._equipment)+\
            "\nPulse sequence parameters:\n"+str(self._pulse_sequence_parameters)+\
            "\nComment:\n"+self._comment

class DispersiveRabiOscillations(Measurement):

    def __init__(self, name, sample_name, vna_name, ro_awg_name, q_awg_name,
                q_lo_name, current_src_name, line_attenuation_db = 60):
        super().__init__(name, sample_name, 1, devs_names=[vna_name, ro_awg_name,
                            q_awg_name, q_lo_name, current_src_name])

        self._ro_awg = self._actual_devices[ro_awg_name]
        self._q_awg = self._actual_devices[q_awg_name]
        self._vna = self._actual_devices[vna_name]
        self._q_lo = self._actual_devices[q_lo_name]
        self._current_src = self._actual_devices[current_src_name]
        self._measurement_result = DispersiveRabiOscillationsResult(name,
                    sample_name, "Excitation durations [ns]")

    def setup_control_parameters(self, vna_parameters, q_lo_parameters,
                ro_awg_calibration, q_awg_calibration, qubit_frequency,
                current, pulse_sequence_parameters, excitation_durations):
        self._vna_parameters = vna_parameters
        self._vna_parameters["power"] = \
            ro_awg_calibration.get_radiation_parameters()["lo_power"]

        self._qubit_frequency = qubit_frequency
        self._excitation_durations = excitation_durations
        q_if_frequency = q_awg_calibration \
                    .get_radiation_parameters()["if_frequency"]

        self._q_lo_parameters = q_lo_parameters
        self._q_lo_parameters["power"] = \
            q_awg_calibration.get_radiation_parameters()["lo_power"]
        self._q_lo_parameters["frequency"] = \
            self._qubit_frequency+q_if_frequency

        self._measurement_result.get_context()\
                .get_equipment()["mw_src"] = self._q_lo_parameters

        self._q_awg_calibration = q_awg_calibration
        self._q_pb = PulseBuilder(q_awg_calibration)
        self._ro_awg_calibration = ro_awg_calibration
        self._ro_pb = PulseBuilder(ro_awg_calibration)
        self._pulse_sequence_parameters = pulse_sequence_parameters

        self._measurement_result.get_context()\
                .get_equipment()["ro_awg"] = ro_awg_calibration
        self._measurement_result.get_context()\
                .get_equipment()["q_awg"] = q_awg_calibration
        self._measurement_result.get_context()\
                .get_pulse_sequence_parameters()\
                .update(pulse_sequence_parameters)

        self._q_lo.set_output_state("OFF")
        self._current_src.set_current(current)
        print("Detecting a resonator within provided frequency range of the VNA %s\
                    at current of %.2f mA"%(str(vna_parameters["freq_limits"]),
                        current*1e3), flush=True)
        res_freq, res_amp, res_phase = self._detect_resonator()
        print("Detected frequency is %.5f GHz, at %.2f mU and %.2f degrees"%(res_freq/1e9, res_amp*1e3, res_phase/pi*180))

        self._vna_parameters["freq_limits"] = (res_freq, res_freq)
        self._measurement_result.get_context() \
            .get_equipment()["vna"] = self._vna_parameters
        self._q_lo.set_output_state("ON")

    def _output_rabi_sequence(self, excitation_duration):
        awg_trigger_reaction_delay = \
                self._pulse_sequence_parameters["awg_trigger_reaction_delay"]
        readout_duration = \
                self._pulse_sequence_parameters["readout_duration"]
        repetition_period = \
                self._pulse_sequence_parameters["repetition_period"]

        self._q_pb.add_zero_pulse(awg_trigger_reaction_delay)\
            .add_sine_pulse(excitation_duration, 0)\
            .add_zero_pulse(readout_duration)\
            .add_zero_pulse(repetition_period-readout_duration\
                    -excitation_duration-awg_trigger_reaction_delay)
        self._q_awg.output_pulse_sequence(self._q_pb.build())

        self._ro_pb.add_zero_pulse(excitation_duration)\
             .add_dc_pulse(readout_duration)\
             .add_zero_pulse(100)
        self._ro_awg.output_pulse_sequence(self._ro_pb.build())

    def _record_data(self):
        super()._record_data()
        vna = self._vna

        vna.set_parameters(self._vna_parameters)
        self._q_lo.set_parameters(self._q_lo_parameters)

        raw_s_data = []

        done_sweeps = 0
        for t in self._excitation_durations:
            if self._interrupted:
                self._interrupted = False
                self._vna.set_parameters(self._pre_measurement_vna_parameters)
                return

            self._output_rabi_sequence(t)
            vna.avg_clear(); vna.prepare_for_stb()
            vna.sweep_single(); vna.wait_for_stb()
            raw_s_data.append(mean(vna.get_sdata()))
            done_sweeps += 1
            raw_data = {"excitation_duration":self._excitation_durations[:done_sweeps],
                "s_data":array(raw_s_data)}
            self._measurement_result.set_data(raw_data)

            part_complete = done_sweeps/len(self._excitation_durations)
            elapsed_time = (dt.now() -  self._measurement_result.get_start_datetime())\
                                .total_seconds()
            time_left = self._format_time_delta(elapsed_time/part_complete-elapsed_time)
            print("\rTime left: "+time_left+\
                    ", excitation duration: %.3e ns       "%t, end="",\
                    flush=True)

        self._measurement_result.set_is_finished(True)

    def _detect_resonator(self):
        self._vna.set_nop(200)
        self._vna.set_freq_limits(*self._vna_parameters["freq_limits"])
        self._vna.set_power(self._vna_parameters["power"])
        self._vna.set_bandwidth(self._vna_parameters["bandwidth"]*10)
        self._vna.set_averages(self._vna_parameters["averages"])
        return super()._detect_resonator()

class DispersiveRabiOscillationsResult(MeasurementResult):

    def __init__(self, name, sample_name, parameter_name):
        super().__init__(name, sample_name)
        self._parameter_name = parameter_name
        self._context = TimeResolvedMeasurementContext()
        self._is_finished = False
        self._phase_units = "rad"

    def _prepare_figure(self):
        fig, axes = plt.subplots(2, 1, figsize=(15,7), sharex=True)
        ax_amps, ax_phas = axes
        return fig, axes, (None, None)

    def _plot(self, axes, caxes):
        ax_amps, ax_phas = axes

        data = self.get_data()
        if data is None:
            return

        ax_amps.clear()
        ax_phas.clear()

        ax_amps.plot(data["excitation_duration"], abs(data["s_data"]), label="|S|")
        ax_amps.plot(data["excitation_duration"],
                    real(data["s_data"]), label="Real")
        ax_amps.plot(data["excitation_duration"],
                    imag(data["s_data"]), label="Imag")
        ax_amps.legend()
        ax_phas.plot(data["excitation_duration"], unwrap(angle(data["s_data"])))

        ax_amps.set_ylabel("Probe amplitude [a.u.]")
        # ax_amps.set_xlabel("Excitation duration [$\mu$s]")
        ax_phas.set_ylabel("Probe phase [%s]"%self._phase_units)
        ax_phas.set_xlabel("Excitation duration [$\mu$s]")
        ax_amps.grid()
        ax_phas.grid()

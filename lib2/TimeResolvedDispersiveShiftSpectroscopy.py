from lib2.VNATimeResolvedDispersiveMeasurement2D import *


class TimeResolvedDispersiveShiftSpectroscopy(
                    VNATimeResolvedDispersiveMeasurement2D):

    def __init__(self, name, sample_name, vna_name, ro_awg, q_awg,
        q_lo_name):
        super().__init__(name, sample_name, vna_name,
                                    ro_awg, q_awg, q_lo_name)

        self._measurement_result =\
                TimeResolvedDispersiveShiftSpectroscopyResult(name, sample_name)

    def set_fixed_parameters(self, vna_parameters, q_frequency,
        ro_awg_parameters, q_awg_parameters, pulse_sequence_parameters):

        self._frequencies = linspace(*vna_parameters["freq_limits"],\
                        vna_parameters["nop"])
        q_if_frequency = q_awg_parameters["calibration"] \
            .get_radiation_parameters()["if_frequency"]
        q_lo_parameters = {"frequency":q_frequency+q_if_frequency}

        super().set_fixed_parameters(vna_parameters, q_lo_parameters,
                ro_awg_parameters, q_awg_parameters, pulse_sequence_parameters,
                detect_resonator=False)

    def set_swept_parameters(self, excitation_durations):
        swept_pars = {"excitation_duration":\
                        (self._output_pulse_sequence,
                            excitation_durations)}
        super().set_swept_parameters(**swept_pars)

    def _output_pulse_sequence(self, excitation_duration):
        self._pulse_sequence_parameters["excitation_duration"] = excitation_duration
        self._output_rabi_sequence()

    def _recording_iteration(self):
        vna = self._vna
        vna.avg_clear(); vna.prepare_for_stb();
        vna.sweep_single(); vna.wait_for_stb();
        return vna.get_sdata()

    def _prepare_measurement_result_data(self, parameter_names, parameters_values):
        measurement_data =\
            super()._prepare_measurement_result_data(parameter_names,
                                                            parameters_values)
        measurement_data["vna_frequency"] = self._frequencies
        return measurement_data

class TimeResolvedDispersiveShiftSpectroscopyResult(
                        VNATimeResolvedDispersiveMeasurement2DResult):

    def _prepare_data_for_plot(self, data):
        return data["excitation_duration"]/1e3,\
                data["vna_frequency"]/1e9,\
                 self._remove_delay(data["vna_frequency"], data["data"]).T

    def _annotate_axes(self, axes):
        axes[0].set_ylabel("VNA frequency [GHz]")
        axes[-2].set_ylabel("VNA frequency [GHz]")
        axes[-1].set_xlabel("Excitation duration [$\mu$s]")
        axes[-2].set_xlabel("Excitation duration [$\mu$s]")

    def _remove_delay(self, frequencies, s_data):
        phases = unwrap(angle(s_data*exp(2*pi*1j*50e-9*frequencies)))
        k, b = polyfit(frequencies, phases[0], 1)
        phases = phases - k*frequencies - b
        corr_s_data = abs(s_data)*exp(1j*phases)
        corr_s_data[abs(corr_s_data)<1e-14] = 0
        return corr_s_data

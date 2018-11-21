
from lib2.VNATimeResolvedDispersiveMeasurement2D import *

class ZPulseProfileScan(VNATimeResolvedDispersiveMeasurement2D):

    def __init__(self, name, sample_name, **devs_aliases_map):
        super().__init__(name, sample_name, devs_aliases_map)
        self._measurement_result = ZPulseProfileScanResult(name, sample_name)
        self._sequence_generator =\
                        IQPulseBuilder.build_z_pulse_profile_scan_sequence

    def set_fixed_parameters(self, vna_parameters,
        ro_awg_parameters, q_awg_parameters, q_z_awg_params, pulse_sequence_parameters):
        super().set_fixed_parameters(vna_parameters, {},
            ro_awg_parameters, q_awg_parameters,
            pulse_sequence_parameters, q_z_awg_params=q_z_awg_params)

    def set_swept_parameters(self, pi_pulse_delays, excitation_freqs):
        q_if_frequency = self._q_awg.get_calibration() \
            .get_radiation_parameters()["if_frequency"]
        swept_pars = {"pi_pulse_delay":
                        (self._set_pi_pulse_delay_and_output,
                            pi_pulse_delays),
                      "excitation_frequency":
                        (lambda x: self._q_lo.set_frequency(x+q_if_frequency),
                            excitation_freqs)}
        super().set_swept_parameters(**swept_pars)

    def _set_pi_pulse_delay_and_output(self, pi_pulse_delay):
        self._pulse_sequence_parameters["pi_pulse_delay"] =\
                                                    pi_pulse_delay
        super()._output_pulse_sequence()

class ZPulseProfileScanResult(VNATimeResolvedDispersiveMeasurement2DResult):

    def _prepare_data_for_plot(self, data):
        return data["pi_pulse_delay"]/1e3,\
                data["excitation_frequency"]/1e9,\
                data["data"].T

    def _annotate_axes(self, axes):
        axes[-1].set_xlabel("$(\pi)$-pulse delay [$\mu$s]")
        axes[-2].set_xlabel("$(\pi)$-pulse delay [$\mu$s]")
        axes[0].set_ylabel("Excitation frequency [GHz]")
        axes[-2].set_ylabel("Excitation frequency [GHz]")


from matplotlib import pyplot as plt, colorbar
from lib2.VNATimeResolvedDispersiveMeasurement2D import *

class DispersiveRamseyFringes(VNATimeResolvedDispersiveMeasurement2D):

    def __init__(self, name, sample_name, vna_name, ro_awg_name, q_awg_name,
        q_lo_name):
        super().__init__(name, sample_name, vna_name,
                                    ro_awg_name, q_awg_name, q_lo_name)

        self._measurement_result =\
                DispersiveRamseyFringesResult(name, sample_name)

    def set_swept_parameters(self, ramsey_delays, excitation_freqs):
        q_if_frequency = self._q_awg.get_calibration() \
            .get_radiation_parameters()["if_frequency"]
        swept_pars = {"ramsey_delay":\
                        (self._output_ramsey_sequence,
                            ramsey_delays),
                      "excitation_frequency":
                        (lambda x: self._q_lo.set_frequency(x++q_if_frequency),
                            excitation_freqs)}
        super().set_swept_parameters(**swept_pars)

class DispersiveRamseyFringesResult(VNATimeResolvedDispersiveMeasurement2DResult):

    def _prepare_data_for_plot(self, data):
        return data["excitation_frequency"]/1e9, data["ramsey_delay"]/1e3

    def _annotate_axes(self, axes):
        axes[0].set_ylabel("Ramsey delay [$\mu$s]")
        axes[-2].set_ylabel("Ramsey delay [$\mu$s]")
        axes[-1].set_xlabel("Excitation frequency [GHz]")
        axes[-2].set_xlabel("Excitation frequency [GHz]")

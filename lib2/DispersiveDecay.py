
from lib2.IQPulseSequence import *
from lib2.VNATimeResolvedDispersiveMeasurement1D import *

class DispersiveDecay(VNATimeResolvedDispersiveMeasurement1D):

    def __init__(self, name, sample_name, line_attenuation_db = 60, **devs_aliases_map):
        devs_aliases_map["q_z_awg"] = None
        super().__init__(name, sample_name, devs_aliases_map, line_attenuation_db)

        self._measurement_result = DispersiveDecayResult(name,
                    sample_name)
        self._sequence_generator = IQPulseBuilder.build_dispersive_decay_sequences
        self._swept_parameter_name = "readout_delay"

    def set_swept_parameters(self, readout_delays):
        super().set_swept_parameters(self._swept_parameter_name, readout_delays)


class DispersiveDecayResult(VNATimeResolvedDispersiveMeasurement1DResult):

    def __init__(self, name, sample_name):
        super().__init__(name, sample_name)
        self._annotation_v_pos = "top"

    def _model(self, t, A_r, A_i, T_1, offset_r, offset_i):
        return (A_i+A_r*1j)*exp(-1/T_1*t)+offset_r+1j*offset_i

    def _generate_fit_arguments(self, x, data):
        bounds =([-1, -1, 0.1, -1, -1], [1, 1, 100, 1, 1])
        p0 = [ptp(real(data))/2, ptp(imag(data))/2, 1, min(real(data)), min(imag(data))]
        return p0, bounds

    def _generate_annotation_string(self, opt_params, err):
        return "$T_1=%.2f \pm %.2f\mu$s"%(opt_params[2], err[2])

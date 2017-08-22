
from lib2.IQPulseSequence import *
from lib2.VNATimeResolvedDispersiveMeasurement1D import *
from lib2.DispersiveRamsey import *

class DispersiveHahnEcho(VNATimeResolvedDispersiveMeasurement1D):

    def __init__(self, name, sample_name, vna_name, ro_awg, q_awg,
                q_lo_name, line_attenuation_db = 60):
        super().__init__(name, sample_name, vna_name, ro_awg, q_awg,
                    q_lo_name, line_attenuation_db)

        self._measurement_result = DispersiveHahnEchoResult(name,
                    sample_name)
        self._sequence_generator = PulseBuilder.build_dispersive_hahn_echo_sequences
        self._swept_parameter_name = "echo_delay"

    def set_swept_parameters(self, echo_delays):
        super().set_swept_parameters(self._swept_parameter_name, echo_delays)

class DispersiveHahnEchoResult(VNATimeResolvedDispersiveMeasurement1DResult):

    def _theoretical_function(self, t, A, T_2_ast, offset):
        return A*exp(-1/T_2_ast*t)+offset

    def _generate_fit_arguments(self, x, data):
        p0=[-(max(data)-min(data)), 1, max(data)]
        bounds =([-10, 0, -10], [10, 20, 10])
        return p0, bounds

    def _generate_annotation_string(self, opt_params, err):
        return "$T_{2E}=%.2f\pm%.2f \mu$s"%(opt_params[1], err[1])

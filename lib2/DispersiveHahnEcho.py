
from lib2.IQPulseSequence import *
from lib2.VNATimeResolvedDispersiveMeasurement1D import *
from lib2.DispersiveRamsey import *

class DispersiveHahnEcho(VNATimeResolvedDispersiveMeasurement1D):

    def __init__(self, name, sample_name, vna_name, ro_awg_name, q_awg_name,
                q_lo_name, line_attenuation_db = 60):
        super().__init__(name, sample_name, vna_name, ro_awg_name, q_awg_name,
                    q_lo_name, line_attenuation_db)

        self._measurement_result = DispersiveHahnEchoResult(name,
                    sample_name)

    def set_swept_parameters(self, echo_delays):
        super().set_swept_parameters("echo_delay", echo_delays)

    def _output_pulse_sequence(self, echo_delay):
        self._pulse_sequence_parameters["echo_delay"] = echo_delay
        super._output_hahn_echo_sequence()

class DispersiveHahnEchoResult(VNATimeResolvedDispersiveMeasurement1DResult):

    def _theoretical_function(self, t, A, T_2_ast, offset):
        return A*exp(-1/T_2_ast*t)+offset

    def _generate_fit_arguments(self, x, data):
        p0=[-(max(data)-min(data)), 1, max(data)]
        bounds =([-1, 0, -1], [1, 20, 1])
        return p0, bounds

    def _generate_annotation_string(self, opt_params, err):
        return "$T_{2E}=%.2f\pm%.2f \mu$s"%(opt_params[1], err[1])

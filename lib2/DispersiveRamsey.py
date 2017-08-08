
from lib2.VNATimeResolvedDispersiveMeasurement1D import *

class DispersiveRamsey(VNATimeResolvedDispersiveMeasurement1D):

    def __init__(self, name, sample_name, vna_name, ro_awg, q_awg,
                q_lo_name, line_attenuation_db = 60):
        super().__init__(name, sample_name, vna_name, ro_awg, q_awg,
                    q_lo_name, line_attenuation_db)
        self._measurement_result = DispersiveRamseyResult(name,
                    sample_name)

    def set_swept_parameters(self, ramsey_delays):
        super().set_swept_parameters("ramsey_delay", ramsey_delays)

    def _output_pulse_sequence(self, ramsey_delay):
        self._pulse_sequence_parameters["ramsey_delay"] = ramsey_delay
        self._output_ramsey_sequence()


class DispersiveRamseyResult(VNATimeResolvedDispersiveMeasurement1DResult):

    def _theoretical_function(self, t, A, T_2_ast, Delta_Omega, offset, phase):
        return A*exp(-1/T_2_ast*t)*cos(Delta_Omega*t+phase)+offset

    def _generate_fit_arguments(self, x, data):
        bounds =([-10, 0, 0, -10, -pi], [10, 100, 20*2*pi, 10, pi])
        p0 = [(max(data)-min(data))/2, 1, 1*2*pi,
            mean((max(data), min(data))), 0]
        return p0, bounds

    def _generate_annotation_string(self, opt_params, err):
        return "$T_2^*=%.2f\pm%.2f \mu$s\n$|\Delta\omega/2\pi| = %.2f\pm%.2f$ MHz"%\
            (opt_params[1], err[1], opt_params[2]/2/pi, err[2]/2/pi)


from lib2.IQPulseSequence import *
from lib2.VNATimeResolvedDispersiveMeasurement1D import *

class DispersiveRabiOscillations(VNATimeResolvedDispersiveMeasurement1D):

    def __init__(self, name, sample_name, vna_name, ro_awg, q_awg,
                q_lo_name, line_attenuation_db = 60):
        super().__init__(name, sample_name, vna_name, ro_awg, q_awg,
                    q_lo_name, line_attenuation_db)
        self._measurement_result = DispersiveRabiOscillationsResult(name,
                    sample_name)

    def set_swept_parameters(self, excitation_durations):
        super().set_swept_parameters("excitation_duration", excitation_durations)

    def _output_pulse_sequence(self, excitation_duration):
        self._pulse_sequence_parameters["excitation_duration"] =\
                                                            excitation_duration
        self._output_rabi_sequence()

class DispersiveRabiOscillationsResult(VNATimeResolvedDispersiveMeasurement1DResult):

    def _theoretical_function(self, t, A, T_R, Omega_R, offset):
        return A*exp(-1/T_R*t)*cos(Omega_R*t)+offset

    def _generate_fit_arguments(self, x, data):
        bounds =([-10, 0, 0, -10], [10, 100, 1e3, 10])
        p0 = [-(max(data)-min(data))/2, 1, 10*2*pi, mean((max(data), min(data)))]
        return p0, bounds

    def _generate_annotation_string(self, opt_params, err):
        return "$T_R=%.2f\pm%.2f \mu$s\n$\Omega_R/2\pi = %.2f\pm%.2f$ MHz"%\
                (opt_params[1], err[1], opt_params[2]/2/pi, err[2]/2/pi)

    def get_pi_pulse_duration(self):
        least_freq_error = 1e3
        name = ""
        for name, errors in self._fit_errors.items():
            if errors[2]<least_freq_error:
                least_freq_error = errors[2]
                name = name
        return 1/(self._fit_params[name][2]/2/pi)/2

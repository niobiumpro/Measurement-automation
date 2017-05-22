
from lib2.IQPulseSequence import *
from lib2.VNATimeResolvedDispersiveMeasurement1D import *

class DispersivePiPulseAmplitudeCalibration(VNATimeResolvedDispersiveMeasurement1D):

    def __init__(self, name, sample_name, vna_name, ro_awg_name, q_awg_name,
                q_lo_name, line_attenuation_db = 60):
        super().__init__(name, sample_name, vna_name, ro_awg_name, q_awg_name,
                    q_lo_name, line_attenuation_db)
        self._measurement_result =\
            DispersivePiPulseAmplitudeCalibrationResult(name, sample_name)

    def set_swept_parameters(self, excitation_amplitudes):
        super().set_swept_parameters("excitation_amplitude",
                                                    excitation_amplitudes)

    def _output_pulse_sequence(self, excitation_amplitude):
        self._pulse_sequence_parameters["excitation_amplitude"] =\
                                                    excitation_amplitude
        self._output_rabi_sequence()

class DispersivePiPulseAmplitudeCalibrationResult(VNATimeResolvedDispersiveMeasurement1DResult):

    def _theoretical_function(self, amplitude, A, pi_amplitude, offset):
        return A*cos(pi*amplitude/pi_amplitude)+offset

    def _generate_fit_arguments(self, x, data):
        bounds =([-1, 0, -1e3], [0, 1e3, 1e3])
        p0 = [-(max(data)-min(data))/2, 1, mean((max(data), min(data)))]
        return p0, bounds

    def _prepare_data_for_plot(self, data):
        return data["excitation_amplitude"], data["data"]

    def _generate_annotation_string(self, opt_params, err):
        return "$(\pi) = %.2f\pm%.2f$ a.u."%(opt_params[1], err[1]/2/pi)

    def get_pi_pulse_amplitude(self):
        smallest_pi_amp_error = 1e3
        name = ""
        for name, errors in self._fit_errors.items():
            if errors[1]<smallest_pi_amp_error:
                smallest_pi_amp_error = errors[1]
                name = name
        return self._fit_params[name][1]

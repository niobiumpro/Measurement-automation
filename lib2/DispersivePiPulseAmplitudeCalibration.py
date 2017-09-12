
from lib2.IQPulseSequence import *
from lib2.VNATimeResolvedDispersiveMeasurement1D import *

class DispersivePiPulseAmplitudeCalibration(VNATimeResolvedDispersiveMeasurement1D):

    def __init__(self, name, sample_name, vna_name, ro_awg, q_awg,
                q_lo_name, line_attenuation_db = 60):
        super().__init__(name, sample_name, vna_name, ro_awg, q_awg,
                    q_lo_name, line_attenuation_db)
        self._measurement_result =\
            DispersivePiPulseAmplitudeCalibrationResult(name, sample_name)
        self._sequence_generator = PulseBuilder.build_dispersive_rabi_sequences
        self._swept_parameter_name = "excitation_amplitude"

    def set_swept_parameters(self, excitation_amplitudes):
        super().set_swept_parameters("excitation_amplitude",
                                            excitation_amplitudes)


class DispersivePiPulseAmplitudeCalibrationResult(VNATimeResolvedDispersiveMeasurement1DResult):

    def __init__(self, name, sample_name):
        super().__init__(name, sample_name)
        if_amps = self._context.get_equipment()["q_awg"]["calibration"]\
                                                                ._if_amplitudes
        self._x_axis_units = r"$\times$ cal values (%.2f %.2f)"%(if_amps[0],
                                                                    if_amps[1])


    def _model(self, amplitude, A_r, A_i, pi_amplitude,
        offset_r, offset_i):
        return (A_r+1j*A_i)*cos(pi*amplitude/pi_amplitude)+(offset_r+offset_i*1j)

    def _generate_fit_arguments(self, x, data):
        bounds =([-10, -10, 0, -10, -10], [10, 10, 10, 10, 10])
        amp_r, amp_i = -ptp(real(data))/2, -ptp(imag(data))/2
        p0 = [amp_r, amp_i, 3, max(real(data))-amp_r, max(imag(data))-amp_i]
        return p0, bounds

    def _prepare_data_for_plot(self, data):
        return data["excitation_amplitude"], data["data"]

    def _generate_annotation_string(self, opt_params, err):
        return "$(\pi) = %.2f \pm %.2f$ a.u."%(opt_params[2], err[2]/2/pi)

    def get_pi_pulse_amplitude(self):
        return self._fit_params[2]

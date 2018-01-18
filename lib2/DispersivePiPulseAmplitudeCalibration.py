
from lib2.IQPulseSequence import *
from lib2.VNATimeResolvedDispersiveMeasurement1D import *

class DispersivePiPulseAmplitudeCalibration(VNATimeResolvedDispersiveMeasurement1D):

    def __init__(self, name, sample_name, vna_name, ro_awg, q_awg,
                q_lo_name, line_attenuation_db = 60, **kwargs):
        super().__init__(name, sample_name, vna_name, ro_awg, q_awg,
                    q_lo_name, line_attenuation_db, **kwargs)
        self._measurement_result =\
            DispersivePiPulseAmplitudeCalibrationResult(name, sample_name)
        self._sequence_generator = IQPulseBuilder.build_dispersive_rabi_sequences
        self._swept_parameter_name = "excitation_amplitude"

    def set_fixed_parameters(self, vna_parameters, ro_awg_params, q_awg_params,
        exc_frequency, sequence_parameters, basis=None):
        super().set_fixed_parameters(vna_parameters, ro_awg_params, q_awg_params,
            exc_frequency, sequence_parameters)
        self._measurement_result.set_x_axis_units()
        self._basis = basis

    def set_swept_parameters(self, excitation_amplitudes):
        super().set_swept_parameters("excitation_amplitude",
                                            excitation_amplitudes)

class DispersivePiPulseAmplitudeCalibrationResult(VNATimeResolvedDispersiveMeasurement1DResult):

    def __init__(self, name, sample_name):
        super().__init__(name, sample_name)

    def set_x_axis_units(self):
        if_amps = self._context.get_equipment()["q_awg"]["calibration"]\
                                                                ._if_amplitudes
        self._x_axis_units = r"$\times$ cal values (%.2f %.2f)"%(if_amps[0],
                                                                    if_amps[1])


    def _model(self, amplitude, A_r, A_i, pi_amplitude,
        offset_r, offset_i):
        return -(A_r+1j*A_i)*cos(pi*amplitude/pi_amplitude)+(offset_r+offset_i*1j)

    def _generate_fit_arguments(self, x, data):
        bounds =([-10, -10, 0, -10, -10], [10, 10, 10, 10, 10])
        amp_r, amp_i = ptp(real(data))/2, ptp(imag(data))/2
        if abs(max(real(data)) - real(data[0])) < abs(real(data[0])-min(real(data))):
            amp_r = -amp_r
        if abs(max(imag(data)) - imag(data[0])) < abs(imag(data[0])-min(imag(data))):
            amp_i = -amp_i
        offset_r, offset_i = max(real(data))-abs(amp_r), max(imag(data))-abs(amp_i)
        p0 = [amp_r, amp_i, 3, offset_r, offset_i]
        return p0, bounds

    def _prepare_data_for_plot(self, data):
        return data["excitation_amplitude"], data["data"]

    def _generate_annotation_string(self, opt_params, err):
        return "$(\pi) = %.2f \pm %.2f$ a.u."%(opt_params[2], err[2])

    def get_pi_pulse_amplitude(self):
        return self._fit_params[2]

    def get_basis(self):
        fit = self._fit_params
        A_r, A_i, offset_r, offset_i = fit[0], fit[1], fit[-2], fit[-1]
        ground_state = -A_r+offset_r+1j*(-A_i+offset_i)
        excited_state = A_r+offset_r+1j*(A_i+offset_i)
        return array((ground_state, excited_state))

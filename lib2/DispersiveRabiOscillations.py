
from lib2.IQPulseSequence import *
from lib2.VNATimeResolvedDispersiveMeasurement1D import *

class DispersiveRabiOscillations(VNATimeResolvedDispersiveMeasurement1D):

    def __init__(self, name, sample_name, vna_name, ro_awg, q_awg,
                q_lo_name, line_attenuation_db = 60, plot_update_interval=1):
        super().__init__(name, sample_name, vna_name, ro_awg, q_awg,
                    q_lo_name, line_attenuation_db, plot_update_interval)
        self._measurement_result = DispersiveRabiOscillationsResult(name,
                    sample_name)
        self._sequence_generator = PulseBuilder.build_dispersive_rabi_sequences
        self._swept_parameter_name = "excitation_duration"
        self._basis = None

    def set_swept_parameters(self, excitation_durations):
        super().set_swept_parameters(self._swept_parameter_name, excitation_durations)

    def set_basis(self, basis):
        self._basis = basis

    def _recording_iteration(self):
        data = super()._recording_iteration()
        if self._basis is None:
            return data
        basis = self._basis
        p_r = (real(data) - real(basis[0]))/(real(basis[1]) - real(basis[0]))
        p_i = (imag(data) - imag(basis[0]))/(imag(basis[1]) - imag(basis[0]))
        return p_r+1j*p_i


class DispersiveRabiOscillationsResult(VNATimeResolvedDispersiveMeasurement1DResult):


    def _model(self, t, A_r, A_i, T_R, Omega_R, offset_r, offset_i):
        return -(A_r+1j*A_i)*exp(-1/T_R*t)*cos(Omega_R*t)+offset_r+offset_i*1j

    def _generate_fit_arguments(self, x, data):
        amp_r, amp_i = ptp(real(data))/2, ptp(imag(data))/2
        bounds =([-amp_r*1.5, -amp_i*1.5, 0.1, 1*2*pi, -10, -10],
                    [amp_r*1.5, amp_i*1.5, 100, 50*2*pi, 10, 10])

        frequency = random.random(1)*50+1
        p0 = [amp_r, amp_i, 1, frequency*2*pi, max(real(data))-amp_r,
        max(imag(data))-amp_i]
        return p0, bounds

    def _generate_annotation_string(self, opt_params, err):
        return "$T_R=%.2f \pm %.2f \mu$s\n$\Omega_R/2\pi = %.2f \pm %.2f$ MHz"%\
                (opt_params[2], err[2], opt_params[3]/2/pi, err[3]/2/pi)

    def get_pi_pulse_duration(self):
        return 1/(self._fit_params[3]/2/pi)/2

    def get_basis(self):
        fit = self._fit_params
        A_r, A_i, offset_r, offset_i = fit[0], fit[1], fit[-2], fit[-1]
        ground_state = -A_r+offset_r+1j*(-A_i+offset_i)
        excited_state = A_r+offset_r+1j*(A_i+offset_i)
        return array((ground_state, excited_state))

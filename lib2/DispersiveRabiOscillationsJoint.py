from lib2.IQPulseSequence import *
from lib2.VNATimeResolvedDispersiveMeasurement1D import *
from numpy import exp, cos, sin, sqrt, pi


class DispersiveRabiOscillationsJoint(VNATimeResolvedDispersiveMeasurement1D):                      # TODO Any changes?

    def __init__(self, name, sample_name, plot_update_interval=1, two_qubits=True,
                                                                                                **devs_aliases_map):
        super().__init__(name, sample_name, devs_aliases_map, plot_update_interval)
        self._sequence_generator = IQPulseBuilder.build_dispersive_rabi_2qubit_sequences
        self._swept_parameter_name = "excitation_duration"
        self._two_qubits = two_qubits
        self._measurement_result = DispersiveRabiOscillationsJointResult(name, sample_name, two_qubits=two_qubits)

    def set_fixed_parameters(self, pulse_sequence_parameters,
                             **dev_params):
        """
        :param dev_params:
            Minimum expected keys and elements expected in each:
                'vna'
                'q_awg': 0,1
                'ro_awg'
        """

        super().set_fixed_parameters(pulse_sequence_parameters,
                                     **dev_params)

    def set_swept_parameters(self, excitation_durations):
        super().set_swept_parameters(self._swept_parameter_name, excitation_durations)


class DispersiveRabiOscillationsJointResult(VNATimeResolvedDispersiveMeasurement1DResult):

    def __init__(self, name, sample_name, two_qubits=True):
        self._two_qubits = two_qubits
        super().__init__(name, sample_name)

    @staticmethod
    def rabi_z_av(t, gamma_1, gamma_2, omega_r):
        tau_r = 2/(gamma_1 + gamma_2)
        omega_r_2 = sqrt(omega_r**2 - (1/tau_r)**2)
        return (gamma_1*gamma_2 + exp(-t/tau_r)*omega_r**2*(cos(omega_r_2*t)+sin(omega_r_2*t)/(tau_r*omega_r_2)))/(gamma_1*gamma_2 + omega_r**2)

    @staticmethod
    def rabi_x_av(t, gamma_1, gamma_2, omega_r):
        tau_r = 2/(gamma_1 + gamma_2)
        omega_r_2 = sqrt(omega_r**2 - (1/tau_r)**2)
        return (gamma_1 + exp(-t/tau_r)*(gamma_1*cos(omega_r_2*t)-sin(omega_r_2*t)*(2*omega_r**2+gamma_1*(gamma_2-gamma_1))/(2*omega_r_2)))/(gamma_1*gamma_2 + omega_r**2)*omega_r

    def _model(self, t, b_II_r, b_II_i,
                        b_ZI_r, b_ZI_i,
                        b_IZ_r, b_IZ_i,
                        b_ZZ_r, b_ZZ_i,
                        b_XI_r, b_XI_i,
                        b_IX_r, b_IX_i,
                        b_XX_r, b_XX_i,
                        b_XZ_r, b_XZ_i,
                        b_ZX_r, b_ZX_i,
                        g_1_q1, g_2_q1, omega_r_q1,
                        g_1_q2, g_2_q2, omega_r_q2):
        if not self._two_qubits:
            print('Warning: One qubit regime. Fit may suffer.')                                     # TODO

        return ((b_II_r+1j*b_II_i) +
                (b_XI_r+1j*b_XI_i)*self.rabi_x_av(t, g_1_q1, g_2_q1, omega_r_q1) +
                (b_ZI_r+1j*b_ZI_i)*self.rabi_z_av(t, g_1_q1, g_2_q1, omega_r_q1) +
                (b_IX_r+1j*b_IX_i)*self.rabi_x_av(t, g_1_q2, g_2_q2, omega_r_q2) +
                (b_IZ_r+1j*b_IZ_i)*self.rabi_z_av(t, g_1_q2, g_2_q2, omega_r_q2) +
                (b_XX_r+1j*b_XX_i)*self.rabi_x_av(t, g_1_q1, g_2_q1, omega_r_q1)*self.rabi_x_av(t, g_1_q2, g_2_q2, omega_r_q2) +
                (b_ZX_r+1j*b_ZX_i)*self.rabi_z_av(t, g_1_q1, g_2_q1, omega_r_q1)*self.rabi_x_av(t, g_1_q2, g_2_q2, omega_r_q2) +
                (b_XZ_r+1j*b_XZ_i)*self.rabi_x_av(t, g_1_q1, g_2_q1, omega_r_q1)*self.rabi_z_av(t, g_1_q2, g_2_q2, omega_r_q2) +
                (b_ZZ_r+1j*b_ZZ_i)*self.rabi_z_av(t, g_1_q1, g_2_q1, omega_r_q1)*self.rabi_z_av(t, g_1_q2, g_2_q2, omega_r_q2))

    def _generate_fit_arguments(self, x, data):                                                 # TODO bounds
        amp_r, amp_i = ptp(real(data))/2 + 0.01, ptp(imag(data))/2 + 0.01
        time_step = x[1]-x[0]
        max_frequency = 1/time_step/2/5
        min_frequency = 1e-6
        frequency = random.random()*(max_frequency-min_frequency)+min_frequency
        g_min = min_frequency / 10
        g_max = max_frequency / 10
        g = frequency / 10
        p0 = [amp_r, amp_i,                 # b_II
              amp_r, amp_i,                 # b_ZI
              amp_r, amp_i,                 # b_IZ
              amp_r, amp_i,                 # b_ZZ
              0, 0,                         # b_XI
              0, 0,                         # b_IX
              0, 0,                         # b_XX
              0, 0,                         # b_XZ
              0, 0,                         # b_ZX
              g, g, frequency * 2 * pi,     # Qubit 1, g_1, g_2, omega
              g, g, frequency * 2 * pi]     # Qubit 2, g_1, g_2, omega
        bounds = ([- amp_r * 2, - amp_i * 2,
                   - amp_r * 2, - amp_i * 2,
                   - amp_r * 2, - amp_i * 2,
                   - amp_r * 2, - amp_i * 2,
                   - amp_r * 2, - amp_i * 2,
                   - amp_r * 2, - amp_i * 2,
                   - amp_r * 2, - amp_i * 2,
                   - amp_r * 2, - amp_i * 2,
                   - amp_r * 2, - amp_i * 2,
                   g_min, g_min, min_frequency * 2 * pi,
                   g_min, g_min, min_frequency * 2 * pi],
                  [amp_r * 2, amp_i * 2,
                   amp_r * 2, amp_i * 2,
                   amp_r * 2, amp_i * 2,
                   amp_r * 2, amp_i * 2,
                   amp_r * 2, amp_i * 2,
                   amp_r * 2, amp_i * 2,
                   amp_r * 2, amp_i * 2,
                   amp_r * 2, amp_i * 2,
                   amp_r * 2, amp_i * 2,
                   g_max, g_max, max_frequency * 2 * pi,
                   g_max, g_max, max_frequency * 2 * pi])
        return p0, bounds

    def _generate_annotation_string(self, opt_params, err):                                     # TODO
        return 0
        # return "$T_R=%.2f \pm %.2f \mu$s\n$\Omega_R/2\pi = %.2f \pm %.2f$ MHz"%\
         #       (opt_params[2], err[2], opt_params[3]/2/pi, err[3]/2/pi)

    def get_betas(self):
        return (self._fit_params[0],
                self._fit_params[2],
                self._fit_params[4],
                self._fit_params[6])

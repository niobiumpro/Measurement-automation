from matplotlib import pyplot as plt, colorbar
from lib2.VNATimeResolvedDispersiveMeasurement2D import *
from scipy.interpolate import interp2d
from lib2.QuantumState import *
import numpy as np
from qutip import qeye, sigmax, sigmay, sigmaz, fidelity, Qobj, expect, tensor
from math import *
from IPython.display import clear_output


from scipy import optimize
from tqdm import tqdm_notebook



class Tomo:

    def __init__(self, dim=4):
        self._dim = dim
        self._local_rotations = []
        self._measurement_operator = []
        self._measurements = []

    @staticmethod
    def x_to_rho(x):                                # Параметризация матрицы плотности
        dim = int(sqrt(len(x)))
        t = np.identity(dim, complex)
        for i in range(dim):
            t[i, i] = abs(x[i])
        k = dim
        for i in range(dim):
            for l in range(i + 1, dim):
                t[i, l] = x[k] + (1j) * x[k + 1]
                k += 2
        q_dim = [2] * int(log(dim) / log(2))
        rho = Qobj(t, dims=[q_dim, q_dim])
        rho = rho.dag() * rho
        rho = rho / rho.tr()
        return rho

    @staticmethod
    def rotator_from_command(com):
        """
        Constructs QObj from the string containing command
        Commands can start from: 'I', 'X', 'Y', 'Z'
        Commands also can contain '/' + number which refers to the length of the pulse
        Commands examples: 'X', 'Y/2', 'Z/6', 'I', ...
        """
        axes = {'I': identity(2), 'X': sigmax(), 'Y': sigmay(), 'Z': sigmaz()}
        if com[0] == 'I':
            return identity(2)
        elif len(com) == 1:
            amp = 1
        else:
            com = com.split('/')
            amp = 1 / float(com[1])
        ax = axes[com[0]]
        return (-1j * amp * pi / 2 * ax).expm()

    def upload_rotation_sequence_from_command_list(self, com_list):
        rot_seq = []
        for coms in com_list:
            op = tensor(list(map(self.rotator_from_command, coms)))
            rot_seq.append(op)
        self._local_rotations = rot_seq

    def upload_measurement_operator(self, meas_op):
        self._measurement_operator = meas_op

    def construct_measurements(self, measurement_results):
        """
        Construct measurement sequence required for reconstruction
        Tomo.upload_rotation_sequence_from_command_list() and Tomo.upload_measurement_operator must be uploaded
        :param measurement_results: measured expected values
        """
        self._measurements = [(rot.dag() * self._measurement_operator * rot, res)
                                for (rot, res) in zip(self._local_rotations, measurement_results)]

    def upload_measurements(self, meas):            # Загрузить набор измерений [(оператор, измеренное. среднее), ...]
        """
        Measurement sequence can be uploaded manually
        Format: [(measurement operator, measured expected value), ...]
        """
        self._measurements = meas

    def likelihood(self, x):                        # Вычисление Likelihood по загруженным измерениям \
        rho = self.x_to_rho(x)                      # для матрицы плотности заданной через x
        lh = 0
        for (op, ex) in self._measurements:
            lh += (expect(rho, op) - ex) ** 2
        return lh

    def find_rho(self, average=5):  # Минимизации Likelihood
        for n in tqdm_notebook(range(average), desc='Tomography: Likelihood minimization', ncols=700):
            x0 = np.random.rand(self._dim ** 2) * 2 - 1
            new = optimize.minimize(self.likelihood, x0, method='L-BFGS-B')
            if n == 0:
                best = new
            else:
                if new.fun < best.fun:
                    best = new
        return self.x_to_rho(best.x)


class DispersiveJointTomography(VNATimeResolvedDispersiveMeasurement):      # TODO

    def __init__(self):


class DispersiveJointTomographyResult(VNATimeResolvedDispersiveMeasurementResult):      # TODO

    def __init__(self, name, sample_name, smoothing_factor):
        super().__init__(name, sample_name)
        self._pulse_sequence_parameters = self._context \
            .get_pulse_sequence_parameters()
        self._smoothing_factor = smoothing_factor
        self._betas = (0, 0, 0, 0)

    @staticmethod
    def _meas_op(amp, ph):
        return (-1j * amp * pi / 2 * (cos(ph) * sigmax() + sin(ph) * sigmay())).expm()



    def upload_betas(self, *betas):                                            # TODO
        self._betas = betas

    def find_density_matrix(self):                                                                 # TODO name

        beta_II, beta_ZI, beta_IZ, beta_ZZ = self._betas
        joint_op = (
                beta_II * tensor(identity(2), identity(2)) +
                beta_ZI * tensor(sigmaz(), identity(2)) +
                beta_IZ * tensor(identity(2), sigmaz()) +
                beta_ZZ * tensor(sigmaz(), sigmaz()))

        tomo = Tomo(dim=4)
        tomo.upload_measurement_operator(joint_op)
        tomo.upload_rotation_sequence_from_command_list(??)                     #TODO
        tomo.construct_measurements(??)                                         #TODO

        return tomo.find_rho()
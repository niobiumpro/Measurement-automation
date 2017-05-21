
from lib2.VNATimeResolvedDispersiveMeasurement1D import *

class DispersiveAPE(VNATimeResolvedDispersiveMeasurement1D):

    def __init__(self, name, sample_name, vna_name, ro_awg_name, q_awg_name,
                q_lo_name, line_attenuation_db = 60):
        super().__init__(name, sample_name, vna_name, ro_awg_name, q_awg_name,
                    q_lo_name, line_attenuation_db)

        self._measurement_result = DispersiveAPEResult(name,
                    sample_name)

    def set_swept_parameters(self, ramsey_angles):
        super().set_swept_parameters("ramsey_angle", ramsey_angles)

    def _output_pulse_sequence(self, ramsey_angle):
        self._pulse_sequence_parameters["ramsey_angle"] = ramsey_angle
        self._output_APE_sequence()


class DispersiveAPEResult(VNATimeResolvedDispersiveMeasurement1DResult):

    def __init__(self, name, sample_name):
        super().__init__(name, sample_name)
        self._x_axis_units = "$\pi$ rad"

    def _theoretical_function(self, ramsey_angle, A, offset, phase_error):
        return A*sin(ramsey_angle*pi+phase_error*pi)+offset

    def _generate_fit_arguments(self, x, data):
        bounds =([0, -1, -pi], [1, 1, pi])
        p0 = [(max(data)-min(data))/2, mean((max(data), min(data))), 0]
        return p0, bounds

    def _prepare_data_for_plot(self, data):
        return data[self._parameter_names[0]]/pi, data["data"]

    def _generate_annotation_string(self, opt_params, err):
        return "$\phi_{err} = %.2f\pm%.2f$ deg"%\
            ((opt_params[2]-1/2)*180, err[2]*180)

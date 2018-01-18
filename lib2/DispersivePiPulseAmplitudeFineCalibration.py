
from lib2.IQPulseSequence import *
from lib2.VNATimeResolvedDispersiveMeasurement1D import *

class DispersivePiPulseAmplitudeFineCalibration(VNATimeResolvedDispersiveMeasurement1D):

    def __init__(self, name, sample_name, vna_name, ro_awg, q_awg,
                q_lo_name, line_attenuation_db = 60, **kwargs):
        super().__init__(name, sample_name, vna_name, ro_awg, q_awg,
                    q_lo_name, line_attenuation_db, **kwargs)
        self._measurement_result =\
            DispersivePiPulseAmplitudeFineCalibrationResult(name, sample_name)
        self._sequence_generator =\
                IQPulseBuilder.build_dispersive_pi_half_calibration_sequences
        self._swept_parameter_name = "twice_pi_half_pulses_count"

    def set_fixed_parameters(self, vna_parameters, ro_awg_params, q_awg_params,
        exc_frequency, sequence_parameters):
        super().set_fixed_parameters(vna_parameters, ro_awg_params, q_awg_params,
            exc_frequency, sequence_parameters)

    def set_swept_parameters(self, twice_pi_half_pulses_counts):
        super().set_swept_parameters(self._swept_parameter_name,
                                            array(twice_pi_half_pulses_counts))

class DispersivePiPulseAmplitudeFineCalibrationResult(VNATimeResolvedDispersiveMeasurement1DResult):

    def __init__(self, name, sample_name):
        super().__init__(name, sample_name)
        self._x_axis_units = r"$(\pi/2)^2$-pulses count"

    def get_correct_pi_half_amplitude(self):
        old_amp = self.get_context()\
                    .get_pulse_sequence_parameters()["excitation_amplitude"]
        return old_amp/(pi/2-self._fit_params[0])*(pi/2)

    def _model(self, twice_pi_half_pulses_count, epsilon,
        offset_r, offset_i):
        # positive epsilon for under-rotation
        n = twice_pi_half_pulses_count*2+1
        return -(.5+.5j)*(-1)**twice_pi_half_pulses_count*cos(pi/2-epsilon*n)+(offset_r+offset_i*1j)

    def _generate_fit_arguments(self, x, data):
        bounds =([-pi, 0, 0], [pi, 1, 1])
        p0 = [0, 1/2, 1/2]
        return p0, bounds

    def _prepare_data_for_plot(self, data):
        return data["twice_pi_half_pulses_count"], data["data"]

    def _generate_annotation_string(self, opt_params, err):
        return r"$\varepsilon = %.2f \pm %.2f$ deg"%(opt_params[0]/pi*180,
                                                                err[0]/pi*180)

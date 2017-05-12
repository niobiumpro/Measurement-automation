
from drivers.KeysightAWG import PulseBuilder
from lib2.Measurement import *
from lib2.MeasurementResult import *

from scipy.optimize import curve_fit

from lib2.VNATimeResolvedMeasurement import *

class DispersiveRabiOscillations(VNATimeResolvedMeasurement1D):

    def __init__(self, name, sample_name, vna_name, ro_awg_name, q_awg_name,
                q_lo_name, current_src_name, line_attenuation_db = 60):
        super().__init__(name, sample_name, vna_name, ro_awg_name, q_awg_name,
                    q_lo_name, current_src_name, line_attenuation_db)

        self._measurement_result = DispersiveRabiOscillationsResult(name,
                    sample_name)

    def set_swept_parameters(self, excitation_durations):
        super().set_swept_parameters("excitation_duration", excitation_durations)

    def _output_pulse_sequence(self, excitation_duration):
        awg_trigger_reaction_delay = \
                self._pulse_sequence_parameters["awg_trigger_reaction_delay"]
        readout_duration = \
                self._pulse_sequence_parameters["readout_duration"]
        repetition_period = \
                self._pulse_sequence_parameters["repetition_period"]

        self._q_pb.add_zero_pulse(awg_trigger_reaction_delay)\
            .add_sine_pulse(excitation_duration, 0)\
            .add_zero_pulse(readout_duration)\
            .add_zero_until(repetition_period)
        self._q_awg.output_pulse_sequence(self._q_pb.build())

        self._ro_pb.add_zero_pulse(excitation_duration)\
             .add_dc_pulse(readout_duration)\
             .add_zero_pulse(100)
        self._ro_awg.output_pulse_sequence(self._ro_pb.build())


class DispersiveRabiOscillationsResult(VNATimeResolvedMeasurementResult1D):

    def _theoretical_function(self, t, A, T_R, Omega_R, offset, phase):
        return A*exp(-1/T_R*t)*cos(Omega_R*t+phase)+offset

    def _generate_fit_arguments(self, data):
        bounds =([-1e3, 0, 0, -1e3, -pi], [1e3, 100, 1e3, 1e3, pi])
        p0 = [(max(data)-min(data))/2, 1, 10*2*pi,
            mean((max(data), min(data))), pi]
        return p0, bounds

    def get_pi_pulse_duration(self):
        least_freq_error = 1e3
        name = ""
        for name, errors in self._fit_errors.items():
            if errors[2]<least_freq_error:
                least_freq_error = errors[2]
                name = name
        return 1/(self._fit_params[name][2]/2/pi)/2

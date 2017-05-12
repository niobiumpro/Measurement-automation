
from drivers.KeysightAWG import PulseBuilder
from lib2.Measurement import *
from lib2.MeasurementResult import *

from scipy.optimize import curve_fit

from lib2.VNATimeResolvedMeasurement import *

class DispersiveRamsey(VNATimeResolvedMeasurement1D):

    def __init__(self, name, sample_name, vna_name, ro_awg_name, q_awg_name,
                q_lo_name, current_src_name, line_attenuation_db = 60):
        super().__init__(name, sample_name, vna_name, ro_awg_name, q_awg_name,
                    q_lo_name, current_src_name, line_attenuation_db)

        self._measurement_result = DispersiveRamseyResult(name,
                    sample_name)

    def set_swept_parameters(self, ramsey_delays):
        super().set_swept_parameters("ramsey_delay", ramsey_delays)

    def _output_pulse_sequence(self, ramsey_delay):
        awg_trigger_reaction_delay = \
                self._pulse_sequence_parameters["awg_trigger_reaction_delay"]
        readout_duration = \
                self._pulse_sequence_parameters["readout_duration"]
        repetition_period = \
                self._pulse_sequence_parameters["repetition_period"]
        half_pi_pulse_duration = \
                self._pulse_sequence_parameters["half_pi_pulse_duration"]

        self._q_pb.add_zero_pulse(awg_trigger_reaction_delay)\
            .add_sine_pulse(half_pi_pulse_duration, 0)\
            .add_zero_pulse(ramsey_delay)\
            .add_sine_pulse(half_pi_pulse_duration,
                    time_offset = half_pi_pulse_duration+ramsey_delay)\
            .add_zero_pulse(readout_duration)\
            .add_zero_until(repetition_period)
        self._q_awg.output_pulse_sequence(self._q_pb.build())

        self._ro_pb.add_zero_pulse(2*half_pi_pulse_duration+ramsey_delay)\
             .add_dc_pulse(readout_duration)\
             .add_zero_pulse(100)
        self._ro_awg.output_pulse_sequence(self._ro_pb.build())


class DispersiveRamseyResult(VNATimeResolvedMeasurementResult1D):

    def _theoretical_function(self, t, A, T_2_ast, Delta_Omega, offset, phase):
        return A*exp(-1/T_2_ast*t)*cos(Delta_Omega*t+phase)+offset

    def _generate_fit_arguments(self, data):
        bounds =([-1e3, 0, 0, -1e3, -pi], [1e3, 100, 1e3, 1e3, pi])
        p0 = [(max(data)-min(data))/2, 1, 10*2*pi,
            mean((max(data), min(data))), 0]
        return p0, bounds

    def _plot_fit(self, axes):
        self.fit(verbose=False)

        for idx, name in enumerate(self._fit_params.keys()):
            ax = axes[name]
            opt_params = self._fit_params[name]
            err = self._fit_errors[name]

            X = self.get_data()[self._parameter_names[0]]/1e3
            Y = self._theoretical_function(X, *opt_params)
            ax.plot(X, Y, "C%d"%list(self._data_formats.keys()).index(name))

            bbox_props = dict(boxstyle="round", fc="white",
                    ec="black", lw=1, alpha=0.5)
            ax.annotate("$T_2^*=%.2f\pm%.2f \mu$s\n$|\Delta\omega/2\pi| = %.2f\pm%.2f$ MHz"%\
                (opt_params[1], err[1], opt_params[2]/2/pi, err[2]/2/pi),
                (mean(ax.get_xlim()),  .9*ax.get_ylim()[0]+.1*ax.get_ylim()[1]),
                bbox=bbox_props, ha="center")

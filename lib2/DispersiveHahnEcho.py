
from lib2.IQPulseSequence import *
from lib2.VNATimeResolvedDispersiveMeasurement1D import *
from lib2.DispersiveRamsey import *

class DispersiveHahnEcho(VNATimeResolvedDispersiveMeasurement1D):

    def __init__(self, name, sample_name, vna_name, ro_awg_name, q_awg_name,
                q_lo_name, line_attenuation_db = 60):
        super().__init__(name, sample_name, vna_name, ro_awg_name, q_awg_name,
                    q_lo_name, line_attenuation_db)

        self._measurement_result = DispersiveHahnEchoResult(name,
                    sample_name)

    def set_swept_parameters(self, echo_delays):
        super().set_swept_parameters("echo_delay", echo_delays)

    def _output_pulse_sequence(self, echo_delay):
        awg_trigger_reaction_delay = \
                self._pulse_sequence_parameters["awg_trigger_reaction_delay"]
        readout_duration = \
                self._pulse_sequence_parameters["readout_duration"]
        repetition_period = \
                self._pulse_sequence_parameters["repetition_period"]
        half_pi_pulse_duration = \
                self._pulse_sequence_parameters["half_pi_pulse_duration"]

        q_pb = self._q_awg.get_pulse_builder()
        q_pb.add_zero_pulse(awg_trigger_reaction_delay)\
                .add_sine_pulse(half_pi_pulse_duration, 0)\
                .add_zero_pulse(echo_delay/2)\
                .add_sine_pulse(2*half_pi_pulse_duration,
                        time_offset = half_pi_pulse_duration+echo_delay/2)\
                .add_zero_pulse(echo_delay/2)\
                .add_sine_pulse(half_pi_pulse_duration,
                        time_offset = 3*half_pi_pulse_duration+echo_delay)\
                .add_zero_pulse(readout_duration)\
                .add_zero_until(repetition_period)
        self._q_awg.output_pulse_sequence(q_pb.build())

        ro_pb = self._ro_awg.get_pulse_builder()
        ro_pb.add_zero_pulse(4*half_pi_pulse_duration+echo_delay)\
             .add_dc_pulse(readout_duration)\
             .add_zero_pulse(100)
        self._ro_awg.output_pulse_sequence(ro_pb.build())


class DispersiveHahnEchoResult(VNATimeResolvedDispersiveMeasurement1DResult):

    def _theoretical_function(self, t, A, T_2_ast, offset):
        return A*exp(-1/T_2_ast*t)+offset

    def _generate_fit_arguments(self, x, data):
        p0=[-(max(data)-min(data)), 1, max(data)]
        bounds =([-1, 0, -1], [1, 20, 1])
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
            ax.annotate("$T_{2E}=%.2f\pm%.2f \mu$s"%\
                (opt_params[1], err[1]),
                (mean(ax.get_xlim()),  .9*ax.get_ylim()[0]+.1*ax.get_ylim()[1]),
                bbox=bbox_props, ha="center")

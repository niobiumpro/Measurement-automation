
from lib2.IQPulseSequence import *
from lib2.VNATimeResolvedDispersiveMeasurement1D import *

class DispersiveDecay(VNATimeResolvedDispersiveMeasurement1D):

    def __init__(self, name, sample_name, vna_name, ro_awg, q_awg,
                q_lo_name, line_attenuation_db = 60):
        super().__init__(name, sample_name, vna_name, ro_awg, q_awg,
                    q_lo_name, line_attenuation_db)

        self._measurement_result = DispersiveDecayResult(name,
                    sample_name)
        self._sequence_generator = PulseBuilder.build_dispersive_decay_sequences
        self._swept_parameter_name = "readout_delay"

    def set_swept_parameters(self, readout_delays):
        super().set_swept_parameters(self._swept_parameter_name, readout_delays)


class DispersiveDecayResult(VNATimeResolvedDispersiveMeasurement1DResult):

    def _theoretical_function(self, t, A, T_1, offset):
        return A*exp(-1/T_1*t)+offset

    def _generate_fit_arguments(self, x, data):
        bounds =([-1e3, 0, -1e3], [1e3, 100, 1e3])
        p0 = [(max(data)-min(data))/2, 1, min(data)]
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
            ax.annotate("$T_1=%.2f\pm%.2f \mu$s"%\
                (opt_params[1], err[1]), (mean(ax.get_xlim()),
                .1*ax.get_ylim()[0]+.9*ax.get_ylim()[1]),
                bbox=bbox_props, ha="center")

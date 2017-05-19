
from lib2.VNATimeResolvedDispersiveMeasurement1D import *

class DispersiveAngularRamsey(VNATimeResolvedDispersiveMeasurement1D):

    def __init__(self, name, sample_name, vna_name, ro_awg_name, q_awg_name,
                q_lo_name, line_attenuation_db = 60):
        super().__init__(name, sample_name, vna_name, ro_awg_name, q_awg_name,
                    q_lo_name, line_attenuation_db)

        self._measurement_result = DispersiveAngularRamseyResult(name,
                    sample_name)

    def set_swept_parameters(self, ramsey_angles):
        super().set_swept_parameters("ramsey_angle", ramsey_angles)

    def _output_pulse_sequence(self, ramsey_delay):
        self._output_APE_sequence(ramsey_angle, 0)


class DispersiveAngularRamseyResult(VNATimeResolvedDispersiveMeasurement1DResult):

    def __init__(self, name, sample_name):
        super().__init__(name, sample_name)
        self._x_axis_units = "rad"

    def _theoretical_function(self, ramsey_angle, A, offset, phase_error):
        return A*cos(ramsey_angle+phase_error)+offset

    def _generate_fit_arguments(self, x, data):
        bounds =([-1, -1, -pi], [1, 1, pi])
        p0 = [(max(data)-min(data))/2, mean((max(data), min(data))), 0]
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
            ax.annotate("$|\phi_{err}| = %.2f\pm%.2f$ rad"%\
                (opt_params[2], err[2]), (mean(ax.get_xlim()),
                .9*ax.get_ylim()[0]+.1*ax.get_ylim()[1]),
                bbox=bbox_props, ha="center")

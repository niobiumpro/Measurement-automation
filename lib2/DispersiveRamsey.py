
from lib2.VNATimeResolvedDispersiveMeasurement1D import *

class DispersiveRamsey(VNATimeResolvedDispersiveMeasurement1D):

    def __init__(self, name, sample_name, vna_name, ro_awg_name, q_awg_name,
                q_lo_name, line_attenuation_db = 60):
        super().__init__(name, sample_name, vna_name, ro_awg_name, q_awg_name,
                    q_lo_name, line_attenuation_db)

        self._measurement_result = DispersiveRamseyResult(name,
                    sample_name)

    def set_swept_parameters(self, ramsey_delays):
        super().set_swept_parameters("ramsey_delay", ramsey_delays)

    def _output_pulse_sequence(self, ramsey_delay):
        self._output_ramsey_sequence(ramsey_delay)


class DispersiveRamseyResult(VNATimeResolvedDispersiveMeasurement1DResult):

    def _theoretical_function(self, t, A, T_2_ast, Delta_Omega, offset, phase):
        return A*exp(-1/T_2_ast*t)*cos(Delta_Omega*t+phase)+offset

    def _generate_fit_arguments(self, x, data):
        bounds =([-1, 0, 0, -1, -pi], [1, 100, 20*2*pi, 1, pi])
        p0 = [(max(data)-min(data))/2, 1, 1*2*pi,
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

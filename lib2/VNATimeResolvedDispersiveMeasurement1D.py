
from lib2.Measurement import *
from lib2.VNATimeResolvedDispersiveMeasurement import *
from lib2.IQPulseSequence import *

from scipy.optimize import curve_fit

class VNATimeResolvedDispersiveMeasurement1D(VNATimeResolvedDispersiveMeasurement):

    def set_fixed_parameters(self, vna_parameters, ro_awg_parameters,
            q_awg_parameters, qubit_frequency, pulse_sequence_parameters):

        vna_parameters["power"] = ro_awg_parameters["calibration"]\
            .get_radiation_parameters()["lo_power"]

        q_if_frequency = q_awg_parameters["calibration"] \
            .get_radiation_parameters()["if_frequency"]

        q_lo_parameters = {"power":q_awg_parameters["calibration"]\
            .get_radiation_parameters()["lo_power"],
            "frequency":qubit_frequency+q_if_frequency}

        res_freq = self._detect_resonator(vna_parameters)
        vna_parameters["freq_limits"] = (res_freq, res_freq)

        super().set_fixed_parameters(vna_parameters, q_lo_parameters,
            ro_awg_parameters, q_awg_parameters, pulse_sequence_parameters)

    def set_swept_parameters(self, par_name, par_values):
        swept_pars = {par_name:(self._output_pulse_sequence, par_values)}
        super().set_swept_parameters(**swept_pars)

    def _output_pulse_sequence(self, sequence_parameter):
        '''
        Should be implemented in a child class
        '''
        pass

class VNATimeResolvedDispersiveMeasurement1DResult(\
                    VNATimeResolvedDispersiveMeasurementResult):

    def __init__(self, name, sample_name):
        super().__init__(name, sample_name)
        self._context = VNATimeResolvedDispersiveMeasurementContext()
        self._fit_params = {}
        self._fit_errors = {}

    def _theoretical_function(self):
        '''
        Should be implemented in a child class
        '''
        pass

    def _generate_fit_arguments(self):
        '''
        Should be implemented in a child class.

        Returns:
        p0: array
            Initial parameters
        bounds: tuple of 2 arrays
            See scipy.optimize.curve_fit(...) documentation
        '''
        pass

    def fit(self, verbose=True):

        meas_data = self.get_data()
        data = meas_data["data"][meas_data["data"]!=0]
        if len(data)<5:
            return
        excitation_times = meas_data[self._parameter_names[0]]/1e3
        excitation_times = excitation_times[:len(data)]
        for name in self._data_formats.keys():
            line = self._data_formats[name][0](data)
            try:
                p0, bounds = self._generate_fit_arguments(excitation_times, line)
                opt_params, pcov = curve_fit(self._theoretical_function,
                            excitation_times, line, p0, bounds = bounds,
                            maxfev=10000)
                std = sqrt(abs(diag(pcov)))
                if (abs(opt_params)>std).all():
                    self._fit_params[name] = opt_params
                    self._fit_errors[name] = std
                else:
                    if verbose:
                        print("Fit of %s had low accuracy:\n popt: %s, std: %s"%\
                                (name, str(opt_params), str(std)))
            except RuntimeError:
                if verbose:
                    print("Fit of %s did not converge"%name)
                continue

    def _plot(self, axes, caxes):
        axes = dict(zip(self._data_formats.keys(), axes))

        data = self.get_data()
        if "data" not in data.keys():
            return

        for idx, name in enumerate(self._data_formats.keys()):
            Y = self._data_formats[name][0](data["data"])
            Y = Y[Y!=0]
            X = data[self._parameter_names[0]]/1e3
            ax = axes[name]
            ax.clear()
            ax.grid()
            ax.ticklabel_format(axis='y', style='sci', scilimits=(-2,2))
            ax.plot(X[:len(Y)], Y, "C%d"%idx, ls=":", marker="o",
                                                        markerfacecolor='none')
            ax.set_xlim(X[0], X[-1])
            ax.set_ylabel(self._data_formats[name][1])

        xlabel = self._parameter_names[0][0].upper()+\
                    self._parameter_names[0][1:].replace("_", " ")+\
                        " [$\mu$s]"
        axes["phase"].set_xlabel(xlabel)
        axes["imag"].set_xlabel(xlabel)

        self._plot_fit(axes)

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
            ax.annotate("$T_R=%.2f\pm%.2f \mu$s\n$\Omega_R/2\pi = %.2f\pm%.2f$ MHz"%\
                (opt_params[1], err[1], opt_params[2]/2/pi, err[2]/2/pi),
                (mean(ax.get_xlim()),  .9*ax.get_ylim()[0]+.1*ax.get_ylim()[1]),
                bbox=bbox_props, ha="center")


from drivers.KeysightAWG import PulseBuilder
from lib2.Measurement import *
from lib2.MeasurementResult import *

from scipy.optimize import curve_fit

class VNATimeResolvedMeasurementContext1D(ContextBase):

    def __init__(self, equipment = {}, pulse_sequence_parameters = {}, comment = ""):
        '''
        Parameters:
        -----------
        equipment: dict
            a dict containing dicts representing device parameters
        pulse_sequence_parameters: dict
            should contain all control parameters of the pulse sequence used in
            the measurement
        '''
        super().__init__(equipment, comment)
        self._pulse_sequence_parameters = pulse_sequence_parameters

    def get_pulse_sequence_parameters(self):
        return self._pulse_sequence_parameters

    def to_string(self):
        return "Pulse sequence parameters:\n"+str(self._pulse_sequence_parameters)+\
            super().to_string()


class VNATimeResolvedMeasurement1D(Measurement):

    def __init__(self, name, sample_name, vna_name, ro_awg_name, q_awg_name,
                q_lo_name, current_src_name, line_attenuation_db = 60):
        super().__init__(name, sample_name, devs_names=[vna_name, ro_awg_name,
                            q_awg_name, q_lo_name, current_src_name],
                            plot_update_interval=0.1)

        self._ro_awg = self._actual_devices[ro_awg_name]
        self._q_awg = self._actual_devices[q_awg_name]
        self._vna = self._actual_devices[vna_name]
        self._q_lo = self._actual_devices[q_lo_name]
        self._current_src = self._actual_devices[current_src_name]

    def set_fixed_parameters(self, vna_parameters, ro_awg_calibration,
                q_awg_calibration, qubit_frequency, current,
                pulse_sequence_parameters):
        vna_parameters["power"] = \
            ro_awg_calibration.get_radiation_parameters()["lo_power"]

        q_if_frequency = q_awg_calibration \
                    .get_radiation_parameters()["if_frequency"]

        q_lo_parameters = {"power":\
            q_awg_calibration.get_radiation_parameters()["lo_power"],
            "frequency":qubit_frequency+q_if_frequency}

        self._q_awg_calibration = q_awg_calibration
        self._q_pb = PulseBuilder(q_awg_calibration)
        self._ro_awg_calibration = ro_awg_calibration
        self._ro_pb = PulseBuilder(ro_awg_calibration)
        self._pulse_sequence_parameters = pulse_sequence_parameters

        self._measurement_result.get_context()\
                .get_equipment()["ro_awg"] = ro_awg_calibration
        self._measurement_result.get_context()\
                .get_equipment()["q_awg"] = q_awg_calibration
        self._measurement_result.get_context()\
                .get_pulse_sequence_parameters()\
                .update(pulse_sequence_parameters)

        self._q_lo.set_output_state("OFF")
        self._current_src.set_current(current)
        print("Detecting a resonator within provided frequency range of the VNA %s\
                    at current of %.2f mA"%(str(vna_parameters["freq_limits"]),
                        current*1e3), flush=True)
        res_freq, res_amp, res_phase = self._detect_resonator(vna_parameters)
        print("Detected frequency is %.5f GHz, at %.2f mU and %.2f degrees"%\
                    (res_freq/1e9, res_amp*1e3, res_phase/pi*180))

        vna_parameters["freq_limits"] = (res_freq, res_freq)
        self._q_lo.set_output_state("ON")

        super().set_fixed_parameters(vna=vna_parameters, q_lo=q_lo_parameters)

    def set_swept_parameters(self, par_name, par_values):
        swept_pars = {par_name:(self._output_pulse_sequence,
                                            par_values)}
        super().set_swept_parameters(**swept_pars)

    def _output_pulse_sequence(self, excitation_duration):
        '''
        Should be implemented in a child class
        '''
        pass

    def _recording_iteration(self):
        vna = self._vna
        vna.avg_clear(); vna.prepare_for_stb();
        vna.sweep_single(); vna.wait_for_stb();
        return mean(vna.get_sdata())

    def _detect_resonator(self, vna_parameters):
        self._vna.set_nop(200)
        self._vna.set_freq_limits(*vna_parameters["freq_limits"])
        self._vna.set_power(vna_parameters["power"])
        self._vna.set_bandwidth(vna_parameters["bandwidth"]*10)
        self._vna.set_averages(vna_parameters["averages"])
        return super()._detect_resonator()

class VNATimeResolvedMeasurementResult1D(MeasurementResult):

    def __init__(self, name, sample_name):
        super().__init__(name, sample_name)
        self._context = VNATimeResolvedMeasurementContext1D()
        self._fit_params = {}
        self._fit_errors = {}
        self._is_finished = False
        self._phase_units = "rad"
        self._data_formats = {
            "abs":(abs, "Transmission amplitude [a.u.]"),
            "real":(real,"Transmission real part [a.u.]"),
            "phase":(angle, "Transmission phase [%s]"%self._phase_units),
            "imag":(imag, "Transmission imaginary part [a.u.]")}

    def _prepare_figure(self):
        fig, axes = plt.subplots(2, 2, figsize=(15,7), sharex=True)
        axes = ravel(axes)
        return fig, axes, (None, None)

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
        pass
        meas_data = self.get_data()
        data = meas_data["data"][meas_data["data"]!=0]
        if len(data)<5:
            return
        excitation_times = meas_data[self._parameter_names[0]]/1e3
        excitation_times = excitation_times[:len(data)]
        for name in self._data_formats.keys():
            line = self._data_formats[name][0](data)
            try:
                p0, bounds = self._generate_fit_arguments(line)
                opt_params, pcov = curve_fit(self._theoretical_function,
                            excitation_times, line, p0, bounds = bounds)
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
            ax.plot(X[:len(Y)], Y, "C%d"%idx, ls=":",
                        marker="o",  markerfacecolor='none')
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

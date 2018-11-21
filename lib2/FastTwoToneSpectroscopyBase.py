'''
Parametric single-tone spectroscopy is perfomed with a Vector Network Analyzer
(VNA) for each parameter value which is set by a specific function that must be
passed to the SingleToneSpectroscopy class when it is created.
'''

from numpy import *
from lib2.SingleToneSpectroscopy import *
from datetime import datetime as dt
from lib2.Measurement import *
from scipy.optimize import curve_fit


class FastTwoToneSpectroscopyBase(Measurement):

    def __init__(self, name, sample_name, line_attenuation_db,
                 devs_aliases_map, plot_update_interval=5):

        super().__init__(name, sample_name, devs_aliases_map,
                         plot_update_interval)

        # devs_names = [vna_name, mw_src_name, current_src_name]
        # super().__init__(name, sample_name, devs_names)
        # self._vna = self._actual_devices[vna_name]
        # self._mw_src = self._actual_devices[mw_src_name]
        # self._current_src = self._actual_devices[current_src_name]

        self._measurement_result = TwoToneSpectroscopyResult(name, sample_name)
        self._interrupted = False
        self._base_parameter_setter = None
        self._base_parameter_name = None

        self._last_resonator_result = None

    def set_fixed_parameters(self, vna_parameters, mw_src_parameters, current=None,
                             voltage=None, detect_resonator=True, bandwidth_factor=1):

        if "ext_trig_channel" in mw_src_parameters.keys():
            # internal adjusted trigger parameters for vna
            vna_parameters["trig_per_point"] = True  # trigger output once per sweep point
            vna_parameters["pos"] = True  # positive edge
            vna_parameters["bef"] = False  # trigger sent before measurement is started

            # internal adjusted trigger parameters for microwave source
            mw_src_parameters["unit"] = "Hz"
            mw_src_parameters["InSweep_trg_src"] = "EXT"
            mw_src_parameters["sweep_trg_src"] = "BUS"

        self._bandwidth_factor = bandwidth_factor

        if voltage is None:
            self._base_parameter_setter = self._current_src.set_current
            base_parameter_value = current
            self._base_parameter_name = "Current [A]"
            msg1 = "at %.4f mA" % (current * 1e3)
        else:
            self._base_parameter_setter = self._voltage_src.set_voltage
            base_parameter_value = voltage
            self._base_parameter_name = "Voltage [V]"
            msg1 = "at %.1f V" % (voltage)

        self._base_parameter_setter(base_parameter_value)

        if detect_resonator:
            self._mw_src.set_output_state("OFF")
            msg = "Detecting a resonator within provided frequency range of the VNA %s \
                            " % (str(vna_parameters["freq_limits"]))
            print(msg + msg1, flush=True)
            res_freq, res_amp, res_phase = self._detect_resonator(vna_parameters, plot=True)
            print("Detected frequency is %.5f GHz, at %.2f mU and %.2f degrees" % (
            res_freq / 1e9, res_amp * 1e3, res_phase / pi * 180))
            vna_parameters["freq_limits"] = (res_freq, res_freq)
            self._measurement_result.get_context() \
                .get_equipment()["vna"] = vna_parameters
            self._mw_src.set_output_state("ON")

        super().set_fixed_parameters(vna=vna_parameters, mw_src=mw_src_parameters)

    def _detect_resonator(self, vna_parameters, plot=True):
        self._vna.set_nop(100)
        self._vna.set_freq_limits(*vna_parameters["freq_limits"])
        if "res_find_power" in vna_parameters.keys():
            self._vna.set_power(vna_parameters["res_find_power"])
        else:
            self._vna.set_power(vna_parameters["power"])
        if "res_find_nop" in vna_parameters.keys():
            self._vna.set_nop(vna_parameters["res_find_nop"])
        else:
            self._vna.set_nop(vna_parameters["nop"])
        self._vna.set_bandwidth(vna_parameters["bandwidth"] * self._bandwidth_factor)
        self._vna.set_averages(vna_parameters["averages"])
        result = super()._detect_resonator(plot)
        self._vna.do_set_power(vna_parameters["power"])
        self._vna.do_set_power(vna_parameters["nop"])
        return result

    def _record_data(self):

        par_names = self._swept_pars_names
        parameters_values = []
        parameters_idxs = []
        done_iterations = 0
        start_time = self._measurement_result.get_start_datetime()

        parameters_values = \
            [self._swept_pars[parameter_name][1] for parameter_name in par_names]
        parameters_idxs = \
            [list(range(len(self._swept_pars[parameter_name][1]))) for parameter_name in par_names]

        cycle_par_idxs = [list(range(len(self._swept_pars[parameter_name][1]))) for parameter_name in par_names if
                          parameter_name != "Frequency [Hz]"]
        cycle_par_vals = [self._swept_pars[parameter_name][1] for parameter_name in par_names if
                          parameter_name != "Frequency [Hz]"]
        raw_data_shape = \
            [len(indices) for indices in cycle_par_idxs]
        total_iterations = reduce(mul, [len(indices) for indices in cycle_par_idxs], 1)

        for idx_group, values_group in zip(product(*cycle_par_idxs), product(*cycle_par_vals)):

            self._call_setters(values_group)

            # This should be implemented in child classes:
            data = self._recording_iteration()

            if done_iterations == 0:
                try:
                    self._raw_data = zeros(raw_data_shape + [len(data)], dtype=complex_)
                except TypeError:  # data has no __len__ attribute
                    self._raw_data = zeros(raw_data_shape, dtype=complex_)
            self._raw_data[idx_group] = data

            # This may need to be extended in child classes:
            measurement_data = self._prepare_measurement_result_data(par_names, parameters_values)
            self._measurement_result.set_data(measurement_data)

            done_iterations += 1

            avg_time = (dt.now() - start_time).total_seconds() / done_iterations
            time_left = self._format_time_delta(avg_time * (total_iterations - done_iterations))

            formatted_values_group = \
                '[' + "".join(["%s: %.2e, " % (par_names[idx], value) \
                               for idx, value in enumerate(values_group)])[:-2] + ']'

            print("\rTime left: " + time_left + ", %s" % formatted_values_group + \
                  ", average cycle time: " + str(round(avg_time, 2)) + " s       ",
                  end="", flush=True)

            if self._interrupted:
                self._interrupted = False
                return
        self._measurement_result.set_recording_time(dt.now() - start_time)
        print("\nElapsed time: %s" % \
              self._format_time_delta((dt.now() - start_time) \
                                      .total_seconds()))
        self._measurement_result.set_is_finished(True)

    def _recording_iteration(self):
        vna = self._vna
        vna.avg_clear()
        vna.prepare_for_stb()
        vna.sweep_single()
        vna.wait_for_stb()
        data = vna.get_sdata()
        return data

    def _base_setter(self, value):
        self._base_parameter_setter(value)
        self._mw_src.send_sweep_trigger()  # telling mw_src to be ready to start

    def _adaptive_setter(self, value):
        self._base_parameter_setter(value)
        vna_parameters = self._fixed_pars["vna"]
        vna_parameters["freq_limits"] = self._resonator_area

        self._mw_src.set_output_state("OFF")
        # print("\rDetecting a resonator within provided frequency range of the VNA %s\
        #            "%(str(vna_parameters["freq_limits"])), flush=True, end="")

        res_result = self._detect_resonator(vna_parameters, plot=False)

        if res_result is None:
            print("Failed to fit resonator, trying to use last successful fit, current = ", value, " A")
            if self._last_resonator_result is None:
                print("no successful fit is present, terminating")
                return None
            else:
                res_result = self._last_resonator_result
        else:
            self._last_resonator_result = res_result

        res_freq, res_amp, res_phase = self._last_resonator_result

        # print("\rDetected frequency is %.5f GHz, at %.2f mU and %.2f \
        #            degrees"%(res_freq/1e9, res_amp*1e3, res_phase/pi*180), end="")
        self._mw_src.set_output_state("ON")
        vna_parameters["freq_limits"] = (res_freq, res_freq)
        self._vna.set_parameters(vna_parameters)
        self._mw_src.send_sweep_trigger()  # telling mw_src to be ready to start


class TwoToneSpectroscopyResult(SingleToneSpectroscopyResult):

    def __init__(self, name, sample_name):
        super().__init__(name, sample_name)
        self._context = ContextBase()
        self._is_finished = False
        self._phase_units = "rad"
        self._annotation_bbox_props = dict(boxstyle="round", fc="white",
                                           ec="black", lw=1, alpha=0.5)

    def _tr_spectrum(self, parameter_value, parameter_value_at_sweet_spot, frequency, period):
        return frequency * sqrt(cos((parameter_value - parameter_value_at_sweet_spot) / period))

    def _lorentzian_peak(self, frequency, amplitude, offset, res_frequency, width):
        return amplitude * (0.5 * width) ** 2 / ((frequency - res_frequency) ** 2 + (0.5 * width) ** 2) + offset

    def _find_peaks(self, freqs, data):
        peaks = []
        for row in data:
            try:
                popt = curve_fit(self._lorentzian_peak,
                                 freqs, row, p0=(ptp(row), median(row),
                                                 freqs[argmax(row)], 10e6))[0]
                peaks.append(popt[2])
            except:
                peaks.append(freqs[argmax(row)])
        return array(peaks)

    def find_transmon_spectrum(self, axes, parameter_limits=(0, -1),
                               format="abs"):
        parameter_name = self._parameter_names[0]
        data = self.get_data()
        x = data[parameter_name][parameter_limits[0]:parameter_limits[1]]
        freqs = data[self._parameter_names[1]]
        Z = data["data"][parameter_limits[0]:parameter_limits[1]]

        if format == "abs":
            Z = abs(Z)
            annotation_ax_idx = 0
        elif format == "angle":
            Z = angle(Z)
            annotation_ax_idx = 1

        y = self._find_peaks(freqs, Z)

        try:
            popt = curve_fit(self._tr_spectrum, x, y, p0=(mean(x), max(y), ptp(x)))[0]
            annotation_string = parameter_name + " sweet spot at: " + self._latex_float(popt[0])

            for ax in axes:
                h_pos = mean(ax.get_xlim())
                v_pos = .1 * ax.get_ylim()[0] + .9 * ax.get_ylim()[1]
                ax.plot(x, y / 1e9, ".", color="C2")
                ax.plot(x, self._tr_spectrum(x, *popt) / 1e9)
                ax.plot([popt[0]], [popt[1] / 1e9], "+")

            axes[annotation_ax_idx].annotate(annotation_string, (h_pos, v_pos),
                                             bbox=self._annotation_bbox_props, ha="center")
            return popt[0], popt[1]
        except Exception as e:
            print("Could not find transmon spectral line" + str(e))

    def _prepare_measurement_result_data(self, data):
        return data[self._parameter_names[0]], data["Frequency [Hz]"] / 1e9, data["data"]

    def _prepare_data_for_plot(self, data):
        s_data = data["data"]
        parameter_list = data[self._parameter_names[0]]
        return parameter_list, data["Frequency [Hz]"]/1e9, s_data
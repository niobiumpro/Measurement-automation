

'''
Paramatric single-tone spectroscopy is perfomed with a Vector Network Analyzer
(VNA) for each parameter value which is set by a specific function that must be
passed to the SingleToneSpectroscopy class when it is created.
'''

from numpy import *
from lib2.SingleToneSpectroscopy import *
from datetime import datetime as dt
from lib2.Measurement import *
from scipy.optimize import curve_fit

class TwoToneSpectroscopyBase(Measurement):

    def __init__(self, name, sample_name, line_attenuation_db,
                    vna_name, mw_src_name, current_src_name):
        devs_names = [vna_name, mw_src_name, current_src_name]
        super().__init__(name, sample_name, devs_names)
        self._vna = self._actual_devices[vna_name]
        self._mw_src = self._actual_devices[mw_src_name]
        self._current_src = self._actual_devices[current_src_name]

        self._measurement_result = TwoToneSpectroscopyResult(name,
                    sample_name)
        self._interrupted = False

    def set_fixed_parameters(self, vna_parameters, mw_src_parameters, current,
        detect_resonator=True):

        self._current_src.set_current(current)

        if detect_resonator:
            self._mw_src.set_output_state("OFF")
            print("Detecting a resonator within provided frequency range of the VNA %s \
                        at %.2f mA"%(str(vna_parameters["freq_limits"]),
                            current*1e3), flush=True)
            res_freq, res_amp, res_phase = self._detect_resonator(vna_parameters)
            print("Detected frequency is %.5f GHz, at %.2f mU and %.2f degrees"%(res_freq/1e9, res_amp*1e3, res_phase/pi*180))
            vna_parameters["freq_limits"] = (res_freq, res_freq)
            self._measurement_result.get_context() \
                .get_equipment()["vna"] = vna_parameters
            self._mw_src.set_output_state("ON")

        super().set_fixed_parameters(vna=vna_parameters, mw_src=mw_src_parameters)

    def _detect_resonator(self, vna_parameters, plot=True, bandwidth_factor = 10):
        self._vna.set_nop(400)
        self._vna.set_freq_limits(*vna_parameters["freq_limits"])
        self._vna.set_power(vna_parameters["power"])
        self._vna.set_bandwidth(vna_parameters["bandwidth"]*bandwidth_factor)
        self._vna.set_averages(vna_parameters["averages"])
        return super()._detect_resonator(plot)

    def _recording_iteration(self):
        vna = self._vna
        vna.avg_clear(); vna.prepare_for_stb();
        vna.sweep_single(); vna.wait_for_stb();
        data = vna.get_sdata();
        return mean(data)

class TwoToneSpectroscopyResult(SingleToneSpectroscopyResult):

    def __init__(self, name, sample_name):
        super().__init__(name, sample_name)
        self._context = ContextBase()
        self._is_finished = False
        self._phase_units = "rad"
        self._annotation_bbox_props = dict(boxstyle="round", fc="white",
                ec="black", lw=1, alpha=0.5)

    def _tr_spectrum(self, current, sweet_spot_current, frequency, period):
        return frequency*sqrt(cos((current-sweet_spot_current)/period))

    def find_transmon_spectrum(self, axes):
        data = self.get_data()
        max_idcs = argmax(abs(data["data"]), 1)
        y = data["Frequency [Hz]"][max_idcs]
        x = data[self._parameter_names[0]]
        try:
            popt = curve_fit(self._tr_spectrum, x, y, p0=(mean(x), max(y), ptp(x)))[0]
            annotation_string = "Sweet spot at: %.2e $\mu$A"%(popt[0]*1e6)
            for ax in axes:
                h_pos = mean(ax.get_xlim())
                v_pos = .1*ax.get_ylim()[0]+.9*ax.get_ylim()[1]
                ax.plot(x, y/1e9, ".")
                ax.plot(x, self._tr_spectrum(x, *popt)/1e9)
                ax.annotate(annotation_string, (h_pos, v_pos),
                            bbox=self._annotation_bbox_props, ha="center")
                return popt[0]
        except Exception as e:
            print("Could not find transmon spectral line"+str(e))

    def _prepare_data_for_plot(self, data):
        return data[self._parameter_names[0]], data["Frequency [Hz]"]/1e9, data["data"]

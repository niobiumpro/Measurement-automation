

'''
Paramatric single-tone spectroscopy is perfomed with a Vector Network Analyzer
(VNA) for each parameter value which is set by a specific function that must be
passed to the SingleToneSpectroscopy class when it is created.
'''


from numpy import *
from lib2.MeasurementResult import *
from datetime import datetime as dt
from matplotlib import pyplot as plt, colorbar
from resonator_tools import circuit
from lib2.Measurement import *



class SingleToneSpectroscopy(Measurement):
    '''
    Class provides all the necssary methods for single-tone spectrscopy with VNA.
    Current is changed with Yokohawa GS-210

    ---------------
    Methods:
         -- __init__(self, name, sample_name, parameter_name,parameter_setter, line_attenuation_db = 60, vna_name="vna2")
         -- setup_control_parameters(self, vna_parameters,parameter_values)
         -- _record_data(self)
         Class SingleToneSpectroscopyResult(MeasurementResult):
            -- __init__(self, name, sample_name, parameter_name)
            --  _prepare_figure(self)
            --  set_phase_units(self, units)
            -- _plot(self, axes, caxes):
            -- _prepare_data_for_plot(self, data):
            -- _prepare_data_for_plot(self, data):
            --  save(self)
            --  remove_delay(self)
            --  _remove_delay(self,frequencies, s_data)
    ----------------
    '''

    def __init__(self, name, sample_name, line_attenuation_db = 60, **devs_aliases_map):
        super().__init__(name, sample_name, list(devs_aliases_map.values()))

        self._devs_aliases = list(devs_aliases_map.keys())
        for alias, dev_name in devs_aliases_map.items():
            self.__setattr__("_"+alias, self._actual_devices[dev_name])

        self._measurement_result = SingleToneSpectroscopyResult(name,
                    sample_name)

    def set_fixed_parameters(self, vna_parameters):
        '''
        SingleToneSpectroscopy only requires vna parameters in format
        {"bandwidth":int, ...}
        '''
        super().set_fixed_parameters(vna = vna_parameters)
        self._frequencies = linspace(*vna_parameters["freq_limits"],\
                        vna_parameters["nop"])

    def set_swept_parameters(self, swept_parameter):
        '''
        SingleToneSpectroscopy only takes one swept parameter in format
        {"parameter_name":(setter, values)}
        '''
        super().set_swept_parameters(**swept_parameter)
        par_name = list(swept_parameter.keys())[0]
        self._measurement_result.set_parameter_name(par_name)

    def _recording_iteration(self):
        vna = self._vna
        vna.avg_clear(); vna.prepare_for_stb(); vna.sweep_single(); vna.wait_for_stb();
        return vna.get_sdata()

    def _fill_measurement_result(self, parameter_names, parameters_values):
        measurement_data = super()._fill_measurement_result(parameter_names, parameters_values)
        measurement_data["frequency"] = self._frequencies
        self._measurement_result.set_data(measurement_data)
    #
    # def _record_data(self):
    #     super()._record_data()
    #
    #     vna = self._vna
    #     vna.set_parameters(self._vna_parameters)
    #
    #     raw_s_data = zeros((len(self._parameter_values),
    #                     self._vna_parameters["nop"]), dtype=complex_)
    #
    #     done_sweeps = 0
    #     total_sweeps = len(self._parameter_values)
    #     vna.sweep_hold()
    #
    #     for idx, value in enumerate(self._parameter_values):
    #         if self._interrupted:
    #             self._interrupted = False
    #             self._vna.set_parameters(self._pre_measurement_vna_parameters)
    #             return
    #
    #         self._parameter_setter(value)
    #         vna.avg_clear(); vna.prepare_for_stb(); vna.sweep_single(); vna.wait_for_stb();
    #         raw_s_data[idx]=vna.get_sdata()
    #         raw_data = {"frequency":self._frequencies,
    #                     self._parameter_name:self._parameter_values,
    #                     "s_data":raw_s_data}
    #         self._measurement_result.set_data(raw_data)
    #         done_sweeps += 1
    #         avg_time = (dt.now() - self._measurement_result.get_start_datetime())\
    #                                         .total_seconds()/done_sweeps
    #         print("\rTime left: "+self._format_time_delta(avg_time*(total_sweeps-done_sweeps))+\
    #                 ", %s: "%self._parameter_name+\
    #                 "%.3e"%value+", average cycle time: "+\
    #                 str(round(avg_time, 2))+" s          ",
    #                 end="", flush=True)
    #
    #     self._vna.set_parameters(self._pre_measurement_vna_parameters)
    #     self._measurement_result.set_is_finished(True)


class SingleToneSpectroscopyResult(MeasurementResult):

    def __init__(self, name, sample_name):
        super().__init__(name, sample_name)
        self._context = ContextBase()
        self._is_finished = False
        self._phase_units = "rad"

    def set_parameter_name(self, parameter_name):
        self._parameter_name = parameter_name

    def _prepare_figure(self):
        fig, axes = plt.subplots(1, 2, figsize=(15,7), sharey=True)
        ax_amps, ax_phas = axes
        ax_amps.ticklabel_format(axis='x', style='sci', scilimits=(-2,2))
        ax_amps.set_ylabel("Frequency [GHz]")
        ax_amps.set_xlabel(self._parameter_name[0].upper()+self._parameter_name[1:])
        ax_phas.ticklabel_format(axis='x', style='sci', scilimits=(-2,2))
        ax_phas.set_xlabel(self._parameter_name[0].upper()+self._parameter_name[1:])
        cax_amps, kw = colorbar.make_axes(ax_amps)
        cax_phas, kw = colorbar.make_axes(ax_phas)
        cax_amps.set_title("$|S_{21}|$")
        cax_phas.set_title("$\\angle S_{21}$ [%s]"%self._phase_units)

        return fig, axes, (cax_amps, cax_phas)

    def set_phase_units(self, units):
        '''
        Sets the units of the phase in the plots

        Parameters:
        -----------
        units: "rad" or "deg"
            units in which the phase will be displayed
        '''
        if units in ["deg", "rad"]:
            self._phase_units = units
        else:
            print("Phase units invalid")

    def _plot(self, axes, caxes):
        ax_amps, ax_phas = axes
        cax_amps, cax_phas = caxes

        data = self.get_data()
        if "data" not in data.keys():
            return

        XX, YY, Z = self._prepare_data_for_plot(data)

        max_amp = max(abs(Z)[abs(Z)!=0])
        min_amp = min(abs(Z)[abs(Z)!=0])
        amps_map = ax_amps.pcolormesh(XX, YY, abs(Z).T, cmap="RdBu_r",
                                    vmax=max_amp, vmin=min_amp)
        plt.colorbar(amps_map, cax = cax_amps)

        phases = unwrap(unwrap(angle(Z))).T
        phases = phases if self._phase_units == "rad" else phases*180/pi
        max_phas = max(phases[phases!=0])
        min_phas = min(phases[phases!=0])
        phas_map = ax_phas.pcolormesh(XX, YY, phases,
                    cmap="RdBu_r", vmin=min_phas, vmax=max_phas)
        plt.colorbar(phas_map, cax = cax_phas)
        ax_amps.grid()
        ax_phas.grid()
        ax_amps.axis("tight")
        ax_phas.axis("tight")

    def _prepare_data_for_plot(self, data):
        s_data = self._remove_delay(data["frequency"], data["data"])
        #s_data = data["s_data"]
        XX, YY = generate_mesh(data[self._parameter_name],
                        data["frequency"]/1e9)
        return XX, YY, s_data

    def save(self):
        super().save()
        self.visualize()
        plt.savefig(self.get_save_path()+self._name+".png", bbox_inches='tight')
        plt.close("all")

    def remove_delay(self):
        copy = self.copy()
        s_data, frequencies = copy.get_data()["data"], copy.get_data()["frequencies"]
        copy.get_data()["data"] = self._remove_delay(frequencies, s_data)
        return copy

    def _remove_delay(self,frequencies, s_data):
        phases = unwrap(angle(s_data*exp(2*pi*1j*50e-9*frequencies)))
        k, b = polyfit(frequencies, phases[0], 1)
        phases = phases - k*frequencies - b
        corr_s_data = abs(s_data)*exp(1j*phases)
        corr_s_data[abs(corr_s_data)<1e-14] = 0
        return corr_s_data

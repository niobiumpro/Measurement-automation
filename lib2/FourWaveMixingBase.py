from numpy import *
from datetime import datetime as dt
from matplotlib import pyplot as plt, colorbar

from lib2.MeasurementResult import *
from lib2.Measurement import *
from lib2.SingleToneSpectroscopy import *

class FourWaveMixingBase(Measurement):
    '''
    Class for wave mixing measurements.

    This one must do:
        create Measurement object, set up all devices and take them from the class;
        set up all the parameters
        make measurements:
         -- sweep power/frequency of one/another/both of generators
            and/or central frequency of EXA and measure single trace / list sweep for certain frequencies
         --


    '''
    def __init__(self, name, sample_name, line_attenuation_db, **devs_aliases):
        '''
        name: name of current measurement
        list_devs_names: {exa_name: default_name, src_plus_name: default_name,
                             src_minus_name: default_name, vna_name: default_name, current_name: default_name}
        sample_name: name of measured sample

        vna and current source is optional

        '''
        super().__init__(name, sample_name, list(devs_aliases.values()))
        self._devs_aliases = list(devs_aliases.keys())

        for alias, name in devs_aliases.items():
            self.__setattr__("_"+alias,self._actual_devices[name])

    def sources_on(src_plus, src_minus):
        for src in [src_plus, src_minus]:
            src.set_output_state('ON')

    def srcs_power_calibration(self):


    def set_fixed_parameters(self, exa_parameters, delta):
        '''
        FourWaveMixingBase requires following parameters
        'exa': bandwidth, centerfreq, span, averages, avg_status
         delta is
        '''
        self._exa_pars = exa_pars
        self._src_plus_freq = exa_pars['centerfreq'] + delta
        self._src_minus_freq = exa_pars['centrerfreq'] - delta

        super().set_fixed_parameters(exa = exa_pars, src_plus = src_plus_pars,
                                                    src_minus = src_minus_pars)


    def _recording_iteration(self):
        '''
        is to be implemented in ancestor classes
        '''
        # pass
        return self._exa.make_trace_get_data()



class FourWaveMixingResult(MeasurementResult):

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

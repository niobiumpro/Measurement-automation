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

        for alias, dev_name in devs_aliases.items():
            self.__setattr__("_"+alias,self._actual_devices[dev_name])

        self._measurement_result = FourWaveMixingResult(name,
                    sample_name)

    def _sources_on(self):
        for src in [self._src_plus, self._src_minus]:
            src.set_output_state('ON')

    def _sources_off(self):
            for src in [self._src_plus, self._src_minus]:
                src.set_output_state('OFF')

    def srcs_power_calibration(self):
        '''
        To define powers to set in setter (not implemented yet)
        '''
        pass


    def set_fixed_parameters(self, exa_parameters, delta, power_plus=None, power_minus=None):
        '''
        FourWaveMixingBase requires following parameters
        'exa': bandwidth, centerfreq, span, averages, avg_status
         delta is half of distance between two generators
        '''
        self._exa_pars = exa_parameters
        self._delta = delta
        self._src_plus_pars = {"frequency": exa_parameters['centerfreq'] + delta}
        self._src_minus_pars = {"frequency":  exa_parameters['centerfreq'] - delta}
        if power_plus is not None:
            self._src_plus_pars["power"] = power_plus
        if power_minus is not None:
            self._src_minus_pars["power"] = power_minus
        freq_limits = (exa_parameters["centerfreq"] - exa_parameters["span"]/2, \
                        exa_parameters["centerfreq"] + exa_parameters["span"]/2)
        self._frequencies = linspace(*freq_limits, exa_parameters["nop"])
        super().set_fixed_parameters(exa = exa_parameters, src_plus = self._src_plus_pars,
                                                    src_minus = self._src_minus_pars)

    def powers_equal_setter_with_offset(self, power): #powers are two floats, plus and minus
        '''
        Construct a function to set two powers simultaneously
        '''
        power_plus = power
        power_minus = power+10.6
        self._src_plus.set_power(power_plus)
        self._src_minus.set_power(power_minus)

    def powers_plus_setter(self,power_plus):
        self._src_plus.set_power(power_plus)

    def powers_minus_setter(self,power_minus):
        self._src_minus.set_power(power_minus)

    def set_swept_parameters(self, actual_setter, powers): # powers are two lists, like [power_plus, power_minus]
        '''
        FourWaveMixingBase only takes one swept parameter in format
        {"parameter_name":(setter, values)}
        '''
        self._actual_setter = actual_setter
        self._powers = powers
        swept_parameters =  {"powers at $\\omega_{p}$": (self._actual_setter, self._powers)}
        super().set_swept_parameters(**swept_parameters)
        par_name = list(swept_parameters.keys())[0]
        self._measurement_result.set_parameter_name(par_name)
        self._sources_on()

    def _fill_measurement_result(self, parameter_names, parameters_values):
        measurement_data = super()._fill_measurement_result(parameter_names, parameters_values)
        measurement_data["frequency"] = self._frequencies
        self._measurement_result.set_data(measurement_data)

    def _recording_iteration(self):
        '''
        is to be implemented in ancestor classes
        '''
        # pass
        return self._exa.make_sweep_get_data()



class FourWaveMixingResult(MeasurementResult):

    def __init__(self, name, sample_name):
        super().__init__(name, sample_name)
        self._context = ContextBase(comment = input('Enter your comment: '))
        self._is_finished = False
        self._peaks_indices = []
        self._colors = []
        self._XX = None
        self._YY = None



    def set_parameter_name(self, parameter_name):
        self._parameter_name = parameter_name

    def _prepare_figure(self):
        self._last_tr = None
        self._peaks_last_tr = None
        fig = plt.figure(figsize = (18,6))
        ax_trace = plt.subplot2grid((4, 8), (0, 0), colspan = 4, rowspan = 1)
        ax_map = plt.subplot2grid((4, 8), (1, 0), colspan = 4, rowspan = 3)
        ax_peaks = plt.subplot2grid((4, 8), (0, 4), colspan = 4, rowspan = 4)
        plt.tight_layout()
        ax_map.ticklabel_format(axis='x', style='plain', scilimits=(-2,2))
        ax_map.set_ylabel("Frequency, kHz")
        ax_map.set_xlabel(self._parameter_name[0].upper()+self._parameter_name[1:])
        ax_trace.ticklabel_format(axis='x', style='sci', scilimits=(-2,2))
        ax_trace.set_xlabel("Frequency, Hz")
        ax_trace.set_ylabel("Emission power, dBm")
        ax_peaks.set_xlabel("Input power, dBm")
        ax_peaks.set_ylabel("Emission power, dBm")

        ax_map.autoscale_view(True,True,True)
        plt.tight_layout()

        cax, kw = colorbar.make_axes(ax_map, fraction=0.05, anchor=(0.0,1.0))
        cax.set_title("$P$,dBm")

        return fig, (ax_trace, ax_map, ax_peaks), (cax,)

    def _plot(self, axes, cax):
        ax_trace, ax_map, ax_peaks = axes
        cax = cax[0]

        data = self.get_data()
        if "data" not in data.keys():
            return

        XX, YY, Z, P = self._prepare_data_for_plot(data)

        max_pow = max(Z[Z != 0])
        min_pow = min(Z[Z != 0])
        av_pow = average(Z[Z != 0])
        pow_map = ax_map.pcolormesh(XX, YY, Z.T, cmap="hot",
                                    vmax=max_pow, vmin=av_pow)
        plt.colorbar(pow_map, cax = cax)
        last_trace_data = Z[Z!=0][-(len(data["frequency"])):]
        if self._last_tr is not None:
            self._last_tr.remove()
        self._last_tr = ax_trace.plot(data["frequency"]/1e3,
                        last_trace_data, 'b').pop(0)

        N_peaks  = len(P[:,0])
        if self._peaks_last_tr is not None:
            for l in self._peaks_last_tr:
                l.pop(0).remove()
        self._peaks_last_tr = [ax_peaks.plot(data["powers at $\\omega_{p}$"],
                        P[i,:], '-',linewidth=1.5,
                         color=self._colors[i]) for i in range(N_peaks)]
        #plt.gcf().canvas.draw()
        #print(self._peaks_last_tr, flush=True)
        ax_trace.set_ylim([average(last_trace_data), max(last_trace_data)])
        ax_peaks.set_ylim([P.min(),P[nonzero(P)].max()])

        ax_map.grid('on')
        ax_trace.grid('on')
        ax_trace.axis("tight")



    def _prepare_data_for_plot(self, data):
        if self._peaks_indices == []:
            max_order = 25
            con_eq = self.get_context().get_equipment()
            nop = int(con_eq["exa"]["nop"])
            span = con_eq["exa"]["span"]
            center_point = (nop-1)/2

            delta = (con_eq["src_plus"]["frequency"] - \
                    con_eq["src_minus"]["frequency"])/2
            delta_index = int(delta/span*(nop-1))
            for i in range(-max_order,max_order+2,2):
                self._colors.append((abs(i)/max_order, 0, (max_order-abs(i))/max_order))
                self._peaks_indices.append(center_point + i*delta_index)
        power_data = real(data["data"])
        peaks_data = [power_data[:,i] for i in self._peaks_indices]
        if self._XX is None and self._YY is None:
            self._XX, self._YY = generate_mesh(data[self._parameter_name], data["frequency"]/1e3)
        return self._XX, self._YY, power_data, array(peaks_data)

    def save(self):
        super().save()
        self.visualize()
        plt.savefig(self.get_save_path()+self._name+".png", bbox_inches='tight')
        plt.close("all")


    def _remove_delay(self,frequencies, s_data):
        phases = unwrap(angle(s_data*exp(2*pi*1j*50e-9*frequencies)))
        k, b = polyfit(frequencies, phases[0], 1)
        phases = phases - k*frequencies - b
        corr_s_data = abs(s_data)*exp(1j*phases)
        corr_s_data[abs(corr_s_data)<1e-14] = 0
        return corr_s_data

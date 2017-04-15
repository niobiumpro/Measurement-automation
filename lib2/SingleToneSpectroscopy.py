

'''
Paramatric single-tone spectroscopy is perfomed with a Vector Network Analyzer
(VNA) for each parameter value which is set by a specific function that must be
passed to the SingleToneSpectroscopy class when it is created.
'''



from numpy import *
from lib2.MeasurementResult import *
from datetime import datetime as dt
from matplotlib import pyplot as plt, colorbar
from threading import Thread


def format_time_delta(delta):
	hours, remainder = divmod(delta, 3600)
	minutes, seconds = divmod(remainder, 60)
	return '%s h %s m %s s' % (int(hours), int(minutes), round(seconds, 2))

class SingleToneSpectroscopy():

    def __init__(self, name, sample_name, vna, parameter_name,
            parameter_setter, line_attenuation_db = 60):

        self._name = name
        self._sample_name = sample_name
        self._vna = vna
        self._parameter_name = parameter_name.lower()
        self._parameter_setter = parameter_setter
        self._measurement_result = SingleToneSpectroscopyResult(name,
                    sample_name, parameter_name)

        self._interrupted = False

    def setup_control_parameters(self, vna_parameters, parameter_values):
        self._vna_parameters = vna_parameters
        self._parameter_values = parameter_values
        self._pre_measurement_vna_parameters = {"bandwidth":self._vna.get_bandwidth(),
                                          "nop":self._vna.get_nop(),
                                          "power":self._vna.get_power(),
                                          "averages":self._vna.get_averages(),
                                          "freq_limits":self._vna.get_freq_limits()}
        start, stop = vna_parameters["freq_limits"]
        self._frequencies = linspace(start, stop, vna_parameters["nop"])

    def _setup_vna(self, vna_parameters):
        self._vna.set_bandwidth(vna_parameters["bandwidth"])
        self._vna.set_averages(vna_parameters["averages"])
        self._vna.set_power(vna_parameters["power"])
        self._vna.set_nop(vna_parameters["nop"])
        self._vna.set_freq_limits(*vna_parameters["freq_limits"])

    def launch(self):
        plt.ion()

        start_datetime = dt.now()
        print("Started at: ", start_datetime.ctime())

        self._measurement_result.set_start_datetime(start_datetime)
        self._measurement_result.get_context() \
                                .get_equipment()["vna"] = self._vna_parameters

        self._setup_vna(self._vna_parameters)
        t = Thread(target=self._record_data)
        t.start()
        try:
            while not self._measurement_result.is_finished():
                self._measurement_result._visualize_dynamic()
                plt.pause(1)
        except KeyboardInterrupt:
            self._interrupted = True

        self._measurement_result.finalize()
        return self._measurement_result


    def _record_data(self):
        vna = self._vna
        start_datetime = self._measurement_result.get_start_datetime()

        raw_s_data = zeros((len(self._parameter_values), self._vna_parameters["nop"]), dtype=complex_)

        done_sweeps = 0
        total_sweeps = len(self._parameter_values)
        vna.sweep_hold()

        for idx, value in enumerate(self._parameter_values):
            if self._interrupted:
                self._interrupted = False
                return

            self._parameter_setter(value)
            vna.avg_clear(); vna.prepare_for_stb(); vna.sweep_single(); vna.wait_for_stb();
            raw_s_data[idx]=vna.get_sdata()
            raw_data = {"frequencies":self._frequencies,
                        self._parameter_name+"s":self._parameter_values,
                        "s_data":raw_s_data}
            self._measurement_result.set_data(raw_data)
            done_sweeps += 1
            avg_time = (dt.now() - start_datetime).total_seconds()/done_sweeps
            print("\rTime left: "+format_time_delta(avg_time*(total_sweeps-done_sweeps))+\
                    ", parameter value: "+\
                    "%.3e"%value+", average cycle time: "+\
                    str(round(avg_time, 2))+" s          ",
                    end="", flush=True)

        self._measurement_result.set_is_finished(True)


class SingleToneSpectroscopyResult(MeasurementResult):

    def __init__(self, name, sample_name, parameter_name):
        super().__init__(name, sample_name)
        self._parameter_name = parameter_name
        self._context = ContextBase()
        self._is_finished = False

    def _prepare_figure(self):
        fig, axes = plt.subplots(1, 2, figsize=(15,7), sharey=True)
        ax_amps, ax_phas = axes
        ax_amps.ticklabel_format(axis='x', style='sci', scilimits=(-2,2))
        ax_amps.set_ylabel("Frequency [GHz]")
        ax_amps.set_xlabel(self._parameter_name[0].upper()+self._parameter_name[1:])
        ax_phas.ticklabel_format(axis='x', style='sci', scilimits=(-2,2))
        ax_phas.set_xlabel(self._parameter_name[0].upper()+self._parameter_name[1:])
        ax_amps.grid()
        ax_phas.grid()
        cax_amps, kw = colorbar.make_axes(ax_amps)
        cax_phas, kw = colorbar.make_axes(ax_phas)
        cax_amps.set_title("$|S_{21}|$")
        cax_phas.set_title("$\\angle S_{21}$ [rad]")

        return fig, axes, (cax_amps, cax_phas)

    def _plot(self, axes, caxes):
        ax_amps, ax_phas = axes
        cax_amps, cax_phas = caxes

        data = self.get_data()
        if data is None:
            return

        s_data = self._remove_delay(data["frequencies"], data["s_data"])

        XX, YY = generate_mesh(data[self._parameter_name+"s"],
                        data["frequencies"]/1e9)

        max_amp = max(abs(s_data)[abs(s_data)!=0])
        min_amp = min(abs(s_data)[abs(s_data)!=0])
        amps_map = ax_amps.pcolormesh(XX,YY, abs(s_data).T, cmap="RdBu_r",
                                    vmax=max_amp, vmin=min_amp)
        plt.colorbar(amps_map, cax = cax_amps)

        max_phas = max(angle(s_data)[angle(s_data)!=0])
        min_phas = min(angle(s_data)[angle(s_data)!=0])
        phas_map = ax_phas.pcolormesh(XX, YY, angle(s_data.T), cmap="RdBu_r")
        plt.colorbar(phas_map, cax = cax_phas)

        ax_amps.axis("tight")
        ax_phas.axis("tight")

    def save(self):
        super().save()
        self.visualize()
        plt.savefig(self.get_save_path()+self._name+".png", bbox_inches='tight')
        plt.close("all")

    def remove_delay(self):
        copy = self.copy()
        s_data, frequencies = copy.get_data()["s_data"], copy.get_data()["frequencies"]
        copy.get_data()["s_data"] = self._remove_delay(frequencies, s_data)
        return copy

    def _remove_delay(self, frequencies, s_data):
        phases = unwrap(angle(s_data[0]))
        k, b = polyfit(frequencies, phases, 1)
        phases = phases - k*frequencies - b
        return abs(s_data)*exp(1j*phases)

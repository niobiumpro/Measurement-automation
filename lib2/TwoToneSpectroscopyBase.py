

'''
Paramatric single-tone spectroscopy is perfomed with a Vector Network Analyzer
(VNA) for each parameter value which is set by a specific function that must be
passed to the SingleToneSpectroscopy class when it is created.
'''


from numpy import *
from lib2.SingleToneSpectroscopy import *
from datetime import datetime as dt


class TwoToneSpectroscopyBase(SingleToneSpectroscopy):

    def __init__(self, name, sample_name, vna, mw_src, parameter_name,
            parameter_setter, line_attenuation_db = 60):

        self._name = name
        self._sample_name = sample_name
        self._vna = vna
        self._mw_src = mw_src
        self._parameter_name = parameter_name
        self._parameter_setter = parameter_setter
        self._measurement_result = TwoToneSpectroscopyResult(name,
                    sample_name, parameter_name)

        self._interrupted = False

    def setup_control_parameters(self, vna_parameters, mw_src_parameters,
                mw_src_frequencies, parameter_values):
        super().setup_control_parameters(vna_parameters, parameter_values)
        self._mw_src_parameters = mw_src_parameters
        self._mw_src_frequencies = mw_src_frequencies

        self._measurement_result.get_context()\
                .get_equipment()["mw_src"] = self._mw_src_parameters

    def _detect_resonator(self):
        self._vna.set_freq_limits(*self._vna_parameters["freq_limits"])
        self._vna.set_power(self._vna_parameters["power"])
        self._vna.set_bandwidth(self._vna_parameters["bandwidth"]*10)
        self._vna.set_averages(self._vna_parameters["averages"])
        return super()._detect_resonator()

    def _record_data(self):
        vna = self._vna
        mw_src = self._mw_src

        vna.set_parameters(self._vna_parameters)
        mw_src.set_parameters(self._mw_src_parameters)

        start_datetime = self._measurement_result.get_start_datetime()

        raw_s_data = zeros((len(self._parameter_values), len(self._mw_src_frequencies)), dtype=complex_)

        done_sweeps = 0
        total_sweeps = len(self._parameter_values)*len(self._mw_src_frequencies)
        vna.sweep_hold()

        for idx, value in enumerate(self._parameter_values):

            self._parameter_setter(value)

            for idx2, frequency in enumerate(self._mw_src_frequencies):

                self._mw_src.set_frequency(frequency)

                if self._interrupted:
                    self._interrupted = False
                    self._vna.set_parameters(self._pre_measurement_vna_parameters)
                    return

                vna.avg_clear(); vna.prepare_for_stb(); vna.sweep_single(); vna.wait_for_stb()

                raw_s_data[idx, idx2] = mean(vna.get_sdata())

                raw_data = {"frequency":self._mw_src_frequencies,
                            self._parameter_name:self._parameter_values,
                            "s_data":raw_s_data}
                self._measurement_result.set_data(raw_data)
                done_sweeps += 1
                avg_time = (dt.now() - start_datetime).total_seconds()/done_sweeps
                print("\rTime left: "+format_time_delta(avg_time*(total_sweeps-done_sweeps))+\
                        ", parameter value: "+\
                        "%.3e"%value+", average cycle time: "+\
                        str(round(avg_time, 2))+" s          ",
                        end="", flush=True)

        self._vna.set_parameters(self._pre_measurement_vna_parameters)
        self._measurement_result.set_is_finished(True)

class TwoToneSpectroscopyResult(SingleToneSpectroscopyResult):

    def _prepare_data_for_plot(self, data):
        s_data = data["s_data"]
        XX, YY = generate_mesh(data[self._parameter_name], data["frequency"]/1e9)
        return XX, YY, s_data

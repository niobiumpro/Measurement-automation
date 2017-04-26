

'''
Paramatric single-tone spectroscopy is perfomed with a Vector Network Analyzer
(VNA) for each parameter value which is set by a specific function that must be
passed to the SingleToneSpectroscopy class when it is created.
'''


from numpy import *
from lib2.TwoToneSpectroscopyBase import *

class FluxTwoToneSpectroscopy(TwoToneSpectroscopyBase):

    def __init__(self, name, sample_name, line_attenuation_db = 60,
        vna_name = "vna2", mw_src_name = "mxg", current_src_name = "yok3"):

        super().__init__(name, sample_name, "Current [A]",
                line_attenuation_db, vna_name, mw_src_name, current_src_name)
        self._parameter_setter = self._current_src.set_current

    def setup_control_parameters(self, vna_parameters, mw_src_parameters,
                mw_src_frequencies, current_values, sweet_spot_current = None):
        super().setup_control_parameters(vna_parameters, mw_src_parameters,
                    mw_src_frequencies, current_values)

        self._mw_src.set_output_state("OFF")

        if sweet_spot_current is None:
            sweet_spot_current = mean((current_values[-1], current_values[0]))

        self._parameter_setter(sweet_spot_current)

        print("Detecting a resonator within provided frequency range of the VNA %s\
                    at qubit's sweet spot (%.2f mA)"%(str(vna_parameters["freq_limits"]),
                        sweet_spot_current*1e3), flush=True)
        res_freq, res_amp, res_phase = self._detect_resonator()
        print("Detected frequency is %.5f GHz, at %.2f mU and %.2f degrees"%(res_freq/1e9, res_amp*1e3, res_phase/pi*180))
        self._vna_parameters["freq_limits"] = (res_freq, res_freq)
        self._measurement_result.get_context() \
            .get_equipment()["vna"] = self._vna_parameters

        self._mw_src.set_output_state("ON")


class PowerTwoToneSpectroscopy(TwoToneSpectroscopyBase):

    def __init__(self, name, sample_name, line_attenuation_db = 60,
                vna_name = "vna2", mw_src_name = "mxg", current_src_name = "yok3"):
        super().__init__(name, sample_name, "Power [dBm]",
                line_attenuation_db, vna_name, mw_src_name, current_src_name)
        self._parameter_setter = self._mw_src.set_power

    def setup_control_parameters(self, vna_parameters, mw_src_parameters,
                mw_src_frequencies, mw_src_power_values, current):
        super().setup_control_parameters(vna_parameters, mw_src_parameters,
                    mw_src_frequencies, mw_src_power_values)

        self._mw_src.set_output_state("OFF")
        self._current_src.set_current(current)

        print("Detecting a resonator within provided frequency range of the VNA %s\
                    at current of %.2f mA"%(str(vna_parameters["freq_limits"]),
                        current*1e3), flush=True)
        res_freq, res_amp, res_phase = self._detect_resonator()
        print("Detected frequency is %.5f GHz, at %.2f mU and %.2f degrees"%(res_freq/1e9, res_amp*1e3, res_phase/pi*180))
        self._vna_parameters["freq_limits"] = (res_freq, res_freq)
        self._measurement_result.get_context() \
            .get_equipment()["vna"] = self._vna_parameters
        self._mw_src.set_output_state("ON")

class AcStarkTwoToneSpectroscopy(TwoToneSpectroscopyBase):

    def __init__(self, name, sample_name, line_attenuation_db = 60,
            vna_name = "vna2", mw_src_name = "mxg", current_src_name = "yok3"):

        super().__init__(name, sample_name, "Readout power [dBm]",
                line_attenuation_db, vna_name, mw_src_name, current_src_name)
        self._parameter_setter = self._power_and_averages_setter

    def setup_control_parameters(self, vna_parameters, mw_src_parameters,
                        mw_src_frequencies, vna_power_values, current):

        super().setup_control_parameters(vna_parameters, mw_src_parameters,
                    mw_src_frequencies, vna_power_values)

        self._mw_src.set_output_state("OFF")
        self._current_src.set_current(current)

        print("Detecting a resonator within provided frequency range of the VNA %s\
                    at current of %.2f mA"%(str(vna_parameters["freq_limits"]),
                        current*1e3), flush=True)
        res_freq, res_amp, res_phase = self._detect_resonator()
        print("Detected frequency is %.5f GHz, at %.2f mU and %.2f degrees"%(res_freq/1e9, res_amp*1e3, res_phase/pi*180))
        self._vna_parameters["freq_limits"] = (res_freq, res_freq)
        self._measurement_result.get_context() \
            .get_equipment()["vna"] = self._vna_parameters

        self._mw_src.set_output_state("ON")

    def _power_and_averages_setter(self, power):
        powers = self._parameter_values
        start_averages = self._vna_parameters["averages"]
        avg_factor = exp((power - powers[0])/powers[0]*log(start_averages))
        self._vna.set_averages(round(start_averages*avg_factor))
        self._vna.set_power(power)

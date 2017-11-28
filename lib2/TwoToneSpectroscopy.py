

'''
Paramatric single-tone spectroscopy is perfomed with a Vector Network Analyzer
(VNA) for each parameter value which is set by a specific function that must be
passed to the SingleToneSpectroscopy class when it is created.
'''


from numpy import *
from lib2.TwoToneSpectroscopyBase import *
from time import sleep

class FluxTwoToneSpectroscopy(TwoToneSpectroscopyBase):

    def __init__(self, name, sample_name, line_attenuation_db = 60,
        vna_name = "vna2", mw_src_name = "mxg", current_src_name = "yok3"):
        super().__init__(name, sample_name,
                line_attenuation_db, vna_name, mw_src_name, current_src_name)

    def set_fixed_parameters(self, vna_parameters, mw_src_parameters,
        sweet_spot_current, adaptive = False):
        self._resonator_area = vna_parameters["freq_limits"]
        self._adaptive = adaptive
        super().set_fixed_parameters(vna_parameters, mw_src_parameters,
                    sweet_spot_current, not adaptive)

    def set_swept_parameters(self, mw_src_frequencies, current_values):
        current_setter =\
            self._current_setter if self._adaptive else self._current_src.set_current
        swept_pars = {"Current [A]":(current_setter, current_values),
                "Frequency [Hz]":(self._mw_src.set_frequency, mw_src_frequencies)}
        super().set_swept_parameters(**swept_pars)

    def _current_setter(self, current):

        self._current_src.set_current(current)

        vna_parameters = self._fixed_pars["vna"]
        vna_parameters["freq_limits"] = self._resonator_area

        self._mw_src.set_output_state("OFF")
        print("\rDetecting a resonator within provided frequency range of the VNA %s\
                    "%(str(vna_parameters["freq_limits"])), flush=True, end="")
        res_freq, res_amp, res_phase = self._detect_resonator(vna_parameters, plot=False,
                                                            bandwidth_factor=2)
        print("\rDetected frequency is %.5f GHz, at %.2f mU and %.2f \
                    degrees"%(res_freq/1e9, res_amp*1e3, res_phase/pi*180), end="")
        self._mw_src.set_output_state("ON")
        vna_parameters["freq_limits"] = (res_freq, res_freq)
        self._vna.set_parameters(vna_parameters)

class PowerTwoToneSpectroscopy(TwoToneSpectroscopyBase):

    def __init__(self, name, sample_name, line_attenuation_db = 60,
                vna_name = "vna2", mw_src_name = "mxg", current_src_name = "yok3"):
        super().__init__(name, sample_name, line_attenuation_db, vna_name,
                                            mw_src_name, current_src_name)

    def set_swept_parameters(self, mw_src_frequencies, power_values):
        swept_pars = {"Power [dBm]":(self._mw_src.set_power, power_values),
                "Frequency [Hz]":(self._mw_src.set_frequency, mw_src_frequencies)}
        super().set_swept_parameters(**swept_pars)

class AcStarkTwoToneSpectroscopy(TwoToneSpectroscopyBase):

    def __init__(self, name, sample_name, line_attenuation_db = 60,
            vna_name = "vna2", mw_src_name = "mxg", current_src_name = "yok3"):

        super().__init__(name, sample_name, line_attenuation_db, vna_name,
                                        mw_src_name, current_src_name)

    def set_fixed_parameters(self, vna_parameters, mw_src_parameters, current):
        self._resonator_area = vna_parameters["freq_limits"]
        super().set_fixed_parameters(vna_parameters, mw_src_parameters,
                                                                current, False)

    def set_swept_parameters(self, mw_src_frequencies, power_values):
        swept_pars =\
            {"Readout power [dBm]":(self._power_and_averages_setter, power_values),
                "Frequency [Hz]":(self._mw_src.set_frequency, mw_src_frequencies)}
        super().set_swept_parameters(**swept_pars)

    def _power_and_averages_setter(self, power):
        powers = self._swept_pars["Readout power [dBm]"][1]
        vna_parameters = self._fixed_pars["vna"]
        start_averages = vna_parameters["averages"]
        avg_factor = exp((power - powers[0])/powers[0]*log(start_averages))
        vna_parameters["averages"] = round(start_averages*avg_factor)
        vna_parameters["power"] = power
        vna_parameters["freq_limits"] = self._resonator_area

        self._mw_src.set_output_state("OFF")
        print("\rDetecting a resonator within provided frequency range of the VNA %s\
                    "%(str(vna_parameters["freq_limits"])), flush=True, end="")
        res_freq, res_amp, res_phase = self._detect_resonator(vna_parameters, plot=False,
                                                            bandwidth_factor=2)
        print("\rDetected frequency is %.5f GHz, at %.2f mU and %.2f \
                    degrees"%(res_freq/1e9, res_amp*1e3, res_phase/pi*180), end="")

        self._mw_src.set_output_state("ON")
        vna_parameters["freq_limits"] = (res_freq, res_freq)

        self._vna.set_parameters(vna_parameters)

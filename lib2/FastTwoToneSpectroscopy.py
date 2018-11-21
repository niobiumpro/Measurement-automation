from numpy import *
from lib2.FastTwoToneSpectroscopyBase import FastTwoToneSpectroscopyBase
from time import sleep


class FastFluxTwoToneSpectroscopy(FastTwoToneSpectroscopyBase):

    def __init__(self, name, sample_name, line_attenuation_db=60, **devs_aliases_map):
        super().__init__(name, sample_name,
                         line_attenuation_db, devs_aliases_map)

    def set_fixed_parameters(self, vna_parameters, mw_src_parameters,
                             sweet_spot_current=None, sweet_spot_voltage=None, adaptive=False,
                             bandwidth_factor=10):
        self._resonator_area = vna_parameters["freq_limits"]
        self._adaptive = adaptive

        # trigger layout is detected via mw_src_parameters in TTSBase class

        super().set_fixed_parameters(vna_parameters, mw_src_parameters,
                                     current=sweet_spot_current, voltage=sweet_spot_voltage,
                                     detect_resonator=not adaptive,
                                     bandwidth_factor=bandwidth_factor)

    def set_swept_parameters(self, mw_src_frequencies, current_values=None,
                             voltage_values=None):
        base_parameter_values = current_values if voltage_values is None else voltage_values
        base_parameter_setter = self._adaptive_setter if self._adaptive else self._base_setter

        swept_pars = {self._base_parameter_name: (base_parameter_setter, base_parameter_values),
                      "Frequency [Hz]": (self._mw_src.set_frequency, mw_src_frequencies)}
        super().set_swept_parameters(**swept_pars)


class FastPowerTwoToneSpectroscopy(FastTwoToneSpectroscopyBase):

    def __init__(self, name, sample_name, line_attenuation_db=60, **devs_aliases_map):
        super().__init__(name, sample_name, line_attenuation_db, devs_aliases_map)

    def set_fixed_parameters(self, vna_parameters, mw_src_parameters,
                             sweet_spot_current=None, sweet_spot_voltage=None, adaptive=False,
                             bandwidth_factor=10):
        self._resonator_area = vna_parameters["freq_limits"]
        self._adaptive = adaptive
        # trigger layout is detected via mw_src_parameters in TTSBase class

        super().set_fixed_parameters(vna_parameters, mw_src_parameters,
                                     current=sweet_spot_current, voltage=sweet_spot_voltage,
                                     detect_resonator=not adaptive, bandwidth_factor=10)

    def set_swept_parameters(self, mw_src_frequencies, power_values):
        self._base_parameter_setter = self._mw_src.set_power
        base_parameter_setter = self._adaptive_setter if self._adaptive else self._base_setter

        swept_pars = {"Power [dBm]": (base_parameter_setter, power_values),
                      "Frequency [Hz]": (self._mw_src.set_frequency, mw_src_frequencies)}

        super().set_swept_parameters(**swept_pars)


class FastAcStarkTwoToneSpectroscopy(FastTwoToneSpectroscopyBase):

    def __init__(self, name, sample_name, line_attenuation_db=60, **devs_aliases_map):

        super().__init__(name, sample_name, line_attenuation_db, devs_aliases_map)

    def set_fixed_parameters(self, vna_parameters, mw_src_parameters, current=None,
                             voltage=None, bandwidth_factor=10):
        self._resonator_area = vna_parameters["freq_limits"]
        super().set_fixed_parameters(vna_parameters, mw_src_parameters,
                                     voltage=voltage, current=current, detect_resonator=False,
                                     bandwidth_factor=bandwidth_factor)

    def set_swept_parameters(self, mw_src_frequencies, current_values=None,
                             voltage_values=None):

        base_parameter_values = current_values if voltage_values is None else voltage_values
        base_parameter_setter = self._adaptive_setter if self._adaptive else self._base_setter

        swept_pars = {self._base_parameter_name: (base_parameter_setter, base_parameter_values),
                      "Frequency [Hz]": (self._mw_src.set_frequency, mw_src_frequencies)}
        super().set_swept_parameters(**swept_pars)

    def set_swept_parameters(self, mw_src_frequencies, power_values):

        swept_pars = \
            {"Readout power [dBm]": (self._power_and_averages_setter, power_values),
             "Frequency [Hz]": (self._mw_src.set_frequency, mw_src_frequencies)}
        super().set_swept_parameters(**swept_pars)

    def _power_and_averages_setter(self, power):
        powers = self._swept_pars["Readout power [dBm]"][1]
        vna_parameters = self._fixed_pars["vna"]
        start_averages = vna_parameters["averages"]
        avg_factor = exp((power - powers[0]) / powers[0] * log(start_averages))
        vna_parameters["averages"] = round(start_averages * avg_factor)
        vna_parameters["power"] = power
        vna_parameters["freq_limits"] = self._resonator_area

        self._mw_src.set_output_state("OFF")
        if vna_parameters["freq_limits"][0] != vna_parameters["freq_limits"][1]:
            # print("\rDetecting a resonator within provided frequency range of the VNA %s\
            #        "%(str(vna_parameters["freq_limits"])), flush=True, end="")

            res_result = self._detect_resonator(vna_parameters, plot=False)

            if (res_result is None):
                print("Failed to fit resonator, trying to use last successful fit, power = ", power,
                      " A")
                if (self._last_resonator_result is None):
                    print("no successful fit is present, terminating")
                    return None
                else:
                    res_result = self._last_resonator_result
            else:
                self._last_resonator_result = res_result

            res_freq, res_amp, res_phase = self._last_resonator_result
            # print("\rDetected frequency is %.5f GHz, at %.2f mU and %.2f \
            #        degrees"%(res_freq/1e9, res_amp*1e3, res_phase/pi*180), end="")
        else:
            res_freq = vna_parameters["freq_limits"][0]

        self._mw_src.set_output_state("ON")
        vna_parameters["freq_limits"] = (res_freq, res_freq)

        self._vna.set_parameters(vna_parameters)
        self._mw_src.send_sweep_trigger()  # telling mw_src to start

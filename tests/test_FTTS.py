from lib2.FastTwoToneSpectroscopy import *
from unittest.mock import MagicMock, Mock
from time import sleep
from numpy import linspace


class DataGen:

    def __init__(self):
        self._counter = 0
        self._nop = 1
        self._freq = 0.1

    def fun(self, x):
        return [cos(self._freq * x) + 1j * cos(self._freq * x)] * self._nop

    def get_sdata(self):
        retval = self.fun(self._counter)
        self._counter += 1
        sleep(0.05)
        return retval

    def get_frequencies(self):
        return linspace(self._freq_limits[0], self._freq_limits[1], self._nop)

    def set_parameters(self, params):
        self._nop = params["nop"]
        self._freq_limits = params["freq_limits"]

    def set_freq_limits(self, *limits):
        self._freq_limits = limits

    def set_nop(self, nop):
        self._nop = nop

    def detect(self):
        return 5.9e9, 0, 0

dg = DataGen()
vna = MagicMock()
cur_src = MagicMock()
vol_src = MagicMock()
q_lo = MagicMock()
q_awg = MagicMock()
ro_awg = MagicMock()
q_z_awg = Mock()
mw_src = MagicMock()
RD = Mock()
RD.detect = dg.detect
vna.get_sdata = dg.get_sdata
vna.get_frequencies = dg.get_frequencies
vna.set_freq_limits = dg.set_freq_limits
vna.set_nop = dg.set_nop


def test_set_fixed_pars_in_FFTTS():

    equipment = {"vna": [vna], "mw_src": [mw_src], 'current_src': [cur_src]}
    TTS = FastFluxTwoToneSpectroscopy("test_delete", "test",
                                      vna=[vna], mw_src=[mw_src], current_src=[cur_src])
    res_limits = [4e9, 6e9]
    vna_parameters = {"bandwidth": 250, "freq_limits": res_limits, "nop": 10, "power": -15, "averages": 1}
    TTS._resonator_detector = RD
    mw_src_frequencies = linspace(8.5e9, 9.2e9, 51)
    mw_src_parameters = {"power": 0, 'freq_limits': mw_src_frequencies}

    center = 0
    sweet_spot = 0
    period = 1
    currents = linspace(sweet_spot - period / 8, sweet_spot + period / 8, 51)
    dev_params = {'vna': [vna_parameters],
                  'mw_src': [mw_src_parameters]}
    TTS.set_fixed_parameters(adaptive=True, **dev_params)
    TTS.set_swept_parameters(current_values=currents)
    TTS._measurement_result._unwrap_phase = True

    for key in dev_params.keys():
        for dev, param in list(zip(equipment[key], dev_params[key])):
            dev.set_parameters.assert_called_with(param)



def test_set_fixed_pars_in_FPTTS():

    equipment = {"vna": [vna], "mw_src": [mw_src], 'current_src': [cur_src]}
    PTS = FastPowerTwoToneSpectroscopy("test_delete", "test",
                                      vna=[vna], mw_src=[mw_src], current_src=[cur_src])

    current = 0
    mw_freq_limits = (5.5e9, 5.9e9)
    mw_freq_nop = 201
    res_limits = [4e9, 6e9]
    mw_src_frequencies = linspace(mw_freq_limits[0], mw_freq_limits[-1], mw_freq_nop)
    PTS._resonator_detector = RD
    vna_parameters = {"bandwidth": 50, "freq_limits": res_limits, "nop": mw_freq_nop,
                      "res_find_power": -0, "res_find_nop": 801,
                      "power": 0, "sweep_type": "LIN", "averages": 1,
                      "aux_num": 1, "trig_dur": 2.5e-3}
    mw_src_parameters = {"power": 7, "freq_limits": mw_freq_limits, "nop": mw_freq_nop,
                         "ext_trig_channel": "TRIG1"}
    dev_params = {'vna': [vna_parameters],
                  'mw_src': [mw_src_parameters]}
    mw_src_powers = linspace(-20, -5, 21)
    PTS.set_fixed_parameters(current, **dev_params, adaptive=True)
    PTS.set_swept_parameters(mw_src_powers)
    PTS._measurement_result.set_phase_units("deg")
    PTS._measurement_result.set_unwrap_phase(False)


    for key in dev_params.keys():
        for dev, param in list(zip(equipment[key], dev_params[key])):
            dev.set_parameters.assert_called_with(param)

    # for power in mw_src_powers:
    #     PTS._mw_src[0].set_power.assert_called_with(power)


def test_set_fixed_pars_in_FASTT():


    equipment = {"vna": [vna], "mw_src": [mw_src], 'voltage_src': [vol_src]}
    FASTS = FastAcStarkTwoToneSpectroscopy("test_delete", 'test', vna=[vna], mw_src=[mw_src], voltage_src=[vol_src])
    FASTS._mw_src[0].write(":SWEep:ATTen:PROTection ON")
    mw_src_frequencies = linspace(5.5e9, 5.7e9, 101)
    res_limits = [4e9, 6e9]
    voltage = 0.32

    mw_src_parameters = {"power": 5, "freq_limits": (mw_src_frequencies[0], mw_src_frequencies[-1]),
                         "nop": len(mw_src_frequencies), "ext_trig_channel": "TRIG1"}

    vna_parameters = {"bandwidth": 100, "freq_limits": res_limits, "nop": len(mw_src_frequencies),
                      "sweep_type": "LIN",
                      "power": -10, "averages": 10, "aux_num": 1, "trig_dur": 3e-3, "res_find_power": -20,
                      "res_find_nop": 401}
    voltage_src_parameters = {'voltage': voltage}

    vna_powers = linspace(-10, 6, 51)
    dev_params = {'vna': [vna_parameters],
                  'mw_src': [mw_src_parameters]}
    FASTS.set_fixed_parameters(**dev_params,voltage=voltage, bandwidth_factor=10)
    FASTS.set_swept_parameters(vna_powers)


    for key in dev_params.keys():
        for dev, param in list(zip(equipment[key], dev_params[key])):
            dev.set_parameters.assert_called_with(param)





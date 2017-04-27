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
        make measurements


    '''
    def __init__(self, name, sample_name, line_attenuation_db,
                    exa_name, mw_src1_name, mw_src2_name, vna_name, current_src_name):
        '''
        name: name of current measurement
        sample_name: name of measured sample_name

        '''

        devs_names = [vna_name, mw_src1_name, current_src_name, exa_name, mw_src2_name]
        super().__init__(name, sample_name, devs_names)

        self._vna = self._actual_devices[vna_name]
        self._src_plus = self._actual_devices[mw_src1_name]
        self._src_minus = self._actual_devices[mw_src2_name]
        self._exa = self._actual_devices[exa_name]
        self._bias = self._actual_devices[current_src_name]

        self._measurement_result = FourWaveMixingResult(name,
                    sample_name, parameter_name)
        self._interrupted = False

    def setup_control_parameters(self, exa_parameters, mw_src_parameters, mw_src_frequencies, parameter_values):

        self._exa_parameters = exa_parameters
        self._parameter_values = parameter_values
        self._pre_measurement_exa_parameters = self._exa.get_parameters()

        self._mw_src_parameters = mw_src_parameters
        self._mw_src_frequencies = mw_src_frequencies

        self._measurement_result.get_context() \
            .get_equipment()["vna"] = self._vna_parameters
        self._measurement_result.get_context()\
                .get_equipment()["mw_src"] = self._mw_src_parameters

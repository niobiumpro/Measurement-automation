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
        sample_name: name of measured sample_name
        swept_par: dictionary {'name1': setter1, 'name2' setter2, ...} 
        swept_par_setter: list of fuctions setting the parameters to be changed during the measurement

        vna and current source is optional 

        '''
        self._devs_aliases = list(devs_aliases.keys())
        super().__init__(name, sample_name, list(devs_aliases.values()))

        for alias, name in devs_aliases.items():
            self.__setattr__("_"+alias,self._actual_devices[name]) 

        self._measurement_result = FourWaveMixingResult(name,
                    sample_name)
        self._interrupted = False

    def _recording_iteration(self):
        self._exa.make_trace_get_data()



          

    



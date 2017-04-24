'''
Base interface for all measurements.

Should define the raw_data type (???)
я бы сказал что он обязательно должен требовать (как-то) чтобы наследники задавали вид сырых данных, я подумаю как это сделать пока на ум не приходит

Should perform following actions:

 --  automatically call all nesessary devices for a certain measurement. (with the names of devices passed through the constructor)
    of course
 --  implementation of parallel plotting (the part with Treads, the actual plot is adjusted in class with actual measurement)
    yes, but not with threads yet with Processes, still thinking about how exactly it should be hidden from the end-user
 --  some universal data operations on-fly (background substraction, normalization, dispersion calculation, etc.)
    the implementation of these operations should go into each MeasurementResult class, so only the calls of the
    corresponding methods should be left here (may be to allow user to choose exact operation to perform during the dynamic plotting)
 --  universal functions for presetting devices in a number of frequently used regimes (creating windows/channels/sweeps/markers)
    я думаю это лучше поместить в драверы
 --  frequently used functions of standart plotting like single trace (but made fancy, like final figures for presentation/)
    это тоже в классы данных по идее лучше пойдет
 --  a logging of launched measurements from ALL certain classes (chronologically, in a single file, like laboratory notebook, with comments)
    может быть, может быть полезно, если 100500 человек чето мерют одними и теми же приборами и что-то сломалось/нагнулось
some other bullshit?
does this class necessary at all?

some other bullshit:
 -- должен нести описания методов, которые должны быть обязательено реализованы в дочерних классах:
        set_devices (устанавливает, какие приборы используются, получает на вход обекты)
        set_control_parameters (установить неизменные параметры приборов)
        set_varied_parameters (установить изменяемые параметры и их значения; надо написать для STS)
        launch (возможно, целиком должен быть реализован здесь, так как он универсальный)
        _record_data (будет содержать логику измерения, пользуясь приборами и параметрами, определенными выше)\
'''
from numpy import *
import copy
import pyvisa
#import sys.stdout.flush
#from sys.stdout import flush
import os, fnmatch
import pickle
from drivers import *
# from drivers.Agilent_PNA_L import *
# from drivers.Agilent_PNA_L import *
# from drivers.Yokogawa_GS200 import *
# from drivers.KeysightAWG import *
# from drivers.E8257D import MXG,EXG
# from drivers.Agilent_DSO import *
from matplotlib import pyplot as plt

class Measurement():

    '''
    Any inheritance?
    The class contains methods to help with the implementation of measurement classes.

    '''
    _vna1 = None
    _vna2 = None
    _exa = None
    _exg = None
    _mxg = None
    _awg1 = None
    _awg2 = None
    _awg3 = None
    _dso = None
    _yok1 = None
    _yok2 = None
    _yok3 = None
    _logs = []

    def __init__(self, devs_names=None, type=None):
        '''
        Parameters:
        --------------------
        devs_names: a list with devices' standard names.
        type: a string with one of defined types of measurements (implemented ones). This
              could
        --------------------

        Constructor creates variables for devices passed to it and initialises all devices.

        Standard names of devices within this driver are:

            'vna1',vna2','exa','exg','mxg','awg1','awg2','awg3','dso','yok1','yok2','yok3'

        with _ added in front for a variable of a class

        if key is not recognised returns a mistake

        '''

        self._devs_dict = \
                        {'vna1' : [ ["PNA-L","PNA-L1"], [Agilent_PNA_L,"Agilent_PNA_L"] ],\
                         'vna2': [ ["PNA-L-2","PNA-L2"], [Agilent_PNA_L,"Agilent_PNA_L"] ],\
                         'exa' : [ ["EXA"], [Agilent_EXA,"Agilent_EXA_N9010A"] ],\
                         'exg' : [ ["EXG"], [E8257D,"EXG"] ],\
                         'mxg' : [ ["MXG"], [E8257D,"MXG"] ],\
                         'awg1': [ ["AWG","AWG1"], [KeysightAWG,"KeysightAWG"] ],\
                         'awg2': [ ["AWG_Vadik","AWG2"], [KeysightAWG,"KeysightAWG"] ],\
                         'awg3': [ ["AWG3"], [KeysightAWG,"KeysightAWG"] ],\
                         'dso' : [ ["DSO"], [Keysight_DSOX2014,"Keysight_DSOX2014"] ],\
                         'yok1': [ ["GS210_1"], [Yokogawa_GS200,"Yokogawa_GS210"] ], \
                         'yok2': [ ["GS210_2"], [Yokogawa_GS200,"Yokogawa_GS210"] ], \
                         'yok3': [ ["GS210_3"], [Yokogawa_GS200,"Yokogawa_GS210"] ]     }

        self._devs_names = devs_names
        self._list = ""
        rm = pyvisa.ResourceManager()
        temp_list = list(rm.list_resources_info().values())

        self._devs_info = \
                        [(list(temp_list)[i])[3:5] for i in range(len(temp_list))]
                        # returns list of tuples: (IP Address string, alias) for all devices present in VISA

        for name in self._devs_names:
            for visa_tuple in self._devs_info:
                if (name in self._devs_dict.keys()) and (visa_tuple[1] in self._devs_dict.get(name)[0]):
                    print(name,visa_tuple[1], flush=True)
                    setattr(Measurement,"_"+name,getattr(self._devs_dict.get(name)[1][0],self._devs_dict.get(name)[1][1])(visa_tuple[1]))
                    print("The device {:} is detected as {:}".format(name, visa_tuple[1]), flush=True)
                    #getattr(self,"_"+name)._visainstrument.query("*IDN?")
                    break

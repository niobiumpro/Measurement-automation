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
some other bullshit?is this class necessary at all?

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
from datetime import datetime as dt
from threading import Thread
from resonator_tools import circuit
from lib2.ResonatorDetector import *
from itertools import product
from functools import reduce
from operator import mul
import traceback

from lib2.LoggingServer import LoggingServer

from collections import OrderedDict

class Measurement():
    '''
    @brief: Purely virtual class that serves as a base to all measurements.
            Handles devices initialization and OS task management.
            Child classes implementation is aimed at measurement process directrly.

            MeasurementResult class is used alongside with Measurement class
            and responsible for data save/load and visualization operations
    @desc:
            purely virtual methods
                self._recording_iteration() -> iterable (data received during iteration)

            methods to be overwritten with certain rules:


            public methods:
                self.set_fixed_parameters( **kwargs )
                    loads fixed parameters into devices
                self.set_swept_parameters( **kwargs )
                    prepares parameters iterator that will vary with the iteration number
                self.launch()
                    starts measurement process

            methods that could be overwritten:
                self._prepare_measurement_result_data

            Usage:
            1. create a class instance using needed devices names
            2. set fixed parameters
            3. set sweep parameters that vary with iteration number
            4. call self.launch() to start measurement

            see self.launch() for detailed operation description
    '''

    _logger = LoggingServer.getInstance()
    _log = []

    '''
    @desc: _actual_devices
            static dict attribute of the Measurement class
            Contains pairs key:val
                key - device's internal alias name (see Measurement._actual_devices for desc)
                val - relevant driver class instance that is shared by all Measuremnt class
                      child classes. 
    '''

    _actual_devices = {}
    '''
    @desc: _devs_dict
            static const dict attribute of the Measurement class
            Contains internal API aliases for devices that are connected
            with this particular PC. This dictionary is filled manually
            due to its dependency on the particular devices setup of your 
            measurement system.
            
            structure:
                key - internal alias name that is used to initialize the device
                val - [ devs_addresses_list, [DriverClass,"DriverClass] ]
                    devs_addresses_list - list that contains NI-VISA aliases for
                        device's physical addresses. This address is used by PyVisa
                        in order establish connection in case if this devices is present
                        in a network.
                    DriverClass - class type that will be used to create 
                        an instance of the device required. The only argument
                        of the driver class is a string, that contains a member of the
                        devs_addresses_list
                    "DriverClass" - DriverClass name as a string
                
    '''
    _devs_dict = \
        {'vna1' : [ ["PNA-L","PNA-L1"], [Agilent_PNA_L,"Agilent_PNA_L"] ],\
         'vna2': [ ["PNA-L-2","PNA-L2"], [Agilent_PNA_L,"Agilent_PNA_L"] ],\
		 'vna3': [ ["pna"], [Agilent_PNA_L,"Agilent_PNA_L"] ],\
         'vna4': [ ["ZNB"], [znb, "Znb"] ],\
         'exa' : [ ["EXA"], [Agilent_EXA,"Agilent_EXA_N9010A"] ],\
         'exg' : [ ["EXG"], [E8257D,"EXG"] ],\
         'psg2' :[ ['PSG'], [E8257D,"EXG"] ],\
         'mxg' : [ ["MXG"], [E8257D,"MXG"] ],\
		 'psg1': [ ["psg1"], [E8257D,"EXG"] ],\
         'awg1': [ ["AWG","AWG1"], [KeysightAWG,"KeysightAWG"] ],\
         'awg2': [ ["AWG_Vadik","AWG2"], [KeysightAWG,"KeysightAWG"] ],\
         'awg3': [ ["AWG3"], [KeysightAWG,"KeysightAWG"] ],\
         'awg4':  [ ["TEK1"], [Tektronix_AWG5014, "Tektronix_AWG5014"] ],\
         'dso' : [ ["DSO"], [Keysight_DSOX2014,"Keysight_DSOX2014"] ],\
         'yok1': [ ["GS210_1"], [Yokogawa_GS200,"Yokogawa_GS210"] ], \
         'yok2': [ ["GS210_2"], [Yokogawa_GS200,"Yokogawa_GS210"] ], \
         'yok3': [ ["GS210_3"], [Yokogawa_GS200,"Yokogawa_GS210"] ],    \
         'yok4': [ ["gs210"], [Yokogawa_GS200,"Yokogawa_GS210"] ], \
         'yok5': [ ["GS_210_3"], [Yokogawa_GS200,"Yokogawa_GS210"] ], \
         'yok6': [ ["YOK1"], [Yokogawa_GS200,"Yokogawa_GS210"] ], \
         'k6220':[["k6220"], [k6220,"K6220"] ], \
		 }


    def __init__(self, name, sample_name, devs_aliases_map, plot_update_interval=5):
        '''
        @desc:  Constructor creates variables for devices passed to it and initialises all devices.
                MUST BE OVERWRITTEN IN THE CHILD CLASS.

                Standard names of devices within this driver are:
                    'vna1',vna2','exa','exg','mxg','awg1','awg2','awg3','dso','yok1','yok2','yok3'
                with _ added in front for a variable of a class

                if key is not recognised doesn't returns an error yet
                prints appropriate message

                if the devices is already initialized: prints appropriate message
                and creates

        @params
            name: string
                name of the measurement
            sample_name: string
                the name of the sample that is measured
            devs_aliases_map: dictionary with key:value pairs
                 key    key is a string that will be prepended with '_'
                        and become a class attribute assigned with
                        the relevant driver class instance
                        see self.__setattr('_' + key, obj)
                 value
                        if 'str':
                            value - device's internal alias string that is used to identify the device and
                            create appropriate driver class instance that will be assigned
                            to the device's attribute. (see Measurement._devs_dict)
                        else:
                            assigns value to the self._key

        '''
        self._interrupted = False
        self._name = name
        self._sample_name = sample_name
        self._plot_update_interval = plot_update_interval


        ## data structures declaration section START ##
        '''
        NOTE_1: ACCESS AND ITERATING PROCESS OVER DATA STRUCTURES
        
        self._swept_pars_names is needed to ensure that order of the iteration over dictionaries is
        preserved over different iteration cycles throughout the program.
        instead of using 
            for par_name in self._swept_pars.keys(): # possible to obtain different order of the iterator return values
                ...
        it is preferable to use:
            for par_name in self._swept_pars_names: # iterator return values are the same all the time
        
        For example: 
        self._record_data relies on the preserved order of the iteration
        over self._swept_pars_names keys and thus, I assume, self._sept_pars_names
        was introduced.
        Also the self._swept_pars_names is passed to the self._measurement_result
        to preserve iteration order over self._measurement_result.data structure
        inside the routines of the self._measurement_result class.
        self._measurement_result contains numpy array self._measurement_result.data["data"]
        the data in this numpy array coincides with self._raw_data.
        In addition, self._measurement_result.data dict contains paris "swept_par_name":swept_par_values_list
        In case you need to iterate over parameters and obtain relevant data values, see following example:
            self._swept_pars_names = ["current","freq"]
            this means that data[i1,i2] will contain measurement result with swept parameters: 
            "current" parameter value - self._swept_parameters["current"][i1] equals to self._measurement_data.data["current"][i1]
            "freq" parameter value self._swept_parameters["freq"][i2] equals to self._measurement_data.data["freq"][i2]
            
        Setting up swept parameters is performed in the self.set_swept_parameters() for Measurement child-class instance.
        self._measurement_result.data is filled with "swept_par_name":swept_par_values_list pairs during the
        calls: self._record_data() -> self._prepare_measurement_result_data(pars_names,pars_vals)
                
        Note: 
        OrderedDict is the preferable solution in case we need to preserve iteration order
        of the dictionary. In this case we can successfuly get rid of the self._swept_pars_names
        '''
        self._swept_pars_names = []
        self._fixed_pars = {}
        self._swept_pars = {}
        self._last_swept_pars_values = {}

        # data returned by self._recording_iteration()
        # is stored in the attribute self._raw_data
        # self._raw_data - multidimensional numpy array
        # which iterating order coincide with the
        # self._swept_pars_names sweep parameters order
        # see NOTE_1 in Measurement class constructor above
        self._raw_data = None

        # self._measurement_result attribute must be filled
        # in the child-class constructor
        # after the call of super().__init__
        # with the appropriate child-class of the
        # MeasurementResult class
        self._measurement_result = None
        ## data structures declaration section END ##

        ## Device initialization section START ##
        self._devs_aliases_map = devs_aliases_map
        self._list = ""
        rm = pyvisa.ResourceManager()
        temp_list = list(rm.list_resources_info().values())
        Measurement._logger.debug("Measurement "+ name + " init")
        Measurement._logger.debug("Measurement "+ name+" devs:" + str(devs_aliases_map))
        self._devs_info = [item[4] for item in list(temp_list)]
                # returns list of tuples: (IP Address string, alias) for all
                # devices present in VISA
        self._write_to_log()
        for field_name, value in self._devs_aliases_map.items():
            if isinstance(value, str):
                name = value
                if name in Measurement._actual_devices.keys():
                    print(name + ' is already initialized')
                    device_object = Measurement._actual_devices[name]
                    self.__setattr__("_"+field_name, device_object)
                    continue

                if name in Measurement._devs_dict.keys():
                    for device_address in self._devs_info:
                        if device_address in Measurement._devs_dict[name][0]:
                            # print(name, device_address)
                            device_object = getattr(*Measurement._devs_dict[name][1])(device_address)
                            Measurement._actual_devices[name]=device_object
                            print("The device %s is detected as %s"%(name, device_address))
                            self.__setattr__("_"+field_name, device_object)
                            break
                else:
                    print("Device", name, "is unknown!")
            else:
                self.__setattr__("_"+field_name, value)

    def close_devs(devs_to_close):
        for name in devs_to_close:
            if name in Measurement._actual_devices.keys():
                Measurement._actual_devices.pop(name)._visainstrument.close()

    def _load_fixed_parameters_into_devices(self):
        '''
        @brief: Loads self.fixed_pars dictionary
                into devices
        @params: None
        @return: None
        '''
        for dev_name in self._fixed_pars.keys():
            dev = getattr(self, '_' + dev_name)
            dev.set_parameters(self._fixed_pars[dev_name])

    def set_fixed_parameters(self, **fixed_pars):
        '''
        @brief: Calls 'set_params' method for every device
                which alias name is in fixed_pars.keys()
                Stores parameters par:val pairs dictionary as a value
                in the self._measurement_result._context._equipment dict
                and in self._fixed_pars
        @params:
                fixed_pars: {'dev1': {'par1': value1, 'par2': value2,...},
                             'dev2': {'par1': value1, 'par2': ...},...}
                key - device's internal alias name
                value - dictionary of the "parameter_name":parameter_value pairs
        @return: None
        '''
        self._fixed_pars = fixed_pars
        self._measurement_result.set_devices_context_fixed_parameters(**fixed_pars)
        self._load_fixed_parameters_into_devices()

    def set_swept_parameters(self, **swept_pars):
        '''
        @brief: set swept par names into self._swept_pars and
                also storing their names into
                    self._measurement_result._parameter_names
                    self._swept_pars_names
        swept_pars - {'par1': (setter1, [value1, value2, ...]),
                     'par2': (setter2, [value1, value2, ...]), ...}

        child-class implementation must have the following structure of the arguments:
        swept_pars - {'par1': [value1, value2, ...],
                     'par2': [value1, value2, ...], ...}
        and reconstruct this dict to the structure accepted by this method
        by introducting setter1, setter2 and so on
        after the reconstruction this method must be called in every child-class
        '''
        self._swept_pars = swept_pars
        self._swept_pars_names = list(swept_pars.keys())
        self._measurement_result.set_parameter_names(self._swept_pars_names)
        self._last_swept_pars_values = \
                            {name:None for name in self._swept_pars_names}

    def _call_setters(self, values_group):
        for name, value in zip(self._swept_pars_names, values_group):
            if self._last_swept_pars_values[name] != value:
                self._last_swept_pars_values[name] = value
                self._swept_pars[name][0](value) # this is setter call, look carefully

    def launch(self):
        '''
        TODO: write human-readable description
        '''
        plt.ion()

        self._measurement_result.set_start_datetime(dt.now())
        if self._measurement_result.is_finished():
            print("Starting with a result from a previous launch")
            self._measurement_result.set_is_finished(False)
        print("Started at: ", self._measurement_result.get_start_datetime())
        t = Thread(target=self._record_data)
        t.start()
        try:
            while not self._measurement_result.is_finished():
                self._measurement_result._visualize_dynamic()
                for i in range(0,10):
                    plt.pause(self._plot_update_interval/10)
                # plt.gcf().canvas.start_event_loop(self._plot_update_interval)
        except KeyboardInterrupt:
            self._interrupted = True
        except Exception as e:
            self._interrupted = True
            traceback.print_exc()

        self._measurement_result.finalize()
        return self._measurement_result

    def _record_data(self):
        '''
        TODO: write descrioption
        '''
        par_names = self._swept_pars_names
        parameters_values = []
        parameters_idxs = []
        done_iterations = 0
        start_time = self._measurement_result.get_start_datetime()

        parameters_values = \
                [self._swept_pars[parameter_name][1] for parameter_name in par_names]
        parameters_idxs = \
                [list(range(len(self._swept_pars[parameter_name][1]))) for parameter_name in par_names]
        raw_data_shape = \
                [len(indices) for indices in parameters_idxs]
        total_iterations = reduce(mul, raw_data_shape, 1)

        for idx_group, values_group in zip(product(*parameters_idxs), product(*parameters_values)):

            self._call_setters(values_group)

            # This should be implemented in child classes:
            data = self._recording_iteration()

            if done_iterations == 0:
                try:
                    self._raw_data = zeros(raw_data_shape+[len(data)], dtype=complex_)
                except TypeError: # data has no __len__ attribute
                    self._raw_data = zeros(raw_data_shape, dtype=complex_)

            self._raw_data[idx_group] = data

            # storing parameters rows according
            if done_iterations == 0:
                measurement_data = \
                    self._prepare_measurement_result_data(par_names, parameters_values)
                self._measurement_result.set_data(
                    measurement_data)  # TODO: calls deepcopy of the whole measurement data

            done_iterations += 1

            avg_time = (dt.now() - start_time).total_seconds()/done_iterations
            time_left = self._format_time_delta(avg_time*(total_iterations-done_iterations))

            formatted_values_group = \
                        '['+"".join(["%s: %.2e, "%(par_names[idx], value)\
                         for idx, value in enumerate(values_group)])[:-2]+']'

            print("\rTime left: "+time_left+", %s"%formatted_values_group+\
                    ", average cycle time: "+str(round(avg_time, 2))+" s       ",
                    end="", flush=True)

            if self._interrupted:
                self._interrupted = False
                return
        self._measurement_result.set_recording_time(dt.now()-start_time)
        print("\nElapsed time: %s"%\
                    self._format_time_delta((dt.now()-start_time)\
                                                            .total_seconds()))
        self._measurement_result.set_is_finished(True)

    def _recording_iteration(self):
        '''
        This method must be overridden for each new measurement type.

        Should contain the recording logic and set the data of the
        corresponding MeasurementResult object.
        See lib2.SingleToneSpectroscopy.py as an example implementation
        '''
        raise NotImplementedError

    def _prepare_measurement_result_data(self, parameter_names, parameter_values):
        '''
        TODO:OPT look at the implementation, it uses deepcopy for all the data
        This method MAY be overridden for a new measurement type.

        An override is needed if you have _recording_iteration(...) that returns
        an array, so effectively you have an additional parameter that is swept
        automatically. You will be able to pass its values and name in the
        overridden method (see lib2.SingleToneSpectroscopy.py).
        '''
        measurement_data = self._measurement_result.get_data()
        measurement_data.update(zip(parameter_names, parameter_values))
        measurement_data["data"] = self._raw_data
        return measurement_data

    def _detect_resonator(self, plot=False, tries_number=3):
        """
        Finds frequency of the resonator visible on the VNA screen
        """
        vna = self._vna
        tries_number = 3
        for i in range(0, tries_number):
            vna.avg_clear(); vna.prepare_for_stb(); vna.sweep_single(); vna.wait_for_stb()
            frequencies, sdata = vna.get_frequencies(), vna.get_sdata()
            vna.autoscale_all()
            RD = ResonatorDetector(frequencies, sdata, plot=plot)

            result = RD.detect()
            if result is not None:
                break
            else:
                print("\rFit was inaccurate (try #%d), retrying"%i, end = "")
        #if result is None:
            #print(frequencies, sdata)
        return result

    def _detect_qubit(self):
        '''
        TODO: To find a peak/dip from a qubit in line automatically (to be implemented)
        '''
        raise NotImplemented

    def _write_to_log(self, line = 'Unknown measurement', parameters = ''):
        '''
        A method writes line with the name of measurement
        (probably with formatted parameters) to log list
        '''
        self._log += str(dt.now().replace(microsecond=0)) + "  " + line + parameters + '\n'

    def return_log(self):
        '''
        Returns string of log containing all addressed measurements in chronological order.
        '''
        return self._log

    '''
    @desc: outdated method. Proposal to delete
    def _construct_fixed_parameters(self):

        self._fixed_params = {}

        yn = input('Do you want to set the dictionary of fixed parameters interactively: yes/no \n')

        if yn == 'yes':
            while True:
                dev_name  = input('Enter name of device : "exa", "vna", etc.\n'+'If finished enter whatever else you want \n')
                if dev_name in self._actual_devices.keys():
                    self._fixed_params[dev_name] = {}
                    print('Enter parameter and value as: "frequency 5e9" and press Enter)\n' + \
                            'If finished with this device enter "stop next"\n')
                    while True:
                        par_name, vs = input().split()
                        if par_name == 'stop':
                            print('\n')
                            break
                        else:
                            value = float(vs)
                            self._fixed_params.get(dev_name)[par_name] = value
                else:
                    return self._fixed_params
        elif yn == 'no':
            return self._fixed_params

        else:
            return self._fixed_params
    '''

    def _format_time_delta(self, delta):
        hours, remainder = divmod(delta, 3600)
        minutes, seconds = divmod(remainder, 60)
        return '%s h %s m %s s' % (int(hours), int(minutes), round(seconds, 2))

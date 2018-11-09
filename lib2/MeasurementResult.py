'''
Base class for all measurement results.

Classes implementing this interface should implement following features:
    -- Sample name, experiment title
    -- Time data
        Start datetime, recording time
    -- Experimental data processing
        -- Storage and basic manipulation necessary for each measurement type
        -- Export to human-readable text files
    -- Visualization
        Nice and detailed plots. Should support:
        -- Static mode
            To visualize the data on user demand
        -- Dynamic mode
            To perform live updates during the recording
    -- Context
        MeasurementResult objects should contain information about the state
        of the equipment and general measurement parameters:
        -- List of the equipment involved in the experiment
            Each device should contain a snapshot of all control parameters
        -- Other data
            Useful data, specific to each measurement type,
    -- Thread safety of the data (already implemented here)
'''

from numpy import *
import copy

import os, fnmatch, platform
import pickle
from threading import Lock
from matplotlib import pyplot as plt
from datetime import datetime


def find(pattern, path):
    result = []
    for root, dirs, files in os.walk(path):
        for name in files:
            if fnmatch.fnmatch(name, pattern):
                result.append(os.path.join(root, name))
    return result

class ContextBase():

    def __init__(self):
        self._equipment = {}
        self._comment = ""

    def get_equipment(self):
        return self._equipment

    def to_string(self):
        return "Equipment with parameters:\n"+str(self._equipment)+\
            "\nComment:\n"+self._comment

    def update_context(self, equipment = {}, comment = ""):
        context._equipment.update(equipment)
        context._comment.join(comment)


class MeasurementResult():

    def __init__(self, name, sample_name):
        self._name = name
        self._sample_name = sample_name
        self._data_lock = Lock()
        self._data = {}
        self._context = ContextBase()
        # Dynamic visualization fileds, see _prepare_figure(...) docstring below

        self._dynamic_figure = None # the figure that will be dynamically updated
        self._dynamic_axes = None # axes of the subplots contained inside it
        self._dynamic_caxes = None # colorbar axes for heatmaps


    def set_parameter_names(self, parameter_names):
        self._parameter_names = parameter_names


    @staticmethod
    def load(sample_name, name, date = '', return_all=False):
        '''
        Finds all files with matching result name within the file structure of ./data/
        folder and prompts user to resolve any ambiguities.

        Returns:
            an instance of the child class containing the specific measurement
            result

        Example usage:
        >>> from lib2.MeasurementResult import MeasurementResult
        >>> result = MeasurementResult.load("<sample_name>", "<name>")

        If the user hits EOF (*nix: Ctrl-D, Windows: Ctrl-Z+Return), raise EOFError.
        On *nix systems, readline is used if available.
        '''

        if platform.system() is "Windows":
            paths = find(name+'.pkl', 'data\\'+sample_name+'\\'+date)
            sep = "\\"
        else:
            paths = find(name+'.pkl', 'data/'+sample_name+'/'+date)
            sep = "/"
        path = None
        if len(paths)>1:
            dates = [datetime.strptime(path.split(sep)[2], "%b %d %Y")\
                                                            for path in paths]
            z = zip(dates, paths)
            sorted_dates, sorted_paths = zip(*sorted(z))
            paths = sorted_paths

            if return_all:
                dict_of_res=[]
                for idx, path in enumerate(paths):
                    try:
                        with open(path, "rb") as f:
                            dict_of_res.append(pickle.load(f))
                    except pickle.UnpicklingError as e:
                        dict_of_res.append(e)

                return dict_of_res
            else:
                for idx, file in enumerate(paths):
                    print(idx, file)
                print("More than one file found. Enter an index from listed above:")
                index = input()
                path = paths[int(index)]
        elif len(paths) == 1:
            path = paths[0]
        else:
            print("Measurement result '%s' for the sample '%s' not found"%(name, sample_name))
            return

        with open(path, "rb") as f:
            if not return_all:
                return pickle.load(f)
            else:
                return [pickle.load(f)]

    def get_save_path(self):

        sample_directory = 'data\\'+self._sample_name
        if not os.path.exists(sample_directory):
            os.makedirs(sample_directory)

        date_directory =  "\\"+ self.get_start_datetime().strftime("%b %d %Y")
        if not os.path.exists(sample_directory+date_directory):
            os.makedirs(sample_directory+date_directory)

        time_directory = "\\"+self.get_start_datetime().strftime("%H-%M-%S")+" - "+self._name
        if not os.path.exists(sample_directory+date_directory+time_directory):
            os.makedirs(sample_directory+date_directory+time_directory)

        return sample_directory+date_directory+time_directory+"\\"

    def __getstate__(self):
        d = dict(self.__dict__)
        del d['_data_lock']
        return d

    def __setstate__(self, state):
        self.__dict__.update(state)
        self._data_lock = Lock()

    def save(self):
        '''
        This method may be overridden in a child class but super().save()
        must be called in the beginning of the overridden method.

        Saves the MeasurementResult object using pickle, creating the folder
        structure if necessary.

        The path is structured as follows:
            data/<sample name>/DD MM YYYY/HH-MM-SS - <name>/

        At least <name>.pkl with serialized object, <name>_raw_data.pkl with raw
        data only and human-readable context will be stored, though
        child methods should save additional files in their overridden methods,
        i.e. plot pictures
        '''
        with self._data_lock:
            with open(self.get_save_path()+self._name+'.pkl', 'w+b') as f:
                pickle.dump(self, f)
            with open(self.get_save_path()+self._name+'_raw_data.pkl', 'w+b') as f:
                pickle.dump(self._data, f)
            with open(self.get_save_path()+self._name+'_context.txt', 'w+') as f:
                f.write(self.get_context().to_string())

        fig, axes, caxes = self.visualize()
        plt.savefig(self.get_save_path()+self._name+".png", bbox_inches='tight')
        plt.savefig(self.get_save_path()+self._name+".pdf", bbox_inches='tight')
        plt.close(fig)

    def visualize(self, maximized = True):
        '''
        Generates the required plots to visualize the measurement result. Should
        be implemented for each subclass.
        '''
        fig, axes, caxes = self._prepare_figure()
        self._plot(axes, caxes)
        figManager = plt.get_current_fig_manager()
        if maximized:
            try:
                figManager.window.showMaximized()
            except:
                figManager.window.state('zoomed')
        return fig, axes, caxes

    def _visualize_dynamic(self):
        '''
        Dynamically visualizes the measurement data. To be used in the recording
        scripts (note the underscore which makes this method private)
        '''
        if self._dynamic_figure is None:
            fig, axes, caxes = self._prepare_figure()
            self._dynamic_figure = fig
            self._dynamic_axes = axes
            self._dynamic_caxes = caxes
            figManager = plt.get_current_fig_manager()
            try:
                figManager.window.showMaximized()
            except:
                figManager.window.state('zoomed')
            # figManager.window.showMaximized()

        self._plot(self._dynamic_axes, self._dynamic_caxes)

    def _prepare_figure(self):
        '''
        This method must be implemented for each new measurement type.

        See lib2.SingleToneSpectroscopy.py for an example implementation
        Should return:
        figure: matplotlib figure
            figure window
        axes: array of matplotlib.Axes objects
            axes of the subplots contained inside the figure
        caxes: array of colorbar axes
            these axes are obtained by calling matplotlib.colorbar.make_axes(ax)
            and then may be used to updated colorbars for each subplot
        '''
        pass

    def _plot(self, axes, caxes):
        '''
        This method must be implemented for each new measurement type.

        The axes and caxes are those created by _prepare_figure(...) method and
        should be used here to visualize the data
        '''
        pass

    def finalize(self):
        '''
        This method may be overridden in a child class but super().finalize()
        must be called in the beginning of the overridden method.

        Method that should be called FROM THE MAIN THREAD upon the end of the
        measurement recording.

        Should at least close the dynamically updated figure (implemented)
        '''
        plt.close(self._dynamic_figure)
        self._dynamic_figure = None
        self._dynamic_axes = None
        self._dynamic_caxes = None

    def set_is_finished(self, is_finished):
        self._is_finished = is_finished

    def is_finished(self):
        return self._is_finished

    def get_start_datetime(self):
        return self._datetime

    def set_start_datetime(self, datetime):
        self._datetime = datetime

    def get_recording_time(self):
        return self._recording_time

    def set_recording_time(self, recording_time):
        self._recording_time = recording_time

    def get_data(self):
        with self._data_lock:
            return copy.deepcopy(self._data)

    def get_context(self):
        return self._context

    def set_data(self, data):
        '''
        Data should consist only of built-in data types to be easy to use on
        other computers without the whole measurement library.
        '''
        with self._data_lock:
            self._data = copy.deepcopy(data)

    def _latex_float(self, f):
        float_str = "{0:.2e}".format(f)
        base, exponent = float_str.split("e")
        if int(exponent)!=0:
            return r"${0} \times 10^{{{1}}}$".format(base, int(exponent))
        else:
            return base

    def copy(self):
        with self._data_lock:
            return copy.deepcopy(self)

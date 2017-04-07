'''
Basic interface for all measurement results.

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
'''

import copy
import os, fnmatch
import pickle

def find(pattern, path):
    result = []
    for root, dirs, files in os.walk(path):
        for name in files:
            if fnmatch.fnmatch(name, pattern):
                result.append(os.path.join(root, name))
    return result

class ContextBase():

    def __init__(equipment = {}, comment = ""):
        '''
        Parameters:
        -----------
        equipment: dict
            a dict containing dicts representing device parameters
        '''
        self._equipment = equipment
        self._comment = comment

    def to_string(self):
        return "Equipment with parameters:\n"+str(self._equipment)+
            "\nComment:\n"+self._comment

class MeasurementResult():

    def __init__(name, sample_name):
        self._name = name
        self._sample_name = sample_name

    @staticmethod
    def load(name):
        '''
        Finds all files with matching name within the file structure of ./data/
        folder and prompts user to resolve any ambiguities.

        Returns:
            an instance of the correct child class
        '''
        paths = find(name+'.pkl', 'data/')
        path = None
        if len(paths)>1:
            print(zip(range(len(paths)), paths))
            print("More than one file found. Enter an index from listed above:")
            index = input()
            path = paths[index]
        elif len(path) == 1:
            path = paths[0]
        else:
            print("Measurement result %s not found"%name)
            return

        with open(path, "rb") as f:
            return pickle.load(f)

    def get_save_path(self, name):

        sample_directory = 'data\\'+sample_name
        if not os.path.exists(directory):
            os.makedirs(directory)

        date_directory =  "\\"+ self.get_start_datetime().strftime("%b %d %Y")
        if not os.path.exists(sample_directory+date_directory):
            os.makedirs(sample_directory+date_directory)

        time_directory = "\\"+measurement.get_start_datetime().strftime("%H-%M-%S")+" - "+name
        if not os.path.exists(sample_directory+date_directory+time_directory):
            os.makedirs(sample_directory+date_directory+time_directory)

        return sample_directory+date_directory+time_directory+"\\"

    def save(self, name):
        '''
        Saves the MeasurementResult object using pickle, creating the folder
        structure if necessary.

        The path is structured as follows:
            data/DD MMM YYYY/HH-MM-SS - <name>/

        At least <name>.pkl with serialized object, <name>_raw_data.pkl with raw
        data only and human-readable context will be stored, though
        child methods should save additional files in their overridden methods,
        i.e. plot pictures
        '''

        with open(get_save_path(self, name)+name+'.pkl', 'w+b') as f:
    		pkl.dump(self, f)
        with open(get_save_path(self, name)+name+'_raw_data.pkl', 'w+b') as f:
            pkl.dump(self.get_data(), f)
        with open(get_save_path(self, name)+name+'context.txt', 'w+') as f:
            f.write(self.get_context().to_string())

    def visualize(self):
        '''
        Generates the required plots to visualize the measurement result. Should
        be implemented for each subclass.
        '''
        pass

    def get_start_datetime(self):
        return self._datetime

    def set_start_datetime(self, datetime):
        self._datetime = datetime

    def get_recording_time(self):
        return self._recording_time

    def set_recording_time(self, recording_time):
        self._recording_time = recording_time

    def get_data(self):
        return self._data

    def set_data(self, data):
        '''
        Data should consist only of built-in data types to be easy to use on
        other computers without the whole measurement library.
        '''
        self._data = data

    def set_context(self, context):
        self._context = context

    def get_context(self):
        return self._context

    def copy(self):
        return copy.deepcopy(self)

# KeysightAWG.py
# Gleb Fedorov <vdrhc@gmail.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA


from numpy import *
from lib2.IQPulseSequence import *


class AWGChannel():

    def __init__(self, host_awg, channel_number):

        self._host_awg = host_awg
        self._channel_number = channel_number

    def output_arbitrary_waveform(self, waveform, frequency, blocking):

        self._host_awg.output_arbitrary_waveform(waveform, frequency,
                                self._channel_number, blocking)

class IQAWG():

    def __init__(self, channel_I, channel_Q):
        self._channels = [channel_I, channel_Q]

    def set_parameters(self, parameters):
        '''
        Sets various parameters from a dictionary

        Parameters:
        -----------
        parameteres: dict {"param_name":param_value, ...}
        '''
        par_names = ["calibration"]
        for par_name in par_names:
            if par_name in parameters.keys():
                setattr(self, "_"+par_name, parameters[par_name])

    def get_calibration(self):
        return self._calibration

    def set_channel_coupling(self, state):
        '''
        Assuming that user knows what he is doing here. Make sure your channels
        are synchronized!
        '''
        pass

    def get_pulse_builder(self):
        '''
        Returns a PulseBuilder instance using the IQ calibration loaded before
        '''
        return PulseBuilder(self._calibration)

    def output_continuous_IQ_waves(self, frequency, amplitudes, relative_phase,
        offsets, waveform_resolution):
        '''
        Prepare and output a sine wave of the form: y = A*sin(2*pi*frequency + phase) + offset
        on both of the I and Q channels
        Parameters:
        -----------
        frequency: float, Hz
            frequency of the output waves
        amplitudes: float, V
            amplitude of the output waves
        phase: float
            relative phase in radians of the iutput waves
        offsets: float, V
            voltage offset of the waveforms
        waveform_resolution: float, ns
            resolution in time of the arbitrary waveform representing one period
            of the wave
        channel: 1 or 2
            channel which will output the wave
        '''
        self._output_continuous_wave(frequency, amplitudes[0], relative_phase,
            offsets[0], waveform_resolution, 1, blocking = False)
        self._output_continuous_wave(frequency, amplitudes[1], 0,
            offsets[1], waveform_resolution, 2, blocking = True)

    def _output_continuous_wave(self, frequency, amplitude, phase, offset,
            waveform_resolution, channel, blocking):
        '''
        Prepare and output a sine wave of the form: y = A*sin(2*pi*frequency + phase) + offset

        Parameters:
        -----------
        frequency: float, Hz
            frequency of the output wave
        amplitude: float, V
            amplitude of the output wave
        phase: float
            phase in radians of the iutput wave
        offset: float, V
            voltage offset of the waveform
        waveform_resolution: float, ns
            resolution in time of the arbitrary waveform representing one period
            of the wave
        channel: 1 or 2
            channel which will output the wave
        '''

        N_points = 1/frequency*2/waveform_resolution*1e9+1 if frequency !=0 else 3
        waveform = amplitude*sin(2*pi*linspace(0,1,N_points)*2+phase) + offset
        self._channels[channel-1].output_arbitrary_waveform(waveform, frequency/2,
                                                            blocking=blocking)

    def output_pulse_sequence(self, pulse_sequence, blocking=True):
        '''
        Load and output given IQPulseSequence.

        Parameters:
        -----------
        pulse_sequence: IQPulseSequence instance
        '''
        frequency = 1/pulse_sequence.get_duration()*1e9

        self._channels[0].output_arbitrary_waveform(pulse_sequence\
                                            .get_I_waveform(), frequency,
                                            blocking=False)
        self._channels[1].output_arbitrary_waveform(pulse_sequence
                                            .get_Q_waveform(), frequency,
                                            blocking=True if blocking else False)

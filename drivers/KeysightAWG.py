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


from drivers.instrument import Instrument
from matplotlib import pyplot as plt
from numpy import *
import visa
import types
import time
import logging

from enum import Enum

class WaveformType(Enum):
	pulse = "PULS"
	square = "SQUA"
	ramp = "RAMP"
	noise = "NOIS"
	dc = "DC"
	sine = "SIN"
	arbitrary = "USER"


class PulseSequence():
	def __init__(self):

		self._waveform = ndarray(0)
		self._pulses = []

	def append_pulse(self, points):
		self._pulses.append(dict(start=len(self._waveform), end=len(self._waveform)+len(points)))
		self._waveform = concatenate((self._waveform, points))

	def get_pulse(self, pulse_idx):
		return self._waveform[self._pulses[idx]["start"], self._pulses[idx]["end"]]

	def modulate_pulse(self, pulse_idx, modulation):
		unmodulated_pulse = self.get_pulse(pulse_idx)
		if unmodulated_pulse.shape != modulation:
			raise ValueError("Modulation for the pulse should have same length")
		modulated_pulse = unmodulated_pulse*modulation
		self._waveform[self._pulses[idx]["start"]:self._pulses[idx]["end"]] = modulated_pulse

	def plot(self):
		plt.plot(self._waveform*5)


class PulseBuilder():

	def __init__(self, awg, iqmx_calibration, grid_resolution=1):
		'''
		Build a PulseBuilder instance for a previously created KeysigtAWG.

		Parameters:
		-----------
		awg: KeysightAWG
			An instance of the KeysightAWG for which the waveforms will be defined
		iqmx_calibration: IQCalibrationData
			Calibration data for the IQ mixer that will be used to send out the pulse sequence.
			Make sure that the radiation parameters of this calibration are in match with your actual settings
		grid_resolution: float, ns
			The minimal time step available for the pulse sequences created by this builder. 
			Can't be shorter then 0.5 ns
		'''

		self._awg = awg
		self._iqmx_calibration = iqmx_calibration
		self._grid_resolution = grid_resolution
		self._pulse_seq_I = PulseSequence()
		self._pulse_seq_Q = PulseSequence()


	def add_zero_pulse(self, duration):
		'''
		Adds a pulse with zero amplitude at frequency f_lo-f_if to the sequence

		Parameters:
		-----------
		duration: float, ns
			Duration of the pulse in nanoseconds
		'''
		vdc1, vdc2 = self._iqmx_calibration.get_optimization_results()[0]["dc_offsets"]
		self._pulse_seq_I.append_pulse(zeros(int(duration/self._grid_resolution))+vdc1/5)
		self._pulse_seq_Q.append_pulse(zeros(int(duration/self._grid_resolution))+vdc2/5)
		return self

	def add_sine_pulse(self, duration, phase):
		"""
		Adds a pulse with amplitude defined by the iqmx_calibration at frequency f_lo-f_if and some phase to the sequence

		Parameters:
		-----------
		duration: float, ns
			Duration of the pulse in nanoseconds
		phase: float, rad
			Adds a relative phase to the outputted signal
		"""
		if_offs1, if_offs2 = self._iqmx_calibration.get_optimization_results()[0]["if_offsets"]
		if_amp1, if_amp2 = self._iqmx_calibration.get_optimization_results()[0]["if_amplitudes"]
		if_phase = self._iqmx_calibration.get_optimization_results()[0]["if_phase"]
		frequency = self._iqmx_calibration.get_radiation_parameters()["if_frequency"]
		self._pulse_seq_I.append_pulse(if_amp1/5*sin(2*pi*frequency/1e9*linspace(0,duration,duration/self._grid_resolution)+if_phase+phase) + if_offs1/5)
		self._pulse_seq_Q.append_pulse(if_amp2/5*sin(2*pi*frequency/1e9*linspace(0,duration,duration/self._grid_resolution)+phase) + if_offs2/5)
		return self

	def build(self):
		return dict(I=self._pulse_seq_I, Q=self._pulse_seq_Q)

class KeysightAWG(Instrument):

	def __init__(self, address):
		'''Create a default Keysight AWG instrument'''
		Instrument.__init__(self, 'AWG', tags=['physical'])
		self._address = address
		rm = visa.ResourceManager()
		self._visainstrument = rm.open_resource(self._address)


		self.add_parameter('outp1', 
		flags = Instrument.FLAG_GETSET, units = '', type = int)

		self.add_parameter('outp2', 
		flags = Instrument.FLAG_GETSET, units = '', type = int)

		self.add_parameter('outp1_compl', 
		flags = Instrument.FLAG_GETSET, units = '', type = int)

		self.add_parameter('outp2_compl', 
		flags = Instrument.FLAG_GETSET, units = '', type = int)

		self.add_parameter('2nd_delay', 
		flags = Instrument.FLAG_GETSET, units = '', type = float)

		self.add_parameter('1st_delay', 
		flags = Instrument.FLAG_GETSET, units = '', type = float)

		self.add_parameter('2nd_width', 
		flags = Instrument.FLAG_GETSET, units = '', type = float)

		self.add_parameter('1st_width', 
		flags = Instrument.FLAG_GETSET, units = '', type = float)



		self.add_function("apply_waveform")


	# High-level functions

	def output_continuous_wave(self, frequency=100e6, amplitude=0.1, phase=0, offset=0, channel=1):
		'''
		Prepare and output a sine wave of the form: y = A*sin(2*pi*frequency + phase) + offset

		Parameters:
		-----------
		frequency: float
			frequency of the output wave
		amplitude: float 
			amplitude of the output wave
		phase: float
			phase in radians of the iutput wave
		offset: float
			voltage offset of the waveform
		chanel:1 or 2
			channel which witll output the wave
		'''

		waveform =amplitude/5*sin(2*pi*linspace(0,1,100)+phase) + offset/5
		self.load_arbitrary_waveform_to_volatile_memory(waveform, channel)
		self.prepare_waveform(WaveformType.arbitrary, frequency, 5, 0, channel)
		self.set_output(channel, 1)



	# Basic low-level functions

	def apply_waveform(self, waveform, freq, amp, offset, channel=1):
		'''
		Set one of the pre-loaded waveforms as output and output it. 
		This function will turn both + and - outputs of the channel. If you don't want this behaviour,
		you may use the prepare_waveform fucntion.

		Parameters:
		-----------
		waveform: KeysightAWG.WaveformType
			one of the supported types of the waveform
		freq: float
			frequency of the applied waveform, i.e. 1000 or 1e3
		amp: float
			amplitude of the applied signal
		offset: float
			dc-offset added to the signal
		channel = 1: int
			channel which will be set to ON and used as output, 1 or 2

		'''

		self._visainstrument.write("*OPC")
		self._visainstrument.write(":APPL%i:%s %f, %f, %f"%(channel, waveform.value, freq, amp, offset))
		self._visainstrument.query("*OPC?")

	def prepare_waveform(self, waveform, freq, amp, offset, channel=1):
		'''
		Set one of the pre-loaded waveforms as output, but do not output anything.

		Parameters:
		-----------
		waveform: KeysightAWG.WaveformType
			one of the supported types of the waveform
		freq: float
			frequency of the applied waveform, i.e. 1000 or 1e3
		amp: float
			amplitude of the applied signal
		offset: float
			dc-offset added to the signal
		channel = 1: int
			channel which will be set to ON and used as output, 1 or 2

		'''
		self._visainstrument.write("*OPC")
		self._visainstrument.write(":FUNC{0} {1}; :FREQ{0} {2}; :VOLT{0} {3}; :VOLT:OFFS{0} {4}".format(channel, waveform.value, freq, amp, offset))
		self._visainstrument.write("*OPC?")

	def list_arbitrary_waveforms(self, channel=1):
		'''
		Get all waveform names currently loaded in the permanent memory of the specified channel.

		Parameters:
		-----------
			channel=1: 1 or 2
				The channel for shich the waveforms will be listed

		'''
		return self._visainstrument.query(":DATA%d:CAT?"%channel).replace('"', "").replace('\n', "").split(",")


	def select_arbitary_waveform(self, waveform_name, channel=1):
		'''
		Select one of the seven built-in arbitrary waveforms, 
		one of the four userdefined waveforms, or the waveform currently 
		downloaded to volatile memory. 
		This command does not output the selected arbitrary waveform. 
		Use the apply_waveform command with WaveformType.arbitrary
		to output the selected waveform.

		Parameters:
		-----------
		waveform_name: string
			one of the waveform names returned by 
			list_arbitrary_waveforms method
		channel=1: int 
			channel for which the waveform will be selected, 1 or 2

		'''
		if waveform_name in self.list_arbitrary_waveforms():
			self._visainstrument.write(":FUNC%i:USER %s"%(channel, waveform_name))
		else:
			raise Value("No such waveform, check available waveforms with list_arbitrary_waveforms method")



	def get_arbitary_waveform(self, channel=1):
		'''
		Get the name of the currently selected arbitrary waveform.

		Parameters:
		-----------
		channel=1: int 
			channel for which the waveform name will aquired, 1 or 2

		'''
		return self._visainstrument.query(":FUNC%i:USER?"%channel)



	def load_arbitrary_waveform_to_volatile_memory(self, waveform_array, channel=1):
		'''
		Load an arbitrary waveform as an array into volatile memory.
		It then will be available in select_arbitrary_waveform method.
		
		The actual timescale and amplitude of the waveform will be defined by
		its frequency and amplitude as specified in apply_waveform method.

		Parameters:
		-----------
		waveform_array: ndarray
			an array of floats within the range [-1,1], of length
			131072 at maximum; if the range is too large the array
			will be normalized
		channel : 1 or 2
			channel index where the waveform will be stored

		'''
		if max(waveform_array) > 1:
			array_string = "".join([str(num)+", " for num in waveform_array/max(waveform_array)])[:-2]
		else:
			array_string = "".join([str(num)+", " for num in waveform_array])[:-2]

		self._visainstrument.write("*OPC")
		self._visainstrument.write(":DATA%d VOLATILE, "%channel+array_string)
		self._visainstrument.query("*OPC?")



	'''Output switches'''


	def set_output(self, channel, status):
		'''
		Control the output on a channel

		Parameters:
		-----------
		channel: 1 or 2
			channel to switch output for
		status: int
			1 for ON and 0 for OFF

		'''
		self._visainstrument.write("OUTP%i %i"%(channel, status))

	def do_set_outp1(self, status):
		'''
		Turn first output channnel on and off.

		Parameters:
		-----------
		status: int
			1 for ON and 0 for OFF

		'''
		self._visainstrument.write("OUTP1 %i"%status)

	def do_get_outp1(self):
		'''Check if first output channnel is turned on'''
		return self._visainstrument.query("OUTP1?") 
	
	def do_set_outp2(self, status):
		'''
		Turn second output channnel on and off.

		Parameters:
		-----------
		status: int
			1 for ON and 0 for OFF

		'''
		self._visainstrument.write("OUTP2 %i"%status)

	def do_get_outp2(self):
		'''Check if second output channnel is turned on'''
		return self._visainstrument.query("OUTP2?") 

	def do_set_outp1_compl(self, status):
		'''
		Turn first output complement channnel on and off.

		Parameters:
		-----------
		status: int
			1 for ON and 0 for OFF

		'''
		self._visainstrument.write("OUTP1:COMP %i"%status)

	def do_get_outp1_compl(self):
		'''Check if first output complement channnel is turned on'''
		return self._visainstrument.query("OUTP1:COMP?") 
	
	def do_set_outp2_compl(self, status):
		'''
		Turn second output complement channnel on and off.

		Parameters:
		-----------
		status: int
			1 for ON and 0 for OFF

		'''
		self._visainstrument.write("OUTP2:COMP %i"%status)

	def do_get_outp2_compl(self):
		'''Check if second output complement channel is turned on'''
		return self._visainstrument.query("OUTP2:COMP?") 

	def do_set_2nd_delay(self,delay):
		'''
		Set a delay to the second puls.

		Parameters:
		-----------
		channel: int (1,2)
		delay: float in ns

		'''
		return self._visainstrument.write("PULS:DEL2 %.1fNS"%delay)

	def do_get_2nd_delay(self):
		'''
		Get a delay from 2nd channel
		'''
		return self._visainstrument.query("PULS:DEL2?")

	def do_set_1st_delay(self,delay):
		'''
		Set a delay to the first puls.

		Parameters:
		-----------
		channel: int (1,2)
		delay: float in ns

		'''
		return self._visainstrument.write("PULS:DEL1 %.1fNS"%delay)

	def do_get_1st_delay(self):
		'''
		Get a delay from 2nd channel
		'''
		return self._visainstrument.query("PULS:DEL1?")

	def do_set_2nd_width(self,width):
		'''
		Set a width to the second puls.

		Parameters:
		-----------
		channel: int (1,2)
		delay: float in ns

		'''
		return self._visainstrument.write("FUNC2:PULS:WIDT %.1fNS"%width)

	def do_get_2nd_width(self):
		'''
		Get a delay from 2nd channel
		'''
		return self._visainstrument.query("FUNC2:PULS:WIDT?")

	def do_set_1st_width(self,width):
		'''
		Set a width to the first puls.

		Parameters:
		-----------
		channel: int (1,2)
		delay: float in ns

		'''
		return self._visainstrument.write("FUNC1:PULS:WIDT %.1fNS"%width)

	def do_get_1st_width(self):
		'''
		Get a delay from 2nd channel
		'''
		return self._visainstrument.query("FUNC1:PULS:WIDT?")



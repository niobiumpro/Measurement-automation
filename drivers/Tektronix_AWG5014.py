# Tektronix_AWG5014.py class, to perform the communication between the Wrapper and the device
# Pieter de Groot <pieterdegroot@gmail.com>, 2008
# Martijn Schaafsma <qtlab@mcschaafsma.nl>, 2008
# Guenevere Prawiroatmodjo <guen@vvtp.tudelft.nl>, 2009
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
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
import visa
import types
import logging
import numpy
import struct

class Tektronix_AWG5014(Instrument):
	'''
	This is the python driver for the Tektronix AWG5014
	Arbitrary Waveform Generator

	Usage:
	Initialize with
	<name> = instruments.create('name', 'Tektronix_AWG5014', address='<GPIB address>',
		reset=<bool>, nop=<int>)

	think about:    clock, waveform length

	TODO:
	1) Get All
	2) Remove test_send??
	3) Add docstrings
	4) Add 4-channel compatibility
	'''

	def __init__(self, address, reset=False, clock=1e9, nop=1000):
		'''
		Initializes the AWG520.

		Input:
			name (string)    : name of the instrument
			address (string) : GPIB address
			reset (bool)     : resets to default values, default=false
			nop (int)  : sets the number of datapoints

		Output:
			None
		'''
		logging.debug(__name__ + ' : Initializing instrument')
		Instrument.__init__(self, "Tektronix_AWG5014", tags=['physical'])


		self._address = address
		self._visainstrument = visa.ResourceManager()\
			.open_resource(self._address, read_termination="\r\n",
							write_termination="\n")
		self._values = {}
		self._values['files'] = {}
		self._clock = clock
		self._nop = nop
		self._waveforms = [None]*4
		self._markers = [None]*8
		self._clear_all_waveforms()

		# Add parameters
		self.add_parameter('waveform', type=list,
			flags=Instrument.FLAG_GETSET | Instrument.FLAG_GET_AFTER_SET,
			channels=(1, 4), channel_prefix='ch%d_')
		self.add_parameter('digital', type=list,
			flags=Instrument.FLAG_GETSET | Instrument.FLAG_GET_AFTER_SET,
			channels=(1, 8), channel_prefix='ch%d_') # marker 1 ch 1-4 are in 1-4, m2 ch 1-4 are in 5-8
		self.add_parameter('clock', type=float,
			flags=Instrument.FLAG_GETSET | Instrument.FLAG_GET_AFTER_SET,
			minval=1e6, maxval=1e9, units='Hz')
		self.add_parameter('nop', type=int,
			flags=Instrument.FLAG_GETSET | Instrument.FLAG_GET_AFTER_SET,
			minval=100, maxval=1e9, units='Int')
		self.add_parameter('amplitude', type=float,
			flags=Instrument.FLAG_GETSET | Instrument.FLAG_GET_AFTER_SET,
			channels=(1, 4), minval=0, maxval=4.5, units='Volts', channel_prefix='ch%d_')
		self.add_parameter('offset', type=float,
			flags=Instrument.FLAG_GETSET | Instrument.FLAG_GET_AFTER_SET,
			channels=(1, 4), minval=-2, maxval=2, units='Volts', channel_prefix='ch%d_')
		self.add_parameter('marker1_low', type=float,
			flags=Instrument.FLAG_GETSET | Instrument.FLAG_GET_AFTER_SET,
			channels=(1, 4), minval=-2, maxval=2, units='Volts', channel_prefix='ch%d_')
		self.add_parameter('marker1_high', type=float,
			flags=Instrument.FLAG_GETSET | Instrument.FLAG_GET_AFTER_SET,
			channels=(1, 4), minval=-2, maxval=2, units='Volts', channel_prefix='ch%d_')
		self.add_parameter('marker2_low', type=float,
			flags=Instrument.FLAG_GETSET | Instrument.FLAG_GET_AFTER_SET,
			channels=(1, 4), minval=-2, maxval=2, units='Volts', channel_prefix='ch%d_')
		self.add_parameter('marker2_high', type=float,
			flags=Instrument.FLAG_GETSET | Instrument.FLAG_GET_AFTER_SET,
			channels=(1, 4), minval=-2, maxval=2, units='Volts', channel_prefix='ch%d_')
		self.add_parameter('status', type=bool,
			flags=Instrument.FLAG_GETSET | Instrument.FLAG_GET_AFTER_SET,
			channels=(1, 4),channel_prefix='ch%d_')




	def output_arbitrary_waveform(self, waveform, repetition_rate, channel, block=True):
		'''
		Prepare and output an arbitrary waveform repeated at some repetition_rate

		Parameters:
		-----------
		waveform: array
			ADC levels, in Volts
		repetition_rate: foat, Hz
			frequency at which the waveform will be repeated
		channel: 1 or 2
			channel which will output the waveform
		'''
		for idx, existing_waveform in enumerate(self._waveforms):
			if self._waveforms[idx] is not None:
				if (len(existing_waveform) != len(waveform)) and (idx != channel-1):
					self._waveforms[idx] = None
					self._clear_waveform(idx+1)

		self._waveforms[channel-1] = waveform

		self.do_set_waveform(waveform/1.5*2, repetition_rate, channel)
		self.do_set_output(1, channel)
		self.run()
		if block:
			self._visainstrument.query("*OPC?")

	def _clear_waveform(self, channel):
		self._visainstrument.write('WLIST:WAVeform:DELETE "CH%iWFM"'%channel)

	def _clear_all_waveforms(self):
		self._visainstrument.write('WLIST:WAVeform:DELETE ALL')

	def run(self):
		'''
		Initiates the output of a waveform or a sequence. This is equivalent to pressing
		Run/Delete/Stop button on the front panel. The instrument can be put in the run
		state only when output waveforms are assigned to channels.

		Input:
			None

		Output:
			None
		'''
		logging.debug(__name__ + ' : Run/Initiate output of a waveform or sequence')
		self._visainstrument.write('AWGC:RUN:IMM')


	def do_set_output(self, state, channel):
		'''
		This command sets the output state of the AWG.
		Input:
			channel (int) : the source channel
			state (int) : on (1) or off (0)

		Output:
			None
		'''
		logging.debug(__name__ + ' : Set channel output state')
		if (state == 1):
			self._visainstrument.write('OUTP%s:STAT ON' % channel)
		if (state == 0):
			self._visainstrument.write('OUTP%s:STAT OFF' % channel)

	def do_get_output(self, channel):
		'''
		This command gets the output state of the AWG.
		Input:
			channel (int) : the source channel

		Output:
			state (int) : on (1) or off (0)
		'''
		logging.debug(__name__ + ' : Get channel output state')
		return self._visainstrument.ask('OUTP%s:STAT?' % channel)

	def load_waveform(self, channel, filename, drive='C:', path='\\'):
		'''
		Use this command to directly load a sequence file or a waveform file to a specific channel.

		Input:
			channel (int) : the source channel
			filename (str) : the waveform filename (.wfm, .seq)
			drive (str) : the local drive where the file is located (e.g. 'C:')
			path (str) : the local path where the file is located (e.g. '\waveforms')

		Output:
			None
		'''
		logging.debug(__name__ + ' : Load waveform file %s%s%s for channel %s' % (drive, path, filename, channel))
		self._visainstrument.write('SOUR%s:FUNC:USER "%s/%s","%s"' % (channel, path, filename, drive))


	def do_get_nop(self):
		'''
		Returns the number of datapoints in each wave

		Input:
			None

		Output:
			nop (int) : Number of datapoints in each wave
		'''
		return self._nop

	def set_repetition_period(self, repetition_period):
		self.repetition_period = repetition_period
		self.set_nop(int(repetition_period*self.get_clock()))

	def get_repetition_period(self, repetition_period):
		return self.get_numpoint()/self.get_clock()

	def do_set_nop(self, numpts):
		'''
		Sets the number of datapoints in each wave.
		This acts on all channels.

		Input:
			numpts (int) : The number of datapoints in each wave

		Output:
			None
		'''
		#logging.debug(__name__ + ' : Trying to set nop to %s' % numpts)
		#if numpts != self._nop:
		#    logging.warning(__name__ + ' : changing nop. This will clear all waveforms!')

		#response = raw_input('type "yes" to continue')
		#if response is 'yes':
		#    logging.debug(__name__ + ' : Setting nop to %s' % numpts)
		self._nop = numpts
		self.clear_waveforms()
		#else:
		#    print 'aborted'

	def do_get_clock(self):
		'''
		Returns the clockfrequency, which is the rate at which the datapoints are
		sent to the designated output

		Input:
			None

		Output:
			clock (int) : frequency in Hz
		'''
		return self._clock

	def do_set_clock(self, clock):
		'''
		Sets the rate at which the datapoints are sent to the designated output channel

		Input:
			clock (int) : frequency in Hz
		'''
		logging.warning(__name__ + ' : Clock set to %s. This is not fully functional yet. To avoid problems, it is better not to change the clock during operation' % clock)
		self._clock = clock
		self._visainstrument.write('SOUR:FREQ %f' % clock)

	def do_set_waveform(self, waveform, repetition_rate, channel):
		import numpy as np
		num_points = len(waveform)-1
		waveform = waveform[:-1]
		w = np.zeros((num_points,),dtype=np.float)
		m1 = np.zeros((num_points,),dtype=np.int)
		m2 = np.zeros((num_points,),dtype=np.int)

		m1[:len(m1)//2] = 1

		if len(waveform)<len(w):
			w[:len(waveform)] = waveform
		else:
			w[:] = waveform[:len(w)]

		filename = 'test_ch{0}.wfm'.format(channel)

		self.send_waveform(w,m1,m2,filename, repetition_rate*num_points)
		self.load_waveform(channel, filename)
		# self.do_set_filename(filename, channel=channel)

	def do_get_waveform(self, channel):
		return self._waveforms[channel-1]

	def do_set_digital(self, marker, channel):
		import numpy as np
		num_points = self.get_nop()
		# pad waveform with zeros
		# or maybe something better?
		w = np.zeros((num_points,),dtype=np.float)
		m1 = np.zeros((num_points,),dtype=np.int)
		m2 = np.zeros((num_points,),dtype=np.int)
		# add markers

		if len(marker)<len(m1):
			m1[:len(marker)] = marker
		else:
			m1[:] = marker[:len(m1)]

		if not (self._markers[(channel-1+4)%8] is None):
			if len(self._markers[(channel-1+4)%8])<len(m2):
				m2[:len(self._markers[(channel-1+4)%8])] = self._markers[(channel-1+4)%8]
			else:
				m2[:] = self._markers[(channel-1+4)%8][:len(m2)]

		if not (self._waveforms[(channel-1)%4] is None):
			if len(self._waveforms[(channel-1)%4])<len(w):
				w[:len(self._waveforms[(channel-1)%4])] = self._waveforms[(channel-1)%4]
			else:
				w[:] = self._waveforms[(channel-1)%4][:len(w)]

		filename = 'test_ch{0}.wfm'.format(channel)

		self._markers[channel-1] = m1
		if (channel-1+4)<8:
			self.send_waveform(w,m1,m2,filename,self.get_clock())
		else:
			self.send_waveform(w,m2,m1,filename,self.get_clock())
		self.do_set_filename(filename, channel=(channel-1)%4+1)
		self.do_set_output (1, channel=(channel-1)%4+1)

	def do_get_digital(self, channel):
		return self._markers[channel-1]

	# def set_filename_fast(self, name, channel):


	def do_set_filename(self, name, channel):
		'''
		Specifies which file has to be set on which channel
		Make sure the file exists, and the nop and clock of the file
		matches the instrument settings.

		If file doesn't exist an error is raised, if the nop doesn't match
		the command is neglected

		Input:
			name (string) : filename of uploaded file
			channel (int) : 1 or 2, the number of the designated channel

		Output:
			None
		'''
		logging.debug(__name__  + ' : Try to set %s on channel %s' % (name, channel))
		exists = False
		self._visainstrument.write('MMEM:IMP "%s", "%s", WFM' % (name,name))
		self._visainstrument.write('SOURCE%s:WAVEFORM "%s"' % (channel,name))
		if name in self._values['files']:
			exists= True
			logging.debug(__name__  + ' : File exists in local memory')
			self._values['recent_channel_%s' % channel] = self._values['files'][name]
			self._values['recent_channel_%s' % channel]['filename'] = name
		else:
			logging.debug(__name__  + ' : File does not exist in memory, \
			reading from instrument')
			lijst = self._visainstrument.ask('MMEM:CAT? "C:"')
			bool = False
			bestand=""
			for i in range(len(lijst)):
				if (lijst[i]=='"'):
					bool=True
				elif (lijst[i]==','):
					bool=False
					if (bestand==name): exists=True
					bestand=""
				elif bool:
					bestand = bestand + lijst[i]
		if exists:
			self._visainstrument.write('SOUR%s:FUNC:USER "%s","C:"' % (channel, name))
			# data = self._visainstrument.ask('MMEM:DATA? "%s"' % name)
			# logging.debug(__name__  + ' : File exists on instrument, loading \
			# into local memory')
			# print (data)
			# # string alsvolgt opgebouwd: '#' <lenlen1> <len> 'MAGIC 1000\r\n' '#' <len waveform> 'CLOCK ' <clockvalue>
			# len1=int(data[1])
			# len2=int(data[2:2+len1])
			# i=len1
			# tekst = ""
			# while (tekst!='#'):
				# tekst=data[i]
				# i=i+1
			# len3=int(data[i])
			# len4=int(data[i+1:i+1+len3])

			# w=[]
			# m1=[]
			# m2=[]

			# for q in range(i+1+len3, i+1+len3+len4,5):
				# j=int(q)
				# c,d = struct.unpack('<fB', str.encode(data[j:5+j]))
				# w.append(c.decode())
				# m2.append(int(d/2))
				# m1.append(d-2*int(d/2))

			# clock = float(data[i+1+len3+len4+5:len(data)])

			# self._values['files'][name]={}
			# self._values['files'][name]['w']=w
			# self._values['files'][name]['m1']=m1
			# self._values['files'][name]['m2']=m2
			# self._values['files'][name]['clock']=clock
			# self._values['files'][name]['nop']=len(w)

			# self._values['recent_channel_%s' % channel] = self._values['files'][name]
			# self._values['recent_channel_%s' % channel]['filename'] = name
		else:
			logging.error(__name__  + ' : Invalid filename specified %s' % name)

		# if (self._nop==self._values['files'][name]['nop']):
			# logging.debug(__name__  + ' : Set file %s on channel %s' % (name, channel))
			# self._visainstrument.write('SOUR%s:FUNC:USER "%s","MAIN"' % (channel, name))
		# else:
			# logging.warning(__name__  + ' : Verkeerde lengte %s ipv %s'
				# % (self._values['files'][name]['nop'], self._nop))

	def do_get_amplitude(self, channel):
		'''
		Reads the amplitude of the designated channel from the instrument

		Input:
			channel (int) : 1 or 2, the number of the designated channel

		Output:
			amplitude (float) : the amplitude of the signal in Volts
		'''
		logging.debug(__name__ + ' : Get amplitude of channel %s from instrument'
			% channel)
		return float(self._visainstrument.ask('SOUR%s:VOLT:LEV:IMM:AMPL?' % channel))

	def do_set_amplitude(self, amp, channel):
		'''
		Sets the amplitude of the designated channel of the instrument

		Input:
			amp (float)   : amplitude in Volts
			channel (int) : 1 or 2, the number of the designated channel

		Output:
			None
		'''
		logging.debug(__name__ + ' : Set amplitude of channel %s to %.6f'
			% (channel, amp))
		self._visainstrument.write('SOUR%s:VOLT:LEV:IMM:AMPL %.6f' % (channel, amp))

	def do_get_offset(self, channel):
		'''
		Reads the offset of the designated channel of the instrument

		Input:
			channel (int) : 1 or 2, the number of the designated channel

		Output:
			offset (float) : offset of designated channel in Volts
		'''
		logging.debug(__name__ + ' : Get offset of channel %s' % channel)
		return float(self._visainstrument.ask('SOUR%s:VOLT:LEV:IMM:OFFS?' % channel))

	def do_set_offset(self, offset, channel):
		'''
		Sets the offset of the designated channel of the instrument

		Input:
			offset (float) : offset in Volts
			channel (int)  : 1 or 2, the number of the designated channel

		Output:
			None
		'''
		logging.debug(__name__ + ' : Set offset of channel %s to %.6f' % (channel, offset))
		self._visainstrument.write('SOUR%s:VOLT:LEV:IMM:OFFS %.6f' % (channel, offset))

	def do_get_marker1_low(self, channel):
		'''
		Gets the low level for marker1 on the designated channel.

		Input:
			channel (int) : 1 or 2, the number of the designated channel

		Output:
			low (float) : low level in Volts
		'''
		logging.debug(__name__ + ' : Get lower bound of marker1 of channel %s' % channel)
		return float(self._visainstrument.ask('SOUR%s:MARK1:VOLT:LEV:IMM:LOW?' % channel))

	def do_set_marker1_low(self, low, channel):
		'''
		Sets the low level for marker1 on the designated channel.

		Input:
			low (float)   : low level in Volts
			channel (int) : 1 or 2, the number of the designated channel

		Output:
			None
		 '''
		logging.debug(__name__ + ' : Set lower bound of marker1 of channel %s to %.3f'
			% (channel, low))
		self._visainstrument.write('SOUR%s:MARK1:VOLT:LEV:IMM:LOW %.3f' % (channel, low))

	def do_get_marker1_high(self, channel):
		'''
		Gets the high level for marker1 on the designated channel.

		Input:
			channel (int) : 1 or 2, the number of the designated channel

		Output:
			high (float) : high level in Volts
		'''
		logging.debug(__name__ + ' : Get upper bound of marker1 of channel %s' % channel)
		return float(self._visainstrument.ask('SOUR%s:MARK1:VOLT:LEV:IMM:HIGH?' % channel))

	def do_set_marker1_high(self, high, channel):
		'''
		Sets the high level for marker1 on the designated channel.

		Input:
			high (float)   : high level in Volts
			channel (int) : 1 or 2, the number of the designated channel

		Output:
			None
		 '''
		logging.debug(__name__ + ' : Set upper bound of marker1 of channel %s to %.3f'
			% (channel, high))
		self._visainstrument.write('SOUR%s:MARK1:VOLT:LEV:IMM:HIGH %.3f' % (channel, high))

	def do_get_marker2_low(self, channel):
		'''
		Gets the low level for marker2 on the designated channel.

		Input:
			channel (int) : 1 or 2, the number of the designated channel

		Output:
			low (float) : low level in Volts
		'''
		logging.debug(__name__ + ' : Get lower bound of marker2 of channel %s' % channel)
		return float(self._visainstrument.ask('SOUR%s:MARK2:VOLT:LEV:IMM:LOW?' % channel))

	def do_set_marker2_low(self, low, channel):
		'''
		Sets the low level for marker2 on the designated channel.

		Input:
			low (float)   : low level in Volts
			channel (int) : 1 or 2, the number of the designated channel

		Output:
			None
		 '''
		logging.debug(__name__ + ' : Set lower bound of marker2 of channel %s to %.3f'
			% (channel, low))
		self._visainstrument.write('SOUR%s:MARK2:VOLT:LEV:IMM:LOW %.3f' % (channel, low))

	def do_get_marker2_high(self, channel):
		'''
		Gets the high level for marker2 on the designated channel.

		Input:
			channel (int) : 1 or 2, the number of the designated channel

		Output:
			high (float) : high level in Volts
		'''
		logging.debug(__name__ + ' : Get upper bound of marker2 of channel %s' % channel)
		return float(self._visainstrument.ask('SOUR%s:MARK2:VOLT:LEV:IMM:HIGH?' % channel))

	def do_set_marker2_high(self, high, channel):
		'''
		Sets the high level for marker2 on the designated channel.

		Input:
			high (float)   : high level in Volts
			channel (int) : 1 or 2, the number of the designated channel

		Output:
			None
		 '''
		logging.debug(__name__ + ' : Set upper bound of marker2 of channel %s to %.3f'
			% (channel, high))
		self._visainstrument.write('SOUR%s:MARK2:VOLT:LEV:IMM:HIGH %.3f' % (channel, high))

	def do_get_status(self, channel):
		'''
		Gets the status of the designated channel.

		Input:
			channel (int) : 1 or 2, the number of the designated channel

		Output:
			None
		'''
		logging.debug(__name__ + ' : Get status of channel %s' % channel)
		outp = self._visainstrument.ask('OUTP%s?' % channel)
		if (outp=='0'):
			return 0
		elif (outp=='1'):
			return 1
		else:
			logging.debug(__name__ + ' : Read invalid status from instrument %s' % outp)
			return 'an error occurred while reading status from instrument'

	def do_set_status(self, status, channel):
		'''
		Sets the status of designated channel.

		Input:
			status (string) : 'On' or 'Off'
			channel (int)   : channel number

		Output:
			None
		'''
		logging.debug(__name__ + ' : Set status of channel %s to %s'
			% (channel, status))
		if (status == 1):
			self._visainstrument.write('OUTP%s ON' % channel)
		elif (status == 0):
			self._visainstrument.write('OUTP%s OFF' % channel)
		else:
			logging.debug(__name__ + ' : Try to set status to invalid value %s' % status)
			print ('Tried to set status to invalid value %s' % status)

	#  Ask for string with filenames
	def get_filenames(self):
		logging.debug(__name__ + ' : Read filenames from instrument')
		return self._visainstrument.ask('MMEM:CAT? "MAIN"')

	# Send waveform to the device
	def send_waveform(self,w,m1,m2,filename,clock):
		'''
		Sends a complete waveform. All parameters need to be specified.
		See also: resend_waveform()

		Input:
			w (float[nop]) : waveform
			m1 (int[nop])  : marker1
			m2 (int[nop])  : marker2
			filename (string)    : filename
			clock (int)          : frequency (Hz)

		Output:
			None
		'''
		logging.debug(__name__ + ' : Sending waveform %s to instrument' % filename)
		# Check for errors
		dim = len(w)

		if (not((len(w)==len(m1)) and ((len(m1)==len(m2))))):
			return 'error'

		self._values['files'][filename]={}
		self._values['files'][filename]['w']=w
		self._values['files'][filename]['m1']=m1
		self._values['files'][filename]['m2']=m2
		self._values['files'][filename]['clock']=clock
		self._values['files'][filename]['nop']=len(w)

		m = m1 + numpy.multiply(m2,2)
		ws = bytes()
		for i in range(0,len(w)):
			ws = ws + struct.pack('<fB', w[i], int(m[i]))

		s1 = str.encode('MMEM:DATA "%s",' % filename)
		s3 = str.encode('MAGIC 1000\n')
		s5 = ws
		s6 = str.encode('CLOCK %.10e' % clock)
		s4 = str.encode('#' + str(len(str(len(s5)))) + str(len(s5)))

		lenlen=str(len(str(len(s6) + len(s5) + len(s4) + len(s3))))
		s2 = str.encode('#' + lenlen + str(len(s6) + len(s5) + len(s4) + len(s3)))

		mes = s1 + s2 + s3 + s4 + s5 + s6

		self._visainstrument.write_raw(mes+b"\n")

	def resend_waveform(self, channel, w=[], m1=[], m2=[], clock=[]):
		'''
		Resends the last sent waveform for the designated channel
		Overwrites only the parameters specified

		Input: (mandatory)
			channel (int) : 1, 2, 3 or 4, the number of the designated channel

		Input: (optional)
			w (float[nop]) : waveform
			m1 (int[nop])  : marker1
			m2 (int[nop])  : marker2
			clock (int) : frequency

		Output:
			None
		'''
		filename = self._values['recent_channel_%s' % channel]['filename']
		logging.debug(__name__ + ' : Resending %s to channel %s' % (filename, channel))


		if (w==[]):
			w = self._values['recent_channel_%s' % channel]['w']
		if (m1==[]):
			m1 = self._values['recent_channel_%s' % channel]['m1']
		if (m2==[]):
			m2 = self._values['recent_channel_%s' % channel]['m2']
		if (clock==[]):
			clock = self._values['recent_channel_%s' % channel]['clock']

		if not ( (len(w) == self._nop) and (len(m1) == self._nop) and (len(m2) == self._nop)):
			logging.error(__name__ + ' : one (or more) lengths of waveforms do not match with nop')

		self.send_waveform(w,m1,m2,filename,clock)
		self.do_set_filename(filename, channel)

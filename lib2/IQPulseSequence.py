from copy import deepcopy
from numpy import *
from matplotlib import pyplot as plt
from scipy.signal import *


class PulseSequence():
    def __init__(self, waveform = ndarray(1), pulses = []):
        self._waveform = waveform
        self._pulses = pulses

    def append_pulse(self, points):
        if len(points)>1:
            self._waveform = concatenate((self._waveform[:-1], points))
        else:
            # We ingore pulses of zero length
            return

    def __add__(self, other):
        copy = deepcopy(self)
        copy._waveform = concatenate((copy._waveform[:-1],other._waveform))
        return copy

    def total_points(self):
        return len(self._waveform)

    def get_waveform(self):
        return self._waveform

    def plot(self, sequence_duration, **kwargs):
        times = linspace(0, sequence_duration, len(self._waveform))
        plt.plot(times, self._waveform*5, **kwargs)


class IQPulseSequence():
    """
    Class whose instances can be loaded directly to the AWG via AWG's ouptut_iq_pulse_sequence() method
    """
    def __init__(self, pulse_sequence_I, pulse_sequence_Q, sequence_duration):
        self._i = pulse_sequence_I
        self._q = pulse_sequence_Q
        self._duration = sequence_duration

    def __add__(self, other):
        I, Q = other.get_IQ_sequences()
        return IQPulseSequence(self._i+I, self._q+Q,
            self._duration+other.get_duration())

    def get_IQ_sequences(self):
        return self._i, self._q

    def get_I_waveform(self):
        return self._i.get_waveform()

    def get_Q_waveform(self):
        return self._q.get_waveform()

    def get_duration(self):
        return self._duration

    def plot(self, **kwargs):
        self._i.plot(self._duration, label="I", **kwargs)
        self._q.plot(self._duration, label="Q", **kwargs)
        plt.legend()


class PulseBuilder():

    def __init__(self, iqmx_calibration):
        '''
        Build a PulseBuilder instance for a previously calibrated IQ mixer.

        Parameters:
        -----------
        iqmx_calibration: IQCalibrationData
            Calibration data for the IQ mixer that will be used to send out the pulse sequence.
            Make sure that the radiation parameters of this calibration are in match with your actual settings
        '''

        self._iqmx_calibration = iqmx_calibration
        self._waveform_resolution = \
            iqmx_calibration.get_radiation_parameters()["waveform_resolution"]
        self._pulse_seq_I = PulseSequence()
        self._pulse_seq_Q = PulseSequence()

    def add_dc_pulse(self, duration, dc_voltage=None):
        '''
        Adds a pulse by putting a dc voltage at the I and Q inputs of the mixer

        Parameters:
        -----------
        duration: float, ns
            Duration of the pulse in nanoseconds
        dc_voltage: float, volts
            The value of the dc voltage applied at the IQ mixer ports during the
            pulse. If not specified, calibration data will be used
        '''
        vdc1, vdc2 = self._iqmx_calibration\
                .get_optimization_results()[0]["dc_offsets_open"] \
                            if dc_voltage is None else (dc_voltage, dc_voltage)
        N_time_steps = int(round(duration/self._waveform_resolution))
        self._pulse_seq_I.append_pulse(zeros(N_time_steps+1)+vdc1/5)
        self._pulse_seq_Q.append_pulse(zeros(N_time_steps+1)+vdc2/5)
        return self

    def add_zero_pulse(self, duration):
        '''
        Adds a pulse with zero amplitude to the sequence

        Parameters:
        -----------
        duration: float, ns
            Duration of the pulse in nanoseconds
        '''
        vdc1, vdc2 = self._iqmx_calibration\
                .get_optimization_results()[0]["dc_offsets"]
        N_time_steps = int(round(duration/self._waveform_resolution))
        self._pulse_seq_I.append_pulse(zeros(N_time_steps+1)+vdc1/5)
        self._pulse_seq_Q.append_pulse(zeros(N_time_steps+1)+vdc2/5)
        return self

    # def modulate_rectangle(self, amplitude):
    #     pulse_length = len(self._pulse_seq_I.get_pulse(-1))
    #     modulation = amplitude*ones(pulse_length)
    #     self._pulse_seq_I.modulate_pulse(-1, modulation)
    #     self._pulse_seq_Q.modulate_pulse(-1, modulation)
    #     return self
    #
    # def modulate_chebwin(self, lobe_attenuation=70):
    #     pulse_length = len(self._pulse_seq_I.get_pulse(-1))
    #     modulation = chebwin(pulse_length, lobe_attenuation)
    #     self._pulse_seq_I.modulate_pulse(-1, modulation)
    #     self._pulse_seq_Q.modulate_pulse(-1, modulation)
    #     return self
    #
    # def modulate_hamming(self, amplitude=1):
    #     pulse_length = len(self._pulse_seq_I.get_pulse(-1))
    #     X = array(range(0, pulse_length))
    #     modulation = amplitude*.5*(1-cos(2*pi*X/(pulse_length-1)))
    #     self._pulse_seq_I.modulate_pulse(-1, modulation)
    #     self._pulse_seq_Q.modulate_pulse(-1, modulation)
    #     return self
    #
    # def modulate_gauss(self, amplitude, sigma):
    #     pulse_length = len(self._pulse_seq_I.get_pulse(-1))
    #     X = linspace(-pulse_length/2*self._waveform_resolution, pulse_length/2*self._waveform_resolution, pulse_length)
    #     modulation = amplitude*exp(-X**2/sigma**2)
    #     self._pulse_seq_I.modulate_pulse(-1, modulation)
    #     self._pulse_seq_Q.modulate_pulse(-1, modulation)
    #     return self

    def add_sine_pulse(self, duration, phase = 0, time_offset = 0):
        """
        Adds a pulse with amplitude defined by the iqmx_calibration at frequency
        f_lo-f_if and some phase to the sequence

        Parameters:
        -----------
        duration: float, ns
            Duration of the pulse in nanoseconds
        phase: float, rad
            Adds a relative phase to the outputted signal
        time_offset: float, rad
            Adds relative phase of omega_if*time_offset which will be rounded
            correctly with regard to the used waveform resolution. Use it when you
            need to imitate a continuous sine wave sliced with windows
        """
        if_offs1, if_offs2 =\
             self._iqmx_calibration.get_optimization_results()[0]["if_offsets"]
        if_amp1, if_amp2 =\
             self._iqmx_calibration.get_optimization_results()[0]["if_amplitudes"]
        if_phase =\
             self._iqmx_calibration.get_optimization_results()[0]["if_phase"]
        frequency =\
            self._iqmx_calibration.get_radiation_parameters()["if_frequency"]
        N_time_steps = round(duration/self._waveform_resolution)
        duration = N_time_steps*self._waveform_resolution
        rounded_time_offset =\
         round(time_offset/self._waveform_resolution)*self._waveform_resolution
        phase = phase + 2*pi*frequency/1e9*rounded_time_offset

        self._pulse_seq_I.append_pulse(if_amp1/5*sin(2*pi*frequency/1e9*\
                linspace(0, duration, N_time_steps+1)+if_phase+phase) + if_offs1/5)

        self._pulse_seq_Q.append_pulse(if_amp2/5*sin(2*pi*frequency/1e9*\
                linspace(0,duration, N_time_steps+1)+phase) + if_offs2/5)
        return self

    def add_zero_until(self, total_duration):
        '''
        Adds a pulse with zero amplitude to the sequence of such length that the
        whole pulse sequence is of specified duration

        Should be used to end the sequence as the last call before build(...)

        Parameters:
        -----------
        total_duration: float, ns
            Duration of the whole sequence
        '''
        total_time_steps = round(total_duration/self._waveform_resolution)
        current_time_steps = self._pulse_seq_I.total_points()-1
        residual_time_steps = total_time_steps-current_time_steps
        self.add_zero_pulse(residual_time_steps*self._waveform_resolution)
        return self

    def build(self):
        '''
        Returns the IQ sequence containing I and Q pulse sequences and the total
        duration of the pulse sequence in ns
        '''
        to_return = IQPulseSequence(self._pulse_seq_I, self._pulse_seq_Q,
                self._waveform_resolution*(self._pulse_seq_I.total_points()-1))
        self._pulse_seq_I = PulseSequence()
        self._pulse_seq_Q = PulseSequence()
        return to_return

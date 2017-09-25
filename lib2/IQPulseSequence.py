from copy import deepcopy
from numpy import *
from matplotlib import pyplot as plt
from scipy.signal import *


class PulseSequence():
    def __init__(self):
        self._waveform = ndarray(1)
        self._pulses = []

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
        plt.plot(times, self._waveform, **kwargs)


class IQPulseSequence():
    """
    Class whose instances can be loaded directly to the AWG via AWG's
    ouptut_iq_pulse_sequence() method
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
        self._pulse_seq_I.append_pulse(zeros(N_time_steps+1)+vdc1)
        self._pulse_seq_Q.append_pulse(zeros(N_time_steps+1)+vdc2)
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
        self._pulse_seq_I.append_pulse(zeros(N_time_steps+1)+vdc1)
        self._pulse_seq_Q.append_pulse(zeros(N_time_steps+1)+vdc2)
        return self


    def add_sine_pulse(self, duration, phase = 0, amplitude = 1,
        window = "rectangular", hd_amplitude = 0):
        """
        Adds a pulse with amplitude defined by the iqmx_calibration at frequency
        f_lo-f_if and some phase to the sequence. All sine pulses will be parts
        of the same continuous wave at frequency of f_if

        Parameters:
        -----------
        duration: float, ns
            Duration of the pulse in nanoseconds. For pulses other than rectangular
            will be interpreted as t_g (see F. Motzoi et al. PRL (2009))
        phase: float, rad
            Adds a relative phase to the outputted signal.
        amplitude: float
            Calibration if_amplitudes will be scaled by the
            amplitude_value.
        window: string
            List containing the name and the description of the modulating
            window of the pulse.
            Implemented modulations:
            "rectangular"
                Rectangular window.
            "gaussian"
                Gaussian window, see F. Motzoi et al. PRL (2009).
            "hahn"
                Hahn sin^2 window
        hd_amplitude: float
            correction for the Half Derivative method, theoretically should be 1
        """
        if_offs1, if_offs2 =\
             self._iqmx_calibration.get_optimization_results()[0]["if_offsets"]

        if_amp1, if_amp2 =\
             self._iqmx_calibration.get_optimization_results()[0]["if_amplitudes"]
        if_amp1, if_amp2 =\
            if_amp1*amplitude, if_amp2*amplitude

        if_phase =\
             self._iqmx_calibration.get_optimization_results()[0]["if_phase"]
        frequency =\
            2*pi*self._iqmx_calibration.get_radiation_parameters()["if_frequency"]/1e9

        N_time_steps = round(duration/self._waveform_resolution)
        duration = N_time_steps*self._waveform_resolution

        phase+=(self._pulse_seq_I.total_points()-1)*\
                self._waveform_resolution*frequency

        points = linspace(0, duration, N_time_steps+1)
        carrier_I = if_amp1*exp(1j*(frequency*points+if_phase+phase))
        carrier_Q = if_amp2*exp(1j*(frequency*points+phase))
        # print(real(carrier_Q)

        def rectangular():
            return ones_like(points), zeros_like(points)

        def gaussian():
            B = exp(-(duration/2)**2/2/(duration/3)**2)
            window = (exp(-(points-duration/2)**2/2/(duration/3)**2) - B)/(1-B)
            derivative = gradient(window, self._waveform_resolution)
            return window, derivative

        def hahn():
            window = sin(pi*linspace(0, N_time_steps, N_time_steps+1)/N_time_steps)**2
            derivative = gradient(window, self._waveform_resolution)
            derivative[0] = derivative[-1] = 0
            return window, derivative

        windows = {"rectangular":rectangular, "gaussian":gaussian, "hahn":hahn}
        window, derivative = windows[window]()

        hd_corretion = - derivative*hd_amplitude/2/(-2*pi*0.2) #anharmonicity
        carrier_I = window*real(carrier_I)+hd_corretion*imag(carrier_I)
        carrier_Q = window*real(carrier_Q)+hd_corretion*imag(carrier_Q)

        self._pulse_seq_I.append_pulse(carrier_I + if_offs1)
        self._pulse_seq_Q.append_pulse(carrier_Q + if_offs2)
        return self

    def add_sine_pulse_from_string(self, pulse_string, pulse_duration,
                                        pulse_amplitude, window='gaussian'):
        '''
        pulse_duration is pi_pulse_duraton for rectangular window
        and is arbitrary for gaussian window.

        pulse_amplitude is pi_pulse_amplitude for gaussian window and
        is arbitrary for rectangular window.
        '''
        global_phase = 0
        pulse_ax = pulse_string[1]
        pulse_angle = eval(pulse_string.replace(pulse_ax,"1"))  # in pi's
        if window == "rectangular":
            pulse_time = pulse_duration*abs(pulse_angle)
        else:
            pulse_time = pulse_duration
            pulse_amplitude = pulse_angle*pulse_amplitude
        pulse_phase = pi/2*(1-sign(pulse_angle))+global_phase
        if pulse_ax == "I":
            self.add_zero_pulse(pulse_time)
        elif pulse_ax == "X":
            self.add_sine_pulse(duration=pulse_time, phase=pulse_phase,
                                amplitude=pulse_amplitude,
                                window=window)
        elif pulse_ax == "Y":
            self.add_sine_pulse(duration=pulse_time, phase=pulse_phase+pi/2,
                                amplitude=pulse_amplitude,
                                window=window)
        elif pulse_ax == "Z":
            global_phase += pi*pulse_angle
            pulse_time = 0
        else:
            raise ValueError("Axis of %s is not allowed. Check your sequence."%(pulse_str))
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


    @staticmethod
    def build_dispersive_rabi_sequences(exc_pb, ro_pb, pulse_sequence_parameters):
        '''
        Returns synchronized excitation and readout IQPulseSequences assuming that
        readout AWG is triggered by the excitation AWG
        '''
        awg_trigger_reaction_delay = \
                pulse_sequence_parameters["awg_trigger_reaction_delay"]
        readout_duration = \
                pulse_sequence_parameters["readout_duration"]
        repetition_period = \
                pulse_sequence_parameters["repetition_period"]
        excitation_duration = \
                pulse_sequence_parameters["excitation_duration"]
        window = \
                pulse_sequence_parameters["modulating_window"]
        amplitude = \
                pulse_sequence_parameters["excitation_amplitude"]

        exc_pb.add_zero_pulse(awg_trigger_reaction_delay)\
            .add_sine_pulse(excitation_duration, 0, amplitude=amplitude,
                                                                window=window)\
            .add_zero_pulse(readout_duration)\
            .add_zero_until(repetition_period)

        ro_pb.add_zero_pulse(excitation_duration+10)\
             .add_dc_pulse(readout_duration)\
             .add_zero_until(repetition_period)

        return exc_pb.build(), ro_pb.build()

    @staticmethod
    def build_dispersive_ramsey_sequences(exc_pb, ro_pb,
        pulse_sequence_parameters):

        awg_trigger_reaction_delay = \
                pulse_sequence_parameters["awg_trigger_reaction_delay"]
        readout_duration = \
                pulse_sequence_parameters["readout_duration"]
        repetition_period = \
                pulse_sequence_parameters["repetition_period"]
        half_pi_pulse_duration = \
                pulse_sequence_parameters["half_pi_pulse_duration"]
        ramsey_delay = \
                pulse_sequence_parameters["ramsey_delay"]
        window =\
                pulse_sequence_parameters["modulating_window"]
        amplitude =\
                pulse_sequence_parameters["excitation_amplitude"]

        exc_pb.add_zero_pulse(awg_trigger_reaction_delay)\
            .add_sine_pulse(half_pi_pulse_duration,
                        amplitude=amplitude, window=window)\
            .add_zero_pulse(ramsey_delay)\
            .add_sine_pulse(half_pi_pulse_duration,
                        amplitude=amplitude, window=window)\
            .add_zero_pulse(readout_duration)\
            .add_zero_until(repetition_period)

        ro_pb.add_zero_pulse(2*half_pi_pulse_duration+ramsey_delay+10)\
             .add_dc_pulse(readout_duration)\
             .add_zero_until(repetition_period)

        return exc_pb.build(), ro_pb.build()

    @staticmethod
    def build_dispersive_decay_sequences(exc_pb, ro_pb,
        pulse_sequence_parameters):
        awg_trigger_reaction_delay = \
                pulse_sequence_parameters["awg_trigger_reaction_delay"]
        readout_duration = \
                pulse_sequence_parameters["readout_duration"]
        repetition_period = \
                pulse_sequence_parameters["repetition_period"]
        pi_pulse_duration = \
                pulse_sequence_parameters["pi_pulse_duration"]
        readout_delay = \
                pulse_sequence_parameters["readout_delay"]

        exc_pb.add_zero_pulse(awg_trigger_reaction_delay)\
            .add_sine_pulse(pi_pulse_duration, 0)\
            .add_zero_pulse(readout_delay+readout_duration)\
            .add_zero_until(repetition_period)

        ro_pb.add_zero_pulse(pi_pulse_duration+readout_delay)\
             .add_dc_pulse(readout_duration)\
             .add_zero_until(repetition_period)

        return exc_pb.build(), ro_pb.build()

    @staticmethod
    def build_dispersive_hahn_echo_sequences(exc_pb, ro_pb,
        pulse_sequence_parameters):

        awg_trigger_reaction_delay = \
                pulse_sequence_parameters["awg_trigger_reaction_delay"]
        readout_duration = \
                pulse_sequence_parameters["readout_duration"]
        repetition_period = \
                pulse_sequence_parameters["repetition_period"]
        half_pi_pulse_duration = \
                pulse_sequence_parameters["half_pi_pulse_duration"]
        echo_delay = \
                pulse_sequence_parameters["echo_delay"]

        exc_pb.add_zero_pulse(awg_trigger_reaction_delay)\
                .add_sine_pulse(half_pi_pulse_duration, 0)\
                .add_zero_pulse(echo_delay/2)\
                .add_sine_pulse(2*half_pi_pulse_duration)\
                .add_zero_pulse(echo_delay/2)\
                .add_sine_pulse(half_pi_pulse_duration)\
                .add_zero_pulse(readout_duration)\
                .add_zero_until(repetition_period)

        ro_pb.add_zero_pulse(4*half_pi_pulse_duration+echo_delay+10)\
             .add_dc_pulse(readout_duration)\
             .add_zero_until(repetition_period)

        return exc_pb.build(), ro_pb.build()

    @staticmethod
    def build_radial_tomography_pulse_sequences(exc_pb, ro_pb,
                    pulse_sequence_parameters):
        awg_trigger_reaction_delay = \
                pulse_sequence_parameters["awg_trigger_reaction_delay"]
        readout_duration = \
                pulse_sequence_parameters["readout_duration"]
        repetition_period = \
                pulse_sequence_parameters["repetition_period"]
        tomo_phase = \
                pulse_sequence_parameters["tomo_phase"]
        prep_pulse = \
                pulse_sequence_parameters["prep_pulse"]   # list with strings of pulses, i.e. '+X/2'
        prep_pulse_pi_amplitude = \
                pulse_sequence_parameters["prep_pulse_pi_amplitude"]
        tomo_delay = \
                pulse_sequence_parameters["tomo_delay"]
        padding = \
                pulse_sequence_parameters["padding"]
        pulse_length = \
                pulse_sequence_parameters["pulse_length"]
        tomo_pulse_amplitude =\
                pulse_sequence_parameters["tomo_pulse_amplitude"]
        window =\
                pulse_sequence_parameters["modulating_window"]
        try:
            hd_amplitude = \
                    pulse_sequence_parameters["hd_amplitude"]
        except KeyError:
            hd_amplitude = 0

        prep_total_duration = 0
        exc_pb.add_zero_pulse(awg_trigger_reaction_delay)
        for idx, pulse_str in enumerate(prep_pulse):
            exc_pb.add_sine_pulse_from_string(pulse_str,pulse_length,prep_pulse_pi_amplitude,
                                            window=window)
            exc_pb.add_zero_pulse(padding)
            prep_total_duration += pulse_length + padding

        exc_pb.add_zero_pulse(tomo_delay)\
            .add_sine_pulse(pulse_length, tomo_phase,
                amplitude=tomo_pulse_amplitude, window=window, hd_amplitude=hd_amplitude)\
            .add_zero_pulse(readout_duration)\
            .add_zero_until(repetition_period)

        ro_pb.add_zero_pulse(prep_total_duration+tomo_delay+pulse_length)\
             .add_dc_pulse(readout_duration)\
             .add_zero_until(repetition_period)

        return exc_pb.build(), ro_pb.build()

    @staticmethod
    def build_dispersive_APE_sequences(exc_pb, ro_pb,
        pulse_sequence_parameters):

        awg_trigger_reaction_delay = \
                pulse_sequence_parameters["awg_trigger_reaction_delay"]
        readout_duration = \
                pulse_sequence_parameters["readout_duration"]
        repetition_period = \
                pulse_sequence_parameters["repetition_period"]
        half_pi_pulse_duration = \
                pulse_sequence_parameters["half_pi_pulse_duration"]
        ramsey_angle = \
                pulse_sequence_parameters["ramsey_angle"]
        pseudo_I_pulses_count = \
                pulse_sequence_parameters["pseudo_I_pulses_count"]
        window =\
                pulse_sequence_parameters["modulating_window"]
        amplitude =\
                pulse_sequence_parameters["excitation_amplitude"]
        padding = \
                pulse_sequence_parameters["padding"]
        max_pseudo_I_pulses_count = \
                pulse_sequence_parameters["max_pseudo_I_pulses_count"]
        try:
            hd_amplitude = \
                pulse_sequence_parameters["hd_amplitude"]
        except KeyError:
            hd_amplitude = 0

        exc_pb.add_zero_pulse(awg_trigger_reaction_delay)\
            .add_sine_pulse(half_pi_pulse_duration, 0,
                amplitude=amplitude, window=window, hd_amplitude=hd_amplitude)\
            .add_zero_pulse(padding)

        for i in range(pseudo_I_pulses_count):
            exc_pb.add_sine_pulse(half_pi_pulse_duration, 0,
                amplitude=amplitude, window=window, hd_amplitude=hd_amplitude)\
                  .add_zero_pulse(padding)\
                  .add_sine_pulse(half_pi_pulse_duration, pi,
                amplitude=amplitude, window=window, hd_amplitude=hd_amplitude)\
                  .add_zero_pulse(padding)

        for i in range(max_pseudo_I_pulses_count-pseudo_I_pulses_count):
            exc_pb.add_zero_pulse(2*(half_pi_pulse_duration+padding))

        exc_pb.add_sine_pulse(half_pi_pulse_duration, ramsey_angle,
                amplitude=amplitude, window=window, hd_amplitude=hd_amplitude)\
            .add_zero_pulse(readout_duration)\
            .add_zero_until(repetition_period)

        ro_pb.add_zero_pulse(2*half_pi_pulse_duration+padding+\
              max_pseudo_I_pulses_count*2*(padding+half_pi_pulse_duration))\
             .add_zero_pulse(padding).add_dc_pulse(readout_duration)\
             .add_zero_until(repetition_period)

        return exc_pb.build(), ro_pb.build()

    @staticmethod
    def build_dispersive_pi_half_calibration_sequences(exc_pb, ro_pb,
        pulse_sequence_parameters):
        awg_trigger_reaction_delay = \
                pulse_sequence_parameters["awg_trigger_reaction_delay"]
        readout_duration = \
                pulse_sequence_parameters["readout_duration"]
        repetition_period = \
                pulse_sequence_parameters["repetition_period"]
        half_pi_pulse_duration = \
                pulse_sequence_parameters["half_pi_pulse_duration"]
        twice_pi_half_pulses_count = \
                pulse_sequence_parameters["twice_pi_half_pulses_count"]
        window =\
                pulse_sequence_parameters["modulating_window"]
        amplitude =\
                pulse_sequence_parameters["excitation_amplitude"]
        padding = \
                pulse_sequence_parameters["padding"]
        try:
            hd_amplitude = \
                pulse_sequence_parameters["hd_amplitude"]
        except KeyError:
            hd_amplitude = 0

        exc_pb.add_zero_pulse(awg_trigger_reaction_delay)\
                .add_sine_pulse(half_pi_pulse_duration, 0, amplitude=amplitude,
                    window=window, hd_amplitude=hd_amplitude).add_zero_pulse(padding)

        for i in range(twice_pi_half_pulses_count):
            exc_pb.add_sine_pulse(half_pi_pulse_duration, 0, amplitude=amplitude,
                            window=window, hd_amplitude=hd_amplitude)\
                  .add_zero_pulse(padding)\
                  .add_sine_pulse(half_pi_pulse_duration, 0, amplitude=amplitude,
                            window=window, hd_amplitude=hd_amplitude)\
                  .add_zero_pulse(padding)

        exc_pb.add_zero_until(repetition_period)

        ro_pb.add_zero_pulse((half_pi_pulse_duration+padding)*(1+2*twice_pi_half_pulses_count))\
                .add_dc_pulse(readout_duration).add_zero_until(repetition_period)

        return exc_pb.build(), ro_pb.build()


    @staticmethod
    def build_interleaved_benchmarking_sequence(exc_pb, ro_pb, \
        pulse_sequence_parameters):
        awg_trigger_reaction_delay = \
                pulse_sequence_parameters["awg_trigger_reaction_delay"]
        window =\
                pulse_sequence_parameters["modulating_window"]
        pulse_duration = \
                    pulse_sequence_parameters["pulse_duration"]
        pulse_amplitude =\
                    pulse_sequence_parameters["excitation_amplitude"]
        readout_duration = \
                pulse_sequence_parameters["readout_duration"]
        repetition_period = \
                pulse_sequence_parameters["repetition_period"]

        padding = \
                pulse_sequence_parameters["padding"]
        benchmarking_sequence = \
                pulse_sequence_parameters["benchmarking_sequence"]

        try:
            hd_amplitude = \
                pulse_sequence_parameters["hd_amplitude"]
        except KeyError:
            hd_amplitude = 0

        exc_pb.add_zero_pulse(awg_trigger_reaction_delay)
        global_phase = 0
        excitation_duration = 0
        for idx, pulse_str in enumerate(benchmarking_sequence):
            exc_pb.add_sine_pulse_from_string(window, pulse_str,
                                        pulse_duration, pulse_amplitude)
            exc_pb.add_zero_pulse(padding)
            excitation_duration += pulse_time+padding
        exc_pb.add_zero_until(repetition_period)
        ro_pb.add_zero_pulse(excitation_duration)\
                    .add_dc_pulse(readout_duration)\
                    .add_zero_until(repetition_period)

        return exc_pb.build(), ro_pb.build()

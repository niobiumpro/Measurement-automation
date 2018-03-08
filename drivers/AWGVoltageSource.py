
class AWGVoltageSource():

    def __init__(self, awg, channel_number):
        self._awg = awg
        self._channel_number = channel_number

    def set_voltage(self, voltage):
        self._voltage = voltage
        self._awg.output_continuous_wave(frequency=0, amplitude=0, phase=0,\
         offset=voltage, waveform_resolution=1,  channel=self._channel_number)

    def get_voltage(self):
        return self._voltage

from scipy import *
from resonator_tools.circuit import notch_port
from matplotlib import pyplot as plt
from scipy.signal import savgol_filter

class ResonatorDetector():

    def __init__(self, frequencies, s_data, plot = True, fast = False):

        self._freqs = frequencies
        self._s_data = s_data
        self._plot = plot
        self._port = notch_port(frequencies, s_data)
        self._s_data_filtered = (savgol_filter(real(self._s_data), 21, 2)\
                                + 1j*savgol_filter(imag(self._s_data), 21, 2))
        self._filtered_port = notch_port(frequencies, self._s_data_filtered)
        self._fast = fast

    def detect(self):

        frequencies, sdata = self._freqs, self._s_data

        for port in [self._filtered_port, self._port]:
            if not self._fast:
                result = self._fit(port)
            else:
                amps = abs(self._s_data_filtered)
                phas = angle(self._s_data_filtered)
                min_idx = argmin(amps)
                result = frequencies[min_idx], min(amps), phas[min_idx]

            if result is not None:
                if self._plot:
                    port.plotall()
                return result


    def _fit(self, port):
        scan_range = self._freqs[-1]-self._freqs[0]

        try:
            port.autofit()
        except:
            return mean(self._freqs), -1, -1
        fit_min_idx = argmin(abs(port.z_data_sim))

        expected_frequency = self._freqs[argmin(abs(self._s_data_filtered))]
        expected_amplitude = min(abs(self._s_data_filtered))

        fit_frequency = self._freqs[fit_min_idx]
        fit_amplitude = min(abs(port.z_data_sim))
        fit_angle = angle(port.z_data_sim)[fit_min_idx]

        if abs(fit_frequency-expected_frequency)<0.1*scan_range and \
            abs(fit_amplitude-expected_amplitude)<5*expected_amplitude:
            return fit_frequency, fit_amplitude, fit_angle

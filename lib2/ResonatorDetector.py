from scipy import *
from resonator_tools.circuit import notch_port
from matplotlib import pyplot as plt
from scipy.signal import savgol_filter

class ResonatorDetector():

    def __init__(self, frequencies, s_data, plot = True):

        self._freqs = frequencies
        self._s_data = s_data
        self._plot = plot
        self._port = notch_port(frequencies, s_data)
        self._s_data_filtered = (savgol_filter(real(self._s_data), 21, 2)\
                                + 1j*savgol_filter(imag(self._s_data), 21, 2))
        self._filtered_port = notch_port(frequencies, self._s_data_filtered)

    def detect(self):

        frequencies, sdata = self._freqs, self._s_data
        scan_range = frequencies[-1]-frequencies[0]

        for port in [self._port, self._filtered_port]:
            result = self._fit(port, frequencies, sdata)
            if result is not None:
                if self._plot:
                    port.plotall()
                return result


    def _fit(self, port, frequencies, sdata):
        scan_range = frequencies[-1]-frequencies[0]

        try:
            port.autofit()
        except:
            return mean(frequencies), -1, -1
        fit_min_idx = argmin(abs(port.z_data_sim))

        estimated_frequency = frequencies[argmin(abs(sdata))]
        estimated_amplitude = min(abs(sdata))

        fit_frequency = frequencies[fit_min_idx]
        fit_amplitude = min(abs(port.z_data_sim))

        if abs(fit_frequency-estimated_frequency)<0.1*scan_range and \
            abs(fit_amplitude-estimated_amplitude)<5*estimated_amplitude:
            return fit_frequency, fit_amplitude, angle(port.z_data_sim)[fit_min_idx]

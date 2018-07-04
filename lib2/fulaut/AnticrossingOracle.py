
from matplotlib import pyplot as plt
from scipy import *
from scipy.signal import *
from scipy.optimize import *
from IPython.display import clear_output
from lib2.fulaut.qubit_spectra import *

class AnticrossingOracle():

    '''
    This class automatically processes anticrossing spectral data for
    different types of qubits and frequency arrangements between the qubits and
    resonators
    '''

    qubit_spectra = {"transmon":transmon_spectrum}

    def __init__(self, qubit_type, sts_result):
        self._qubit_spectrum = AnticrossingOracle.qubit_spectra[qubit_type]
        self._sts_result = sts_result

    def launch(self, plot=False):

        self._extract_data(plot=plot)

        intersections = self._find_resonator_intersections()

        if intersections is None or len(intersections) < 2:
            idx_1 = argmin(self._res_points[:,1])
            idx_2 = argmax(self._res_points[:,1])
            res_freq_1 = self._res_points[idx_1,1]
            res_freq_2 = self._res_points[idx_2,1]
            period = 2*abs(self._res_points[idx_2, 0]-self._res_points[idx_1, 0])
        elif len(intersections) == 2:
            idx_1 = intersections[0]
            idx_2 = intersections[1]
            res_freq_1 = self._freqs[argmin(abs(self._data)[idx_1, :])]
            res_freq_2 = self._freqs[argmin(abs(self._data)[idx_2, :])]
            res_freq_1, res_freq_2 = sorted((res_freq_1, res_freq_2))
            period = self._curs[intersections[1]]-self._curs[intersections[0]]
        elif len(intersections) >= 3:
            idx_1 = (intersections[0]+intersections[1])//2
            idx_2 = (intersections[1]+intersections[2])//2
            res_freq_1 = self._freqs[argmin(abs(self._data)[idx_1, :])]
            res_freq_2 = self._freqs[argmin(abs(self._data)[idx_2, :])]
            res_freq_1, res_freq_2 = sorted((res_freq_1, res_freq_2))
            period = self._curs[intersections[2]]-self._curs[intersections[0]]

        d_range = slice(0.,0.9,0.2)
        res_freq_range = slice(res_freq_1, res_freq_2, (res_freq_2-res_freq_1)/10)
        q_freq_range = slice(6,10, 0.25)
        g_range = slice(0.02, 0.04, 0.01)
        Ns = 3
        args = (self._res_points[:,0], self._res_points[:,1])


        best_fit_loss = 1e10
        fitresult = None
        for sweet_spot_cur in [self._curs[idx_1], self._curs[idx_2]]:
            # We are not sure where the sweet spot is, so let's choose the best
            # fit among two possibilities
            def brute_cost_function(params, curs, res_freqs):
                f_res, g, q_max_freq, d = list(params)
                full_params = [f_res, g, period, sweet_spot_cur, q_max_freq, d]
                return self._cost_function(full_params, curs, res_freqs,
                                                        freqs_fine_number = 100)

            result = brute(brute_cost_function,
                    (res_freq_range, g_range, q_freq_range, d_range), Ns=Ns,
                        args = args, finish=None)

            f_res, g, q_max_freq, d = list(result)
            full_params = [f_res, g, period, sweet_spot_cur, q_max_freq, d]

            result = minimize(self._cost_function, full_params,
                                        args=args, method="Nelder-Mead")

            loss = self._cost_function(result.x, *args)
            if loss<best_fit_loss:
                best_fit_loss = loss
                fitresult = result

        res_freq, g, period, sweet_spot_cur, q_freq, d = fitresult.x

        if plot:
            plt.figure()
            plt.plot(self._res_points[:,0], self._res_points[:,1], '.',
                        label="Data")
            plt.plot([sweet_spot_cur], [mean(self._res_points[:,1])], '+')

            p0 = [mean((res_freq_2, res_freq_2)), 0.03, period,
                                                    sweet_spot_cur, 10, 0.6]
            # plt.plot(self._curs, self._model(self._curs, p0), "o")
            plt.plot(self._res_points[:,0],
                    self._model(self._res_points[:,0], fitresult.x, False),
                                "orange", ls="", marker=".", label="Model")
            plt.legend()
            plt.gcf().set_size_inches(15,5)

        fitresult.x[0] = fitresult.x[0]*1e9
        fitresult.x[4] = fitresult.x[4]*1e9
        return fitresult.x

    def _extract_data(self, plot=False):
        data =  self._sts_result.get_data()
        try:
            curs, freqs, self._data =\
                data["Current [A]"], data["frequency"]/1e9, data["data"]
        except:
            curs, freqs, self._data =\
                data["current"], data["frequency"]/1e9, data["data"]
        data = self._data
        res_freqs = []

        # Taking peaks deeper than half of the distance between the median
        # transmission level and the deepest point
        threshold = abs(data).min()+0.5*(median(abs(data))-abs(data).min())

        res_points = []
        for idx, row in enumerate(data):
            row = abs(row)
            extrema = argrelextrema(row, less, order=10)[0]
            extrema = extrema[row[extrema]<threshold]

            if len(extrema)>0:
                smallest_extremum = extrema[argmin(row[extrema])]
                res_points.append((curs[idx], freqs[smallest_extremum]))

        self._res_points = array(res_points)
        self._freqs = freqs
        self._curs = curs

        if plot:
            plt.figure()
            plt.plot(self._res_points[:,0], self._res_points[:,1], 'C1.',
                        label="Extracted points")
            plt.pcolormesh(curs, freqs, abs(data).T)
            plt.legend()
            plt.gcf().set_size_inches(15,5)

    def _find_resonator_intersections(self):
        max_peaks_detected = 0
        peaks_detected = None
        current_peaks_quality = 0
        data = abs(self._data)

        for cut in data.T:
            threshold_depth = median(cut)-ptp(data)*0.1
            window = 10
            peaks = argrelextrema(cut, less, order = window, mode="clip")[0]
            deep_sharp_peaks = []
            for peak in peaks:
                if peak-window<0:
                    continue
                level = max(cut[peak-window:peak+window])
                if cut[peak]<level-ptp(data)*0.5:
                    deep_sharp_peaks.append(peak)
            if len(deep_sharp_peaks)==0:
                continue
            peaks = array(deep_sharp_peaks)
    #         print(peaks)
            peaks = peaks[cut[peaks]<threshold_depth]
            peaks_quality = 1/mean(cut[peaks])
            if len(peaks)>=max_peaks_detected and peaks_quality>current_peaks_quality:
                max_peaks_detected = len(peaks)
                peaks_detected = peaks
        return peaks_detected

    @staticmethod
    def _transmission(f_q, f_probe, f_r, g):
        κ = 1e-4
        γ = 1e-4
        return abs(1/(κ+1j*(f_r-f_probe)+(g**2)/(γ+1j*(f_q-f_probe))))**2

    def _model(self, curs, params, plot_colours = False, freqs_fine_number=5e3):

        f_r, g = params[:2]
        qubit_params = params[2:]
    #     phis_fine = linspace(phis[0],phis[-1], 1000)
        f_qs = self._qubit_spectrum(curs, *qubit_params)

        span = ptp(self._freqs)
        freqs_fine = linspace(self._freqs[0]-span*0.5,
                                self._freqs[-1]+span*0.5,
                                    freqs_fine_number)

        XX, YY = meshgrid(f_qs, freqs_fine)
        transmissions = self._transmission(XX, YY, f_r, g)

        if plot_colours:
            plt.pcolormesh(curs, freqs_fine, transmissions)
            plt.colorbar()

        res_freqs_model = []
        for row in transmissions.T:
            res_freqs_model.append(freqs_fine[argmax(abs(row))])
        return array(res_freqs_model)

    def _cost_function(self, params, curs, res_freqs, freqs_fine_number = 5e3):
        cost = (abs(self._model(curs, params,
                        freqs_fine_number=freqs_fine_number) - res_freqs))
        clear_output(wait=True)
        print((("{:.3e}, "*len(params))[:-2]).format(*params), "loss:",
                "%.2f"%(sum(cost)/len(curs)*1000), "MHz")
        return sum(cost)

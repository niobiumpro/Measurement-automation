import numpy as np
from copy import deepcopy
from scipy.signal import correlate
from itertools import product

import matplotlib
import matplotlib.pyplot as plt

# pyCharm is not resolving this package due to the fact that only cv2.pyd file
# is present in the Python packges dir
import cv2


class Snapshot:
    # value that is assigned to all self.data entries
    # that are below relative threshold
    # during the call of the self._preproc_data(...)
    MACROPARAM_PREPROC = 0

    def __init__(self, data_ma=None):
        self.x = None
        self.y = None
        self.data = None
        self.dx = None
        self.dy = None
        if isinstance(data_ma, dict):
            self.x = data_ma["Current [A]"]
            self.y = data_ma["Frequency [Hz]"] / 1e9
            self.data = data_ma["data"].T
            self._init_dependent_attributes()

    def _init_dependent_attributes(self):
        self.dx = self.x[1] - self.x[0]
        self.dy = self.y[1] - self.y[0]

    def resize(self, new_pixel_size: tuple, inplace=False):
        """
        @brief: box physical dimensions is not changed. Only number of pixels (data points) is changed
        @params
            new_pixel_size : tuple
                (x_pixels_N, y_pixels_N) - tuple of integers
                                           specifying the amount of pixels
                                           along x and y direction respectively
            inplace : bool
                True - modifies self
                False - return modified copy of self
        """
        if inplace is False:
            tmp = Snapshot()
        else:
            tmp = self

        xlims = (self.x[0], self.x[-1])
        ylims = (self.y[0], self.y[-1])

        # INTER_AREA to downscale
        tmp.data = cv2.resize(np.real(self.data), new_pixel_size, interpolation=cv2.INTER_AREA) + \
                   1j * cv2.resize(np.imag(self.data), new_pixel_size, interpolation=cv2.INTER_AREA)

        tmp.x = np.linspace(*xlims, new_pixel_size[0])
        tmp.y = np.linspace(*ylims, new_pixel_size[1])
        tmp._init_dependent_attributes()  # updates tmp.dx and tmp.dy

        return tmp

    def crop(self, xlims=None, ylims=None, inplace=False):
        """
        @params:
            inplace : bool
                True - modifies self
                False - return modified copy of self
        """
        if (inplace is False):
            tmp = Snapshot()
        else:
            tmp = self

        x_idxs = (self.x > xlims[0]) & (self.x < xlims[1]) if (xlims is not None) else \
            np.full_like(self.x, True, dtype=np.bool)
        y_idxs = (self.y > ylims[0]) & (self.y < ylims[1]) if (ylims is not None) else \
            np.full_like(self.y, True, dtype=np.bool)
        tmp.x = self.x[x_idxs]
        tmp.y = self.y[y_idxs]
        tmp.data = self.data[np.ix_(y_idxs, x_idxs)]
        tmp._init_dependent_attributes()

        return tmp

    def intersection(self, snapshot):
        return ((max(self.x[0], snapshot.x[0]), min(self.x[-1], snapshot.x[-1])),
                (max(self.y[0], snapshot.y[0]), min(self.y[-1], snapshot.y[-1])))

    def match_ylims(self, snapshot, inplace=False):
        """
        @brief: return Snapshot that is contained in 'self' as a mathamtical set
                and results from intersection of the 'self' and 'snapshot' in 'y' direction
        @params:
            inplace : bool
                True - modifies self
                False - return modified copy of self
        """
        common_ylims = self.intersection(snapshot)[1]
        return self.crop(ylims=common_ylims, inplace=inplace)

    def match_resolution(self, snapshot, inplace=False):
        """
        @brief: resizes self in order to provide the same self.dx and self.dy
                that is coinciding with snapshot.dx and snapshot.dy
        @params:
            inplace : bool
                True - modifies self
                False - return modified copy of self
        """

        new_dx = snapshot.dx
        new_dy = snapshot.dy
        new_pixel_size = (int(round((self.x[-1] - self.x[0]) / new_dx + 1)),
                          int(round((self.y[-1] - self.y[0]) / new_dy + 1)))
        return self.resize(new_pixel_size, inplace=inplace)

    def _preproc_data(self, relative_threshold=0.3, inplace=False):
        """
        @params:
            relative_threshold : float from interval (0.0 ; 1.0)
                defines the threshold in the normalized data interval in a relative way
                normalized data interval is (0.0 ; 1.0)
                all the data values below threshold is set to 0.0

            inplace : bool
                True - modifies self
                False - return modified copy of self
        """

        if inplace is False:
            tmp = Snapshot()
        else:
            tmp = self

        tmp.data = self._nullify_threshold(deepcopy(self.data),
                                           self._threshold_rel2abs(relative_threshold))
        tmp.x = self.x
        tmp.y = self.y
        tmp._init_dependent_attributes()

        return tmp

    def _threshold_rel2abs(self, rel_threshold):
        """
        @brief: converts relative threshold to the absolute value of the data
        @params:
                rel_threshold : f float from interval (0.0 ; 1.0)
                    defines the threshold in the normalized data interval in a relative way
                    normalized data interval is (0.0 ; 1.0)
                    all the data values below threshold is set to 0.0
        @return: float
                absolute threshold value in the data range (min(data) ; max(data))
        """
        maximum = np.amax(np.abs(self.data))
        minimum = np.amin(np.abs(self.data))
        return minimum * (1 - rel_threshold) + rel_threshold * maximum

    def _nullify_threshold(self, x, threshold, inplace=False):
        """
        @brief: set all the data entries from x with values
                below 'threshold' to fixed value close to zero
        @params:
            inplace : bool
                True - modifies self
                False - return modified copy of self
        """
        x[x < threshold] = Snapshot.MACROPARAM_PREPROC
        return x

    def _correlate_overX(self, snapshot2find):
        """
        @brief:     return correlation function over the horizontal (axis = 1) variable
                    between the self and snapshot2find
                    returns normalized correlation function and normalization factor array
                    in the denominator.
        @desc:      The algorithm is analogous to the opencv.matchTemplate function
                    except that image that's location is to be found only displaced along
                    the horizontal axis.
                    See more in documentation of 'opencv.matchTemplate(..)' method:
                    https://docs.opencv.org/2.4/doc/tutorials/imgproc/histograms/template_matching/template_matching.html
                    method = CV_TM_CCORR_NORMED - match function implemented in this function
        @params:
                    snapshot2find : class Snapshot
                        represents an image that participates as a second variable in scipy.signal.correlate method
        @return:    (res,res_norm)
                    res : 1D numpy array.
                        len(res) = self.shape[1] + snapshot2find.shape[1] - 1
                        autocorrelation function of the two images across horizontal axis
                    res_norm : 1D numpy array
                        len(res_norm) = len(res)
                        normalization factor in denumenator of the matching function formula.
                        See more via the link provided in @desc section.

        """
        # constructing 2 new snapshots with ylims
        # that are contained in both initial snapshots
        cropped_self = self.match_ylims(snapshot2find)
        cropped_2find = snapshot2find.match_ylims(self)

        # print(snapshot.dx,snapshot.dy)
        # print(snapshot_ymatch.dx,snapshot_ymatch.dy)
        # print(self_matched.data.shape,self_matched.dx,self_matched.dy)
        # transform cropped_self to the same resolution as a cropped_2find
        cropped_2find.match_resolution(self, inplace=True)
        # print(self_matched.data.shape,self_matched.dx,self_matched.dy)

        # plot_snapshot(cropped_self)
        # plot_snapshot(cropped_2find)

        n_y = min(cropped_self.data.shape[0], cropped_2find.data.shape[0])
        n_cross_corr = cropped_self.data.shape[1] + cropped_2find.data.shape[1] - 1  # number of correlation output

        cross_corr_res = np.zeros((n_y, n_cross_corr), dtype=np.complex128)  # cross-correlation
        cross_corr_norm = np.zeros((n_y, n_cross_corr), dtype=np.complex128)  # cross correlation norm

        # print(cropped_self.data.shape)
        # print(cropped_2find.data.shape)
        l = cropped_2find.data.shape[1]
        r = cropped_self.data.shape[1]
        for i, (y1_i, y2_i) in enumerate(zip(cropped_self.data, cropped_2find.data)):  # equals to len(snap2crop)
            # correct phase for each measurement
            y1_i /= np.exp(np.angle(y1_i[0]))
            y2_i /= np.exp(np.angle(y2_i[0]))

            cross_corr_res[i] = correlate(y1_i, y2_i, mode="full")
            for j in range(n_cross_corr):
                # normalization of the correlation norm
                # I will never explain this indexes origin without piece of paper
                cross_corr_norm[i, j] = np.linalg.norm(cropped_self.data[:, max(1 - l + j, 0):min(r, 1 + j)]) * \
                                        np.linalg.norm(cropped_2find.data[:, max(0, l - 1 - j):min(l, l + r - 1 - j)])

        cross_corr_res = cross_corr_res.sum(axis=0)
        cross_corr_norm = cross_corr_norm.sum(axis=0)

        cross_corr_res /= cross_corr_norm

        return cross_corr_res, cross_corr_norm

    def find_shift_overX(self, snapshot):
        res, res_norm = self._correlate_overX(snapshot)
        pixel_shift = np.argmax(res)
        xvar_shift = self.dx * (pixel_shift - (len(snapshot.x) - 1))
        return xvar_shift

    def plot(self):
        fig, axes = plt.subplots(1, 2, figsize=(15, 7), sharey=True, sharex=True)
        ax_amps, ax_phas = axes
        ax_amps.ticklabel_format(axis='x', style='sci', scilimits=(-2, 2))
        ax_amps.set_ylabel("Frequency [GHz]")
        xlabel = "Current, A"
        ax_amps.set_xlabel(xlabel)
        ax_phas.ticklabel_format(axis='x', style='sci', scilimits=(-2, 2))
        ax_phas.set_xlabel(xlabel)
        plt.tight_layout(pad=2, h_pad=-10)
        cax_amps, kw = matplotlib.colorbar.make_axes(ax_amps, aspect=40)
        cax_phas, kw = matplotlib.colorbar.make_axes(ax_phas, aspect=40)
        cax_amps.set_title("$|S_{21}|$", position=(0.5, -0.05))
        cax_phas.set_title("$\\angle S_{21}$\n [deg]",
                           position=(0.5, -0.1))
        ax_amps.grid()
        ax_phas.grid()
        extent = [self.x[0] - self.dx / 2, self.x[-1] + self.dx / 2, \
                  self.y[0] - self.dy / 2, self.y[-1] + self.dy / 2, ]
        amps_map = ax_amps.imshow(abs(self.data), aspect='auto', origin='lower', cmap="RdBu_r", extent=extent)
        cb_amps = plt.colorbar(amps_map, cax=cax_amps)
        phas_map = ax_phas.imshow(np.angle(self.data), aspect='auto', origin='lower', cmap="RdBu_r", extent=extent)
        cb_phas = plt.colorbar(phas_map, cax=cax_phas)

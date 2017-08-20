
from matplotlib import pyplot as plt, colorbar
from lib2.VNATimeResolvedDispersiveMeasurement import *

class VNATimeResolvedDispersiveMeasurement2D(VNATimeResolvedDispersiveMeasurement):

    def __init__(self, name, sample_name, vna_name, ro_awg, q_awg,
        q_lo_name):
        super().__init__(name, sample_name, vna_name,
                ro_awg, q_awg, q_lo_name, plot_update_interval=5)

    def set_fixed_parameters(self, vna_parameters, q_lo_parameters,
        ro_awg_parameters, q_awg_parameters, pulse_sequence_parameters,
        detect_resonator=True):

        vna_parameters["power"] = ro_awg_parameters["calibration"]\
            .get_radiation_parameters()["lo_power"]

        q_lo_parameters["power"] = q_awg_parameters["calibration"]\
            .get_radiation_parameters()["lo_power"]

        if detect_resonator:
            res_freq = self._detect_resonator(vna_parameters)
            vna_parameters["freq_limits"] = (res_freq, res_freq)

        super().set_fixed_parameters(vna_parameters, q_lo_parameters,
            ro_awg_parameters, q_awg_parameters, pulse_sequence_parameters)


class VNATimeResolvedDispersiveMeasurement2DResult(
                VNATimeResolvedDispersiveMeasurementResult):

    def _prepare_figure(self):
        fig, axes, caxes = super()._prepare_figure()
        caxes = []
        for ax in axes:
            caxes.append(colorbar.make_axes(ax)[0])
        return fig, axes, caxes

    def _prepare_data_for_plot(self, data):
        '''
        Should be implemented in child classes
        '''
        pass

    def _annotate_axes(self, axes):
        '''
        Should be implemented in child classes
        '''
        pass

    def _plot(self, axes, caxes):

        data = self.get_data()
        if "data" not in data.keys():
            return

        X, Y, Z_raw = self._prepare_data_for_plot(data)
        extent = [X[0], X[-1], Y[0], Y[-1]]

        for idx, name in enumerate(self._data_formats.keys()):
            caxes[idx].clear()
            ax = axes[idx]
            ax.clear()

            Z = self._data_formats[name][0](Z_raw)
            max_Z = max(Z[Z!=0])
            min_Z = min(Z[Z!=0])
            Z_map = ax.imshow(Z, origin='lower', aspect = 'auto',
                cmap="RdBu_r", vmin=min_Z, vmax=max_Z, extent=extent)
            cb = plt.colorbar(Z_map, cax = caxes[idx])
            cb.set_label(self._data_formats[name][1])
            ax.grid()
            cb.formatter.set_scientific(True)
            cb.formatter.set_powerlimits((0,4))
            cb.update_ticks()

        self._annotate_axes(axes)

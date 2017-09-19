from matplotlib import pyplot as plt, colorbar
from lib2.VNATimeResolvedDispersiveMeasurement2D import *

class DispersiveRadialTomography(VNATimeResolvedDispersiveMeasurement2D):

    def __init__(self, name, sample_name, vna_name, ro_awg, q_awg,
        q_lo_name):
        super().__init__(name, sample_name, vna_name,
                                    ro_awg, q_awg, q_lo_name)
        self._measurement_result =\
                DispersiveRadialTomographyResult(name, sample_name)
        self._sequence_generator = PulseBuilder.build_radial_tomography_pulse_sequences

    def set_fixed_parameters(self, vna_parameters, ro_awg_parameters,
            q_awg_parameters, excitation_frequency, pulse_sequence_parameters, basis):

        q_if_frequency = q_awg_parameters["calibration"]\
                    .get_radiation_parameters()["if_frequency"]

        q_lo_parameters = {"power": q_awg_parameters["calibration"]\
                    .get_radiation_parameters()["lo_power"],
                    "frequency": excitation_frequency+q_if_frequency}

        super().set_fixed_parameters(vna_parameters, q_lo_parameters,
            ro_awg_parameters, q_awg_parameters, pulse_sequence_parameters)
        self._basis = basis

    def set_swept_parameters(self, tomo_phases, tomo_pulse_amplitudes):
        q_if_frequency = self._q_awg.get_calibration() \
            .get_radiation_parameters()["if_frequency"]
        swept_pars = {"tomo_pulse_amplitude":
                            (self._set_exc_ampl_and_call_outp_puls_seq,
                            tomo_pulse_amplitudes),
                      "tomo_phase":
                            (self._set_phase_of_drive, tomo_phases)}
        super().set_swept_parameters(**swept_pars)

    def _set_phase_of_drive(self, tomo_phase):
        self._pulse_sequence_parameters["tomo_phase"] = tomo_phase
        super()._output_pulse_sequence()

    def _set_exc_ampl_and_call_outp_puls_seq(self, tomo_pulse_amplitude):
        self._pulse_sequence_parameters["tomo_pulse_amplitude"] = \
                            tomo_pulse_amplitude

    def _recording_iteration(self):
        data = super()._recording_iteration()
        basis = self._basis
        p_r = (real(data) - real(basis[0]))/(real(basis[1]) - real(basis[0]))
        p_i = (imag(data) - imag(basis[0]))/(imag(basis[1]) - imag(basis[0]))
        return p_r+1j*p_i

class DispersiveRadialTomographyResult(VNATimeResolvedDispersiveMeasurementResult):

    def __init__(self, name, sample_name):
        super().__init__(name, sample_name)
        self._pulse_sequence_parameters = self._context\
                .get_pulse_sequence_parameters()


    def _prepare_figure(self):
        fig, axes = plt.subplots(1,2,subplot_kw=dict(projection='polar'),figsize=(12,7))
        plt.tight_layout(pad=4)
        caxes = []
        for ax in axes:
            caxes.append(colorbar.make_axes(ax,
                    locaion="bottom", orientation="horizontal",
                    pad=0.1,shrink=0.7, aspect=40)[0])
        return fig, axes, caxes

    def _prepare_data_for_plot(self, data):

        r = data[self._parameter_names[0]]
        theta = data[self._parameter_names[1]]
        theta_step = (theta[1]-theta[0])
        theta = concatenate((theta - theta_step/2, [theta[-1]+theta_step/2]))
        r_step = (r[1]-r[0])
        r = concatenate((r, [r[-1]+r_step]))
        r_norm = r/self._pulse_sequence_parameters["prep_pulse_pi_amplitude"]
        return theta,r_norm, data["data"]

    def _annotate_axes(self, axes):
        '''
        Should be implemented in child classes
        '''
        pass

    def _plot(self, axes, caxes):

        data = self.get_data()
        if "data" not in data.keys():
            return

        r, theta, Z_raw = self._prepare_data_for_plot(data)
        r_2d, theta_2d = meshgrid(r, theta)

        for idx, name in enumerate(['real','imag']):
            caxes[idx].clear()
            ax = axes[idx]
            ax.clear()

            Z = self._data_formats[name][0](Z_raw)
            max_Z = max(Z[Z!=0])
            min_Z = min(Z[Z!=0])
            Z_map = ax.pcolormesh(r_2d, theta_2d, Z,
                    cmap="RdBu_r", vmin=min_Z, vmax=max_Z)
            ax.text(radians(ax.get_rlabel_position()+10),\
                            0.13*abs(ax.get_rmax()-ax.get_rmin())+ax.get_rmax(),\
                            r"Tomography"+"\n"+ "pulse [$\pi$ rad]", rotation = 0, ha='left',va='center')

            ax.set_ylabel('Tomography phase [deg]', labelpad=30)
            cb = plt.gcf().colorbar(Z_map, cax = caxes[idx], orientation='horizontal')
            cb.set_label(self._data_formats[name][1])
            ax.grid()
            cb.formatter.set_scientific(False)
            cb.formatter.set_powerlimits((-1,4))
            cb.update_ticks()
        plt.suptitle("Preparation sequence: "+\
                    str(self._pulse_sequence_parameters["prep_pulse"]) )
        #self._annotate_axes(axes)
        #plt.tight_layout()

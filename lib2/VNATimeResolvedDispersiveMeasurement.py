from lib2.Measurement import *
from lib2.MeasurementResult import *
from lib2.IQPulseSequence import *

from scipy.optimize import curve_fit

class VNATimeResolvedDispersiveMeasurementContext(ContextBase):

    def __init__(self):
        super().__init__()
        self._pulse_sequence_parameters = {}

    def get_pulse_sequence_parameters(self):
        return self._pulse_sequence_parameters

    def to_string(self):
        return "Pulse sequence parameters:\n"+\
                str(self._pulse_sequence_parameters)+"\n"+\
                super().to_string()

class VNATimeResolvedDispersiveMeasurement(Measurement):

    def __init__(self, name, sample_name, vna_name, ro_awg, q_awg,
        q_lo_name, line_attenuation_db = 60, plot_update_interval = 1):
        super().__init__(name, sample_name, devs_names=[vna_name, q_lo_name],
                    plot_update_interval=plot_update_interval)

        self._ro_awg = ro_awg
        self._q_awg = q_awg
        self._vna = self._actual_devices[vna_name]
        self._q_lo = self._actual_devices[q_lo_name]
        self._basis = None
        self._ult_calib = False
        self._pulse_sequence_parameters =\
            {"modulating_window":"rectangular", "excitation_amplitude":1}

    def set_fixed_parameters(self, vna_parameters, q_lo_parameters,
        ro_awg_parameters, q_awg_parameters, pulse_sequence_parameters,
        detect_resonator=True):

        self._pulse_sequence_parameters.update(pulse_sequence_parameters)
        self._measurement_result.get_context()\
                .get_pulse_sequence_parameters()\
                .update(pulse_sequence_parameters)

        freq_limits = vna_parameters["freq_limits"]
        if detect_resonator and freq_limits[0]!=freq_limits[1]:
            res_freq = self._detect_resonator(vna_parameters,
                                    ro_awg_parameters["calibration"],
                                    q_awg_parameters["calibration"])
            vna_parameters["freq_limits"] = (res_freq, res_freq)

        super().set_fixed_parameters(vna=vna_parameters, q_lo=q_lo_parameters,
                            ro_awg=ro_awg_parameters, q_awg=q_awg_parameters)

    def set_basis(self, basis):
        self._basis = basis

    def set_ult_calib(self, value=False):
        self._ult_calib = value

    def _recording_iteration(self):
        vna = self._vna
        q_lo = self._q_lo
        vna.avg_clear(); vna.prepare_for_stb();
        vna.sweep_single(); vna.wait_for_stb();
        data = vna.get_sdata();
        if self._ult_calib:
            q_lo.set_output_state("OFF")
            vna.avg_clear(); vna.prepare_for_stb();
            vna.sweep_single(); vna.wait_for_stb();
            bg = vna.get_sdata();
            q_lo.set_output_state("ON")
            mean_data = mean(data)/mean(bg)
        else:
            mean_data = mean(data)
        if self._basis is None:
            return mean_data
        basis = self._basis
        p_r = (real(mean_data) - real(basis[0]))/(real(basis[1]) - real(basis[0]))
        p_i = (imag(mean_data) - imag(basis[0]))/(imag(basis[1]) - imag(basis[0]))
        return p_r+1j*p_i

    def _detect_resonator(self, vna_parameters, ro_calibration, q_calibration):
        self._q_lo.set_output_state("OFF")
        print("Detecting a resonator within provided frequency range of the VNA %s\
                    "%(str(vna_parameters["freq_limits"])))
        self._vna.set_nop(201)
        self._vna.set_freq_limits(*vna_parameters["freq_limits"])
        self._vna.set_power(vna_parameters["power"])
        self._vna.set_bandwidth(vna_parameters["bandwidth"]*10)
        self._vna.set_averages(vna_parameters["averages"])

        rep_period = self._pulse_sequence_parameters["repetition_period"]
        ro_duration = self._pulse_sequence_parameters["readout_duration"]
        ro_pb = PulseBuilder(ro_calibration)
        q_pb = PulseBuilder(q_calibration)
        self._ro_awg.output_pulse_sequence(ro_pb\
                    .add_dc_pulse(ro_duration).add_zero_until(rep_period).build())
        self._q_awg.output_pulse_sequence(q_pb.add_zero_until(rep_period).build())

        res_freq, res_amp, res_phase = super()._detect_resonator()
        print("Detected frequency is %.5f GHz, at %.2f mU and %.2f degrees"%\
                    (res_freq/1e9, res_amp*1e3, res_phase/pi*180))
        self._q_lo.set_output_state("ON")
        return res_freq

    def _output_pulse_sequence(self):
        q_pb = self._q_awg.get_pulse_builder()
        ro_pb = self._ro_awg.get_pulse_builder()
        q_seq, ro_seq = self._sequence_generator(q_pb, ro_pb,
                                        self._pulse_sequence_parameters)
        self._ro_awg.output_pulse_sequence(ro_seq, blocking=False)
        self._q_awg.output_pulse_sequence(q_seq)


class VNATimeResolvedDispersiveMeasurementResult(MeasurementResult):

    def __init__(self, name, sample_name):
        super().__init__(name, sample_name)
        self._context =\
            VNATimeResolvedDispersiveMeasurementContext()
        self._is_finished = False
        self._fit_params = None
        self._fit_errors = None
        self._phase_units = "rad"
        self._data_formats = {
            "abs":(abs, "Transmission amplitude [a.u.]"),
            "real":(real,"Transmission real part [a.u.]"),
            "phase":(self._unwrapped_phase, "Transmission phase [%s]"%self._phase_units),
            "imag":(imag, "Transmission imaginary part [a.u.]")}

    def _generate_fit_arguments(self):
        '''
        Should be implemented in child classes.

        Returns:
        p0: array
            Initial parameters
        scale: tuple
            characteristic scale of the parameters
        bounds: tuple of 2 arrays
            See scipy.optimize.least_squares(...) documentation
        '''
        pass

    def _model(self, *params):
        '''
        Fit theoretical function. Should be implemented in child classes
        '''
        return None
    
    def _unwrapped_phase(self, sdata):
        try:
            unwrapped_phase = unwrap(angle(sdata))
            unwrapped_phase[sdata==0] = 0
            return unwrapped_phase
        except:
            return angle(sdata)

    def _prepare_figure(self):
        fig, axes = plt.subplots(2, 2, figsize=(15,7), sharex=True)
        axes = ravel(axes)
        return fig, axes, (None, None)

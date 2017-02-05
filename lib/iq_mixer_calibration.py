
from numpy import *
from scipy.optimize import minimize
from datetime import datetime


class IQCalibrationData():

    def __init__(self, mixer_id, iq_attenuation, lo_frequency, lo_power, if_frequency, ssb_power, waveform_resolution, dc_offsets, 
                        if_offsets, if_amplitudes, if_phase, spectral_values, optimization_time, end_date):
        self._mixer_id = mixer_id
        self._iq_attenuation = iq_attenuation
        self._lo_frequency = lo_frequency
        self._if_frequency = if_frequency
        self._lo_power = lo_power
        self._ssb_power = ssb_power
        self._waveform_resolution = waveform_resolution

        self._dc_offsets = dc_offsets
        self._if_offsets = if_offsets
        self._if_amplitudes = if_amplitudes
        self._if_phase = if_phase

        self._spectral_values = spectral_values
        self._optimization_time = optimization_time
        self._end_date = end_date
    
    def get_optimization_results(self):
        '''
        Get the optimal paramters and the resulting spectral component values

        Returns:
            parameters, results: tuple
        '''
        return dict(dc_offsets=self._dc_offsets, if_offsets=self._if_offsets,
            if_amplitudes=self._if_amplitudes, if_phase=self._if_phase), self._spectral_values

    def get_radiation_parameters(self):
        return dict(lo_frequency=self._lo_frequency, lo_power=self._lo_power,
            if_frequency=self._if_frequency, ssb_power=self._ssb_power, waveform_resolution=self._waveform_resolution)

    def get_mixer_parameters(self):
        return dict(mixer_id=self._mixer_id, iq_attenuation=self._iq_attenuation)

    def __str__(self):
        return "Calibration data for mixer "+self._mixer_id+\
                "\nMixer parameters: "+str(self.get_mixer_parameters())+\
                "\nRadiation parameters: "+str(self.get_radiation_parameters())+\
                "\nOptimization results: "+str(self.get_optimization_results()[1])+\
                "\nOptimization parameters "+str(self.get_optimization_results()[0])+\
                "\nOptimization time: "+format_time_delta(self._optimization_time)+\
                "\nFinished at: "+str(self._end_date)


class IQCalibrator():

    def __init__(self, awg, sa, lo, mixer_id, iq_attenuation):
        '''
        IQClibrator is a class that allows you to calibrate automatically an IQ mixer to obtain a Single Sideband (SSB) 
        with desired parameters.
        '''
        self._awg = awg
        self._sa = sa
        self._lo = lo
        self._mixer_id = mixer_id
        self._iq_attenuation = iq_attenuation


    def calibrate(self, lo_frequency, if_frequency, lo_power, ssb_power, waveform_resolution=1, initial_guess=None, 
                sa_res_bandwidth=500, iterations=5, minimize_iterlimit=20):
        '''
        Perform the calibration routine to suppress LO and upper sideband LO+IF while maintaining the lower sideband at ssb_power. 

        Parameters:
        ----------
        lo_frequency: float
            Frequency of the local oscillator
        if_frequency: float
            Frequency of the awg-generated wavefomrs, i.e. intermediate frequency
        ssb_power: float
            The power which the remaining sideband LO-IF will have after the optimization
        waveform_resolution: float, ns
            The resolution in time of the arbitrary waveform representing one period of the continuous wave used in calibration
        initial_guess=None : IQCalibrationData
            It's possible to specify the initial guess by passing the IQCalibrationData object from previous calibrations
        sa_res_bandwisth=500: float
            The bandwidth that spectrum analyser will use during the calibration
        iterations=5: int
            The number of iterations of the cycle {optimize_if_offsets, optimize_if_amolitudes, optimize_if_phase}.
            For the dc offsets interation limit is iterations*minimize_iterlimit
        minimize_iterlimit=20: int
            Iteration limit for the minimize function used in each routine listed above    

        Returns:
        iqmx_calibration: IQCalibrationData
            Object containing the parameters and results of the optimization
        '''

        def loss_function_dc_offsets(voltages):
            vdc1, vdc2 = voltages
            self._awg.output_continuous_wave(frequency=0, amplitude=0, phase=0, offset=vdc1, waveform_resolution=waveform_resolution, channel=1)
            self._awg.output_continuous_wave(frequency=0, amplitude=0, phase=0, offset=vdc2, waveform_resolution=waveform_resolution, channel=2)
            self._sa.prepare_for_stb();self._sa.sweep_single();self._sa.wait_for_stb()
            data = self._sa.get_tracedata()
            answer =  data[0]
            print("\rDC offsets: ", voltages, data, end=", ", flush=True)
            return answer
        def loss_function_if_offsets(voltages, args):
            vdc1, vdc2 = voltages
            amp1, amp2 = args[0]
            phase = args[1]
            self._awg.output_continuous_wave(frequency=if_frequency, amplitude=amp1, phase=phase, offset=vdc1, waveform_resolution=waveform_resolution, channel=1)
            self._awg.output_continuous_wave(frequency=if_frequency, amplitude=amp2, phase=0, offset=vdc2, waveform_resolution=waveform_resolution, channel=2)
            self._sa.prepare_for_stb();self._sa.sweep_single();self._sa.wait_for_stb()
            data = self._sa.get_tracedata()
            answer =  data[1]
            print("\rIF offsets: ", voltages, data, end=", ", flush=True)
            return answer
        def loss_function_if_amplitudes(amplitudes, args):
            amp1, amp2 = amplitudes
            vdc1, vdc2 = args[0]
            phase = args[1]
            self._awg.output_continuous_wave(frequency=if_frequency, amplitude=amp1, phase=phase, offset=vdc1, waveform_resolution=waveform_resolution, channel=1)
            self._awg.output_continuous_wave(frequency=if_frequency, amplitude=amp2, phase=0, offset=vdc2, waveform_resolution=waveform_resolution, channel=2)
            self._sa.prepare_for_stb();self._sa.sweep_single();self._sa.wait_for_stb()
            data = self._sa.get_tracedata()
            answer =  data[2] + 10*abs(ssb_power - data[0])
            print("\rAmplitudes: ", amplitudes, data, end=", ", flush=True)
            return answer
        def loss_function_if_phase(phase, args):
            vdc1, vdc2 = args[0]
            amp1, amp2 = args[1]
            self._awg.output_continuous_wave(frequency=if_frequency, amplitude=amp1, phase=phase, offset=vdc1, waveform_resolution=waveform_resolution, channel=1)
            self._awg.output_continuous_wave(frequency=if_frequency, amplitude=amp2, phase=0, offset=vdc2, waveform_resolution=waveform_resolution, channel=2)
            self._sa.prepare_for_stb();self._sa.sweep_single();self._sa.wait_for_stb()
            data = self._sa.get_tracedata()
            answer =  data[2] - data[0]
            print("\rPhase: ", phase/pi, data, end=", ", flush=True)
            return answer

        def iterate_minimization(prev_results, n=2):

            res_if_offs = minimize(loss_function_if_offsets, prev_results["if_offsets"], args=[prev_results["if_amplitudes"], prev_results["if_phase"]],
                              method="Nelder-Mead", options={"maxiter":minimize_iterlimit, "xatol":1e-3, "fatol":10})
            res_amps = minimize(loss_function_if_amplitudes, prev_results["if_amplitudes"], args=[res_if_offs.x, prev_results["if_phase"]],
                                method="Nelder-Mead", options={"maxiter":minimize_iterlimit, "xatol":1e-3, "fatol":10})
            res_phase = minimize(loss_function_if_phase, prev_results["if_phase"], args=[res_if_offs.x, res_amps.x],
                                 method="Nelder-Mead", options={"maxiter":minimize_iterlimit, "xatol":1e-3, "fatol":10})
            results["if_offsets"] = res_if_offs.x
            results["if_amplitudes"] = res_amps.x
            results["if_phase"] = res_phase.x
            if(n-1==0):
                return
            iterate_minimization(results, n-1)

        start = datetime.now()

        self._lo.set_power(lo_power)
        self._lo.set_frequency(lo_frequency)
        self._lo.set_output_state("ON")

        self._awg.set_channel_coupling(True)

        results = None
        if initial_guess==None:
            results = {"dc_offsets":(0.1,0.1), "if_offsets":(0.1,0.1), "if_amplitudes":(0.5,0.5), "if_phase":pi*0.54}
        else:
            results = initial_guess

        self._sa.setup_list_sweep([lo_frequency], [sa_res_bandwidth])

        res_dc_offs = minimize(loss_function_dc_offsets, results["dc_offsets"],
                      method="Nelder-Mead", options={"maxiter":minimize_iterlimit*iterations,"xatol":1e-3, "fatol":100})

        self._sa.setup_list_sweep([lo_frequency-if_frequency, lo_frequency, lo_frequency+if_frequency], [sa_res_bandwidth]*3)

        results["if_offsets"]=res_dc_offs.x
        iterate_minimization(results, iterations)

        spectral_values = {"dc":res_dc_offs.fun, "if":self._sa.get_tracedata()}
        elapsed_time = (datetime.now() - start).total_seconds()  

        self._sa.setup_swept_sa(lo_frequency, 2.5*if_frequency, nop=1001, rbw=1e4)
        self._sa.set_continuous()

        return IQCalibrationData( self._mixer_id, self._iq_attenuation, lo_frequency, lo_power, if_frequency, ssb_power, waveform_resolution,
         res_dc_offs.x, results["if_offsets"], results["if_amplitudes"], results["if_phase"], spectral_values, elapsed_time, datetime.now())



def format_time_delta(delta):
    hours, remainder = divmod(delta, 3600)
    minutes, seconds = divmod(remainder, 60)
    return '%s h %s m %s s' % (int(hours), int(minutes), round(seconds, 2))

from lib2.Measurement import Measurement
from lib2.MeasurementResult import MeasurementResult
from lib2.DispersiveRabiOscillations import DispersiveRabiOscillations

class DispersiveRabiFromFrequency(Measurement):
    '''
    @brief: class is used to measure qubit lifetimes from the flux/qubit frequency
            displacement from the sweet-spot.

            Measurement setup is the same as for the any other dispersive measurements

            class constructor must be provided with the following dictionary key;val pairs
                vna;"vector_network_analyzer_name"
                    vector analyzer that performs resonator readout
                q_lo;"microwave_source_device_name"
                    microwave source that performs qubit excitation
                current_source;"current_source_name"
                    current source that controls flux through the qubit
                ro_awg;IQAWG class instance
                    vna mixer object, responsible for readout pulses
                q_awg;IQAWG class instance
                    mw_src mixer object, responsible for qubit excitation pulses

                tts_result; TwoToneSpectroscopyResult class instance
                    contains lust successful TTS result performed around sweet spot
                ss_current: sweet_spot current, detected manually from the tts_result
                ss_freq: sweet_spot frequency, detected manually from the tts_result
    '''
    def __init__(self, name, sample_name, plot_update_interval=5, **kwargs):
        ## Equipment variables declaration section START ##
        self._vna = None
        self._mw_src = None
        self._current_source = None
        self._ro_awg = None
        self._q_awg = None
        ## Equipment variables declaration section END ##

        # last successful two tone spectroscopy result
        self._tts_result = kwargs["tts_result"]

        # constructor initializes devices from kwargs.keys() with '_' appended
        super().__init__(name, sample_name, kwargs, plot_update_interval)

        # class that is responsible for rabi measurements
        self._DRO = DispersiveRabiOscillations(name, sample_name, **kwargs)

    def set_swept_parameters(self, **swept_pars):
        raise NotImplemented


class RabiFromFrequencyResult(MeasurementResult):
    def __init__(self, name, sample_name):
        super().__init__(name, sample_name)
        self._graph_curve = None

    def _prepare_figure(self):
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(1,1)
        ax.set_xlabel( "$\delta\nu$, MHz")
        ax.set_ylabel( "$T_R, \; \mu s$")
        ax.grid()
        self._graph_curve, = ax.scatter()
        ax.set_xlimit(self.)
        return fig, [ax], None

    def _plot(self, axes, caxes):
        '''
        caxes is None
        '''
        ax = axes[0]
        line = ax.get_lines()[0] # the only line of this class is T_R( f - f0 )
        line.set_data()





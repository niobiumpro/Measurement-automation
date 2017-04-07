from lib import ResonatorDetector as RD
from lib import parametric_sweep_with_plot as ps
from time import sleep



def detect_resonator_frequency_at_the_sweet_spot():

    vna.set_nop(100)
    # current.set_current(.2e-3) # manual value for non-symmetric scans
    current.set_current(mean((currents[0], currents[-1]))) # for symmetric scans
    current.set_status(1)
    sleep(1)

    vna.avg_clear()
    vna.prepare_for_stb()
    vna.sweep_single()
    vna.wait_for_stb()
    res_freq1 = RD.detect_resonator(vna, type="FIT")[0]

    vna.set_nop(1)
    vna.set_center(res_freq1)
    vna.prepare_for_stb()
    vna.sweep_single()
    vna.wait_for_stb()

    print(vna.get_frequencies(), 20*log10(abs(vna.get_sdata())))

try:
    start_center_freq = RD.detect_resonator(vna, type="AMP")[0]
    start_center_freq2 = RD.detect_resonator(vna, type="FIT")
    print("Idle amplitude center freq", start_center_freq, "vs fitresult center frequency:", start_center_freq2)

    # currents = np.linspace(-58.5e-6-7e-6,-58.5e-6+7e-6, 100)
    # mw_src_freqs = np.linspace(10.3e9, 10.5e9, 100)
    currents = np.linspace(.260e-3, .300e-3, 50)
    mw_src_freqs = np.linspace(9e9, 9.3e9, 100)

    center_freqs = None
    # Should we use adaptive center frequencies
    adaptive_center_freqs = False

    current.set_appropriate_range(max(abs(currents)))
    current.set_voltage_compliance(5)

    vna.set_averages(1)
    vna.set_bandwidth(25)
    vna.set_power(-30)

    mw_src.set_power(15)

    if adaptive_center_freqs:
        print("Using adaptive center frequencies estimated before")
        center_freqs = center_freq_estimator(currents) # for an adaptive scan
    else:
        detect_resonator_frequency_at_the_sweet_spot()


    vna.set_nop(1)

    current.set_status(1)
    mw_src.set_output_state("ON")

    # vna._visainstrument.write("DISPlay:VISible OFF")

    measurement = ps.sweep2D(vna, currents, current.set_current, mw_src_freqs, mw_src.set_frequency, center_freqs=center_freqs)#, "xmon_al_bmstu_1-I-spectrum-upper-high-res")



finally:
    # vna._visainstrument.write("DISPlay:VISible ON")
    current.set_current(0)
    current.set_status(0)
    mw_src.set_output_state("OFF")
    vna.avg_clear()
    vna.set_averages(1)
    vna.set_nop(200)
    #lo1.set_status(0)
    vna.set_center(start_center_freq)
    vna.set_span(5e6)
    vna.set_bandwidth(50)
    vna.set_power(-30)
    vna.prepare_for_stb()
    vna.sweep_single()
    vna.wait_for_stb()
    vna.autoscale_all()

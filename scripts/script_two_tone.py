from lib import ResonatorDetector as RD
from lib import parametric_sweep as ps
from time import sleep



def detect_resonator_frequency_at_the_sweet_spot():

    znb.set_nop(100)
    # current.set_current(???) # manual value for non-symmetric scans
    current.set_current(mean((currents[0], currents[-1]))) # for symmetric scans
    current.output_on()

    znb.avg_clear()
    znb.prepare_for_stb()
    znb.sweep_single()
    znb.wait_for_stb()
    res_freq1 = RD.detect_resonator(znb, type="AMP")[0]

    znb.set_nop(1)
    znb.set_center(res_freq1)
    znb.prepare_for_stb()
    znb.sweep_single()
    znb.wait_for_stb()

    print(znb.get_frequencies(), 20*log10(abs(znb.get_sdata())))

try:

    start_center_freq = RD.detect_resonator(znb, type="AMP")[0]
    start_center_freq2 = RD.detect_resonator(znb, type="FIT")
    print("Idle cetnter freq", start_center_freq, "vs fitresult:", start_center_freq2)

    currents = np.linspace(-8.5e-3, 0.65e-3, 200)
    mw_src_freqs = np.linspace(9e9, 9.7e9, 200)

    center_freqs = None
    # Should we use adaptive center frequencies
    adaptive_center_freqs = False

    current.set_range(max(abs(currents)))
    current.set_compliance(5)

    znb.set_averages(5)
    znb.set_bandwidth(10)
    znb.set_power(-40)

    mw_src.set_power(10)

    if adaptive_center_freqs:
        print("Using adaptive center frequencies estimated before")
        center_freqs = center_freq_estimator(currents) # for an adaptive scan
    else:
        detect_resonator_frequency_at_the_sweet_spot()


    znb.set_nop(1)

    current.output_on()
    mw_src.set_output_state("ON")
    measurement = ps.sweep2D(znb, currents, current.set_current, mw_src_freqs, mw_src.set_frequency, center_freqs=center_freqs)#, "xmon_al_bmstu_1-I-spectrum-upper-high-res")



finally:
    current.set_current(0)
    current.output_off()
    mw_src.set_output_state("OFF")
    znb.avg_clear()
    znb.set_averages(10)
    znb.set_nop(200)
    #lo1.set_status(0)
    znb.set_freq_center_span(start_center_freq, 5e6)
    znb.set_bandwidth(50)
    znb.set_power(-60)
    znb.sweep_single()

from lib import ResonatorDetector as RD
from lib import parametric_sweep as ps
from time import sleep

def detect_resonator_frequency_at_the_sweet_spot():

    znb.set_nop(100)
    old_avg = znb.get_averages()
    old_bw = znb.get_bandwidth()
    znb.set_bandwidth(10)
    znb.set_averages(5)
    current.output_on()

    znb.avg_clear()
    znb.prepare_for_stb()
    znb.sweep_single()
    znb.wait_for_stb()
    res_freq1 = RD.detect_resonator(znb, type="FIT")[0]

    znb.set_averages(old_avg)
    znb.set_bandwidth(old_bw)
    znb.set_nop(1)
    znb.set_center(res_freq1)
    znb.prepare_for_stb()
    znb.sweep_single()
    znb.wait_for_stb()

    print(znb.get_frequencies(), 20*log10(abs(znb.get_sdata())))


try:

    start_center_freq = RD.detect_resonator(znb, type="AMP")[0]
    start_center_freq2 = RD.detect_resonator(znb, type="FIT")[0]
    print("AMP:", RD.detect_resonator(znb, type="AMP"), "vs FIT:", RD.detect_resonator(znb, type="FIT"))

    mw_src_freqs = np.linspace(9.496e9, 9.5e9, 100)
    mw_src.set_power(5)

    powers = linspace(-60, -50, 20)

    current.set_current(-4.13e-3)
    current.output_on()

    znb.set_averages(20)
    znb.set_bandwidth(1)
    znb.set_power(-60)

    detect_resonator_frequency_at_the_sweet_spot()

    mw_src.set_output_state("ON")
    measurement = ps.sweep2D(znb, powers, znb.set_power, mw_src_freqs, mw_src.set_frequency)



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

from lib import ResonatorDetector as RD
from lib import parametric_sweep_with_plot as ps
from time import sleep

def detect_resonator_frequency_at_the_sweet_spot():

    vna.set_nop(100)
    old_avg = vna.get_averages()
    old_bw = vna.get_bandwidth()
    vna.set_bandwidth(100)
    vna.set_averages(1)
    current.set_status(1)

    vna.avg_clear()
    vna.prepare_for_stb()
    vna.sweep_single()
    vna.wait_for_stb()
    res_freq1 = RD.detect_resonator(vna, type="FIT")[0]

    vna.set_averages(old_avg)
    vna.set_bandwidth(old_bw)
    vna.set_nop(1)
    vna.set_center(res_freq1)
    vna.prepare_for_stb()
    vna.sweep_single()
    vna.wait_for_stb()

    print(vna.get_frequencies(), 20*log10(abs(vna.get_sdata())))


try:

    start_center_freq = RD.detect_resonator(vna)[0]

    mw_src_freqs = np.linspace(9.22e9, 9.226e9, 100)

    powers = linspace(-10, -11, 2)

    current.set_current(.285e-3)
    current.set_status(1)

    vna.set_averages(10)
    vna.set_bandwidth(10)
    vna.set_power(-35)

    detect_resonator_frequency_at_the_sweet_spot()

    mw_src.set_output_state("ON")
    measurement = ps.sweep2D(vna, powers, mw_src.set_power, mw_src_freqs, mw_src.set_frequency)



finally:
    current.set_current(0)
    current.set_status(0)
    mw_src.set_output_state("OFF")
    vna.avg_clear()
    vna.set_averages(10)
    vna.set_nop(200)
    #lo1.set_status(0)
    vna.set_center(start_center_freq)
    vna.set_span(10e6)
    vna.set_bandwidth(50)
    vna.set_power(-20)
    vna.sweep_single()

from lib import ResonatorDetector as RD
from lib import parametric_sweep as ps
from time import sleep

try:

    start_center_freq = RD.detect_resonator(znb)[0]

    mw_src_freqs = np.linspace(6.4e9, 6.65e9, 300)
    mw_src.set_power(5)

    powers = np.linspace(-60, 0, 100)

    current.set_current(-4.13e-3)
    current.output_on()

    znb.prepare_for_stb()
    znb.sweep_single()
    znb.wait_for_stb()
    znb.set_freq_center_span(RD.detect_resonator(znb)[0], 5e6)
    znb.set_bandwidth(100)
    znb.set_nop(100)

    center_freqs = []
    averages = np.round(abs(powers/7)**2)
    for idx, power in enumerate(powers):

        znb.set_averages(averages[idx])
        znb.set_power(power)
        znb.avg_clear()
        znb.prepare_for_stb()
        znb.sweep_single()
        znb.wait_for_stb()

        center_freqs.append(RD.detect_resonator(znb)[0])

    print("Using center frequencies from %.5f to %.5f"%(min(center_freqs)/1e9, max(center_freqs)/1e9))

    znb.set_nop(1)

    mw_src.set_output_state("ON")
    measurement = ps.sweep2D(znb, powers, znb.set_power, mw_src_freqs, mw_src.set_frequency, center_freqs=center_freqs, averages = averages)



finally:
    current.set_current(0)
    current.output_off()
    mw_src.set_output_state("OFF")
    znb.avg_clear()
    znb.set_averages(1)
    znb.set_nop(200)
    #lo1.set_status(0)
    znb.set_freq_center_span(start_center_freq, 5e6)
    znb.set_bandwidth(100)
    znb.set_power(-20)
    znb.sweep_single()

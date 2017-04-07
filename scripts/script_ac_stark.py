from lib import ResonatorDetector as RD
from lib import parametric_sweep as ps
from time import sleep

try:

    start_center_freq = RD.detect_resonator(vna)[0]

    mw_src_freqs = np.linspace(9.2e9, 9.23e9, 100)
    mw_src.set_power(0)

    powers = np.linspace(-50, -20, 31)

    current.set_current(.276e-3)
    current.set_status(1)

    vna.set_bandwidth(500)
    vna.set_averages(1)
    vna.set_nop(100)

    center_freqs = []
    averages = np.round((10**(abs(powers)/50))**2)
    for idx, power in enumerate(powers):

        vna.set_averages(averages[idx])
        vna.set_power(power)
        vna.avg_clear()
        vna.prepare_for_stb()
        vna.sweep_single()
        vna.wait_for_stb()

        center_freqs.append(RD.detect_resonator(vna, type="FIT")[0])

    print("Using center frequencies from %.5f to %.5f"%(min(center_freqs)/1e9, max(center_freqs)/1e9))

    vna.set_nop(1)
    vna.set_bandwidth(25)

    mw_src.set_output_state("ON")
    measurement = ps.sweep2D(vna, powers, vna.set_power, mw_src_freqs, mw_src.set_frequency, center_freqs=center_freqs, averages = averages)



finally:
    current.set_current(0)
    current.set_status(0)
    mw_src.set_output_state("OFF")
    vna.avg_clear()
    vna.set_averages(1)
    vna.set_nop(200)
    #lo1.set_status(0)
    vna.set_center(start_center_freq)
    vna.set_span(20e6)
    vna.set_bandwidth(50)
    vna.set_power(-20)
    vna.sweep_single()

from lib import ResonatorDetector as RD
from lib import parametric_sweep as ps
from time import sleep

try:

    start_center_freq = znb.get_center()

    res_freq1 = 6.6212e9

    znb.set_freq_center_span(res_freq1, 1)

    currents = np.linspace(0.28e-3, 0.48e-3, 400)
    #currents = np.linspace(0.3e-3, 0.38e-3, 160)
    current.set_compliance(1)
    current.set_range(max(abs(currents)))

    mw_src_freqs = np.linspace(6.8e9, 9.8e9, 450)
    mw_src.set_power(-8)

    znb.set_averages(3)
    znb.set_nop(1)
    znb.set_power(-30)
    znb.set_bandwidth(15)

    current.output_on()
    mw_src.set_output_state("ON")
    measurement = ps.sweep2D(znb, currents, current.set_current, mw_src_freqs, mw_src.set_frequency)#, "res with freq %.3e"%(res_freq1))

finally:
    current.set_current(0)
    current.output_off()
    mw_src.set_output_state("OFF")
    znb.avg_clear()
    znb.set_nop(200)
    #lo1.set_status(0)
    znb.set_freq_center_span(start_center_freq, 5e6)
    znb.set_bandwidth(50)
    znb.set_power(-50)
    znb.sweep_single()

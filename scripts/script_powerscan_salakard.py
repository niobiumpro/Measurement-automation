from lib import ResonatorDetector as RD
from lib import parametric_sweep as ps
from time import sleep

try:

   # start_center_freq = RD.detect_resonator(znb)[0]
    start_center_freq = 5.892e9

    mw_src_freqs = np.linspace(3.5e9, 4.5e9, 400)
    mw_src.set_power(-20)
        
    powers = np.linspace(-20, 14, 200)

    current.set_current(-0.59e-3)
    current.output_on()

    znb.set_nop(100)
    znb.set_averages(50)
    znb.set_power(-30)

    znb.avg_clear()
    znb.prepare_for_stb()
    znb.sweep_single()
    znb.wait_for_stb()
    znb.set_freq_center_span(RD.detect_resonator(znb)[0], 1)
    print(RD.detect_resonator(znb))
    znb.scale_auto_by_trace_name("Trc1")

    znb.set_nop(1)
    znb.set_averages(20)
    mw_src.set_output_state("ON")
    measurement = ps.sweep2D(znb, powers, mw_src.set_power, mw_src_freqs, mw_src.set_frequency)
    
    

finally:
    current.set_current(0)	
    current.output_off()
    mw_src.set_output_state("OFF")
    znb.avg_clear()
    znb.set_averages(10)
    znb.set_nop(200)
    #lo1.set_status(0)
    znb.set_freq_center_span(start_center_freq, 5e6)
    znb.set_bandwidth(100)
    znb.set_power(-30)
    znb.sweep_single()

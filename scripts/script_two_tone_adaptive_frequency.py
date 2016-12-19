from lib import ResonatorDetector as RD
from lib import parametric_sweep as ps
from time import sleep

try:

    start_center_freq = RD.detect_resonator(znb)[0]

    currents = np.linspace(-1490e-6, 930e-6, 200)
    current.set_compliance(1)
    current.set_range(max(abs(currents)))

    center_freqs = center_freq_estimator(currents)
    
    for idx, current_val in enumerate(currents):
        current.set_current(current_val)
        znb.avg_clear()
        znb.prepare_for_stb()
        znb.sweep_single()
        znb.wait_for_stb()
        center_freq = RD.detect_resonator(znb)[0]
        center_freqs.append(center_freq)
        znb.set_freq_center_span(center_freq, 10e6)
        print("\rCurrent %.3e, center frequency %.5e"%(current_val, center_freq), end=" %.2f %%"%(100*idx/len(currents)), flush=True)

    mw_src_freqs = np.linspace(7e9, 10.5e9, 300)
    mw_src.set_power(-10)

    znb.set_averages(1)
    znb.set_bandwidth(10)
    znb.set_nop(1)
    znb.set_power(-45)

    current.output_on()
    mw_src.set_output_state("ON")
    measurement = ps.sweep2D(znb, currents, current.set_current, mw_src_freqs, mw_src.set_frequency, center_freqs=center_freqs)#, "res with freq %.3e"%(res_freq1))



finally:
    current.set_current(0)
    current.output_off()
    mw_src.set_output_state("OFF")
    znb.avg_clear()
    znb.set_averages(10)
    znb.set_nop(200)
    #lo1.set_status(0)
    znb.set_freq_center_span(start_center_freq, 5e6)
    znb.set_bandwidth(1000)
    znb.set_power(-20)
    znb.sweep_single()

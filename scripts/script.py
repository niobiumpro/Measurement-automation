from lib import ResonatorDetector as RD
from lib import parametric_sweep as ps


try:
	#mvna._sw_2D(current_coil, 'coilcurrent', fluxbias_coil.set_current, current_biasT, 'fluxbias', fluxbias.set_current)


    # res_freq1 = RD.detect_resonator(znb)[0]
    # znb.set_center(res_freq1)


    currents = np.linspace(-13.5e-3, 5.5e-3, 50)
    current.set_range(max(abs(currents)))


    znb.set_xlim(6.615e9, 6.625e9)
    znb.set_bandwidth(100)
    znb.set_averages(2)
    znb.set_nop(50)
    znb.set_power(-60)

	# arr = arange(-20e-3, 20e-3+1e-3, 1e-3)
	# currents = zeros_like(arr)
	# j=0
	# for i in range(0, arr.shape[0]-1, 2):
		# currents[i] = arr[arr.shape[0]//2 - j] # Symmetric currents
		# currents[i+1] = arr[arr.shape[0]//2 + j+1]
		# j+=1

	# currents[-1] = -20e-3
	#print(arr)
	#print(currents)
	#currents = arange(-6e-3, 1e-3, 0.05e-3)    ##0.03e-3 step for holidays spectrum

    #current.set_current(0.12e-3)
    current.output_on()
    current.set_compliance(5)

	###Flux aiming and anticrossing
    #lo1.set_status(1)
    measurement = ps.sweep1D(znb, currents, current.set_current) #, filename="powers, res freq %.3e"%(res_freq1))
    #measurement = ps.sweep1D(znb, tone2freq, lo1.set_frequency)
	#measurement8 = ps.sweep1D(znb, tone2powers, lo1.set_power)
	#lo1.set_status(0)
	#reference5 = ps.sweep1D(znb, znb_powers, znb.set_power)
    #marray = []
    #for m in range(0, 1):
    #    marray.append(ps.sweep1D(znb, currents, current.set_current))

	###Spectrum
    #current.set_status(1)
    #lo1.set_status(1)
    #measurement = ps.sweep2D(znb, currents, current.set_current, tone2freq, lo1.set_frequency)#, "res with freq %.3e"%(res_freq1))

	###LZ interference
    #current.set_status(1)
    #measurement = ps.sweep2D(znb, powers, znb.set_power, currents, current.set_current)



finally:
    current.set_current(0)
    current.output_off()
    # mw_src.set_output_state("OFF")
    # znb.avg_clear()
    znb.set_nop(100)
    #lo1.set_status(0)
    # znb.set_span(50e6)
    #znb.set_bandwidth(10)
    #znb.set_averages(10)
    znb.set_power(-30)
    znb.sweep_single()
    znb.autoscale_all()

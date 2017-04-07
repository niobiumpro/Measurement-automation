from lib import ResonatorDetector as RD
from lib import parametric_sweep_with_plot as ps


try:
	#mvna._sw_2D(current_coil, 'coilcurrent', fluxbias_coil.set_current, current_biasT, 'fluxbias', fluxbias.set_current)


    # res_freq1 = RD.detect_resonator(vna)[0]
    # vna.set_center(res_freq1)


    # currents = np.linspace(-150e-6, 35e-6, 100)
    currents = np.linspace(0.e-3, .5e-3, 50)

    current.set_appropriate_range(max(abs(currents)))


    vna.set_xlim(6.61e9, 6.65e9)
    vna.set_bandwidth(50)
    vna.set_averages(1)
    vna.set_nop(50)
    vna.set_power(-35)
    #powers = np.linspace(-70, -40, 60)

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
    current.set_voltage_compliance(5)
    current.set_status(1)

	###Flux aiming and anticrossing
    #lo1.set_status(1)
    measurement = ps.sweep1D(vna, currents, current.set_current) #, filename="powers, res freq %.3e"%(res_freq1))
    #measurement = ps.sweep1D(vna, powers, .set_frequency)
	#measurement8 = ps.sweep1D(vna, tone2powers, lo1.set_power)
	#lo1.set_status(0)
	#reference5 = ps.sweep1D(vna, vna_powers, vna.set_power)
    #marray = []
    #for m in range(0, 1):
    #    marray.append(ps.sweep1D(vna, currents, current.set_current))

	###Spectrum
    #current.set_status(1)
    #lo1.set_status(1)
    #measurement = ps.sweep2D(vna, currents, current.set_current, tone2freq, lo1.set_frequency)#, "res with freq %.3e"%(res_freq1))
    #measurement = ps.sweep2D(vna, currents, current.set_current, powers, vna.set_power)

	###LZ interference
    #current.set_status(1)
    #measurement = ps.sweep2D(vna, powers, vna.set_power, currents, current.set_current)



finally:
    current.set_current(0)
    current.set_status(0)
    # mw_src.set_output_state("OFF")
    # vna.avg_clear()
    vna.set_nop(100)
    #lo1.set_status(0)
    # vna.set_span(50e6)
    #vna.set_bandwidth(10)
    #vna.set_averages(10)
    vna.set_power(-30)
    vna.prepare_for_stb()
    vna.sweep_single()
    vna.wait_for_stb()
    vna.autoscale_all()

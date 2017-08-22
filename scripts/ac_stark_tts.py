from numpy import *
ro_powers = linspace(-20, 0, 11)
start_averages = 100
avg_factors = exp((ro_powers - ro_powers[0])/ro_powers[0]*log(start_averages))*start_averages
for idx,ro_power in enumerate(ro_powers):
    TTS = FluxTwoToneSpectroscopy("IV-two-tone_"+str(ro_power)+"_ro_power", "Xmons_Nb_bandage", vna_name="vna1",
                                  mw_src_name="mxg", current_src_name="yok3")
    vna_parameters = {"bandwidth":600, "freq_limits":res_limits, "nop":3, "sweep_type":"LIN", "power":ro_power, "averages":round(avg_factors[idx])}
    mw_src_parameters = {"power":-15}
    mw_src_frequencies = linspace(6.6e9, 7.8e9, 201)
    currents = linspace(0.65e-3, 1.15e-3, 101)
    TTS.setup_control_parameters(vna_parameters, mw_src_parameters, mw_src_frequencies, currents)

    tts_result = TTS.launch()
    tts_result.save()

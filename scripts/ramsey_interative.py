
for i in range(0, 100):
    DR = DispersiveRamsey("%s-gauss-ramsey_%i"%(qubit_idx, i), sample_name, vna_name="vna4",
                  ro_awg=ro_awg, q_awg=q_awg, q_lo_name='psg2', plot_update_interval=0.1)
    vna_parameters = {"bandwidth":1, "freq_limits":[ro_freq]*2, "nop":2, "averages":1}
    ramsey_delays = linspace(0, 2000, 150)
    exc_frequency = q_freq-5e6
    ramsey_sequence_parameters =\
     {"awg_trigger_reaction_delay":0, "readout_duration":1000,
      "excitation_amplitude":pi_pulse_amplitude/2, "modulating_window":"rectangular",
      "repetition_period":20000, "half_pi_pulse_duration":50}
    DR.set_fixed_parameters(vna_parameters, ro_awg_params, q_awg_params,
                                    exc_frequency, ramsey_sequence_parameters)
    DR.set_swept_parameters(ramsey_delays)
    DR.set_basis(basis)
    dr_result = DR.launch()
    dr_result.save()
    clear_output(wait=True)

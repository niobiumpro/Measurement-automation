import numpy as np

def transmon_spectrum(curs, period, sweet_spot_cur, max_freq, d):
    phis = (curs-sweet_spot_cur)/period
    return max_freq*np.sqrt(abs(np.cos(np.pi*phis))*np.sqrt(1+d**2*np.tan(np.pi*phis)**2))

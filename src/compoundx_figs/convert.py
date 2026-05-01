import numpy as np


def ph_to_hplus_nmol(ph):
    return 10 ** (-ph) * 1e9


def hplus_nmol_to_ph(hplus_nmol):
    return -np.log10(hplus_nmol * 1e-9)

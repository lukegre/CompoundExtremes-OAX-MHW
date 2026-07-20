"""
Data for the "When Ocean Heatwaves Turn Acidic" infographic.

All values are transcribed from Table 1 of:
    Gregor, L. & Gruber, N. (2025). "Recent history of surface ocean
    acidification extremes that compound marine heatwaves", AGU Advances.
    Data product: OceanSODA-ETHZ, 1982-2024.

Edit the numbers here and re-run any chart script to regenerate the figure.
`area` is the event-maximum area in millions of km^2.
`dur`  is the Lagrangian duration (L) in months.
`I`    is the 95th-percentile normalised compound intensity (OAX n MHW).
`lon`/`lat` are approximate event centroids for map placement.
"""
import numpy as np

# --- The largest / most notable compound (OAX n MHW) events ----------------
EVENTS = [
    dict(key="blob",   name="The Blob",           region="NE Pacific", year=2015, lon=-142, lat=46,  area=12.6, dur=12, I=3.52, note="Largest on record"),
    dict(key="catl",   name="Central Atlantic",   region="C Atlantic", year=2023, lon=-20,  lat=-6,  area=12.5, dur=14, I=3.44, note="+N. Atlantic = 19.3 Mkm2"),
    dict(key="seasia", name="Southeast Asia",     region="SE Asia",    year=1998, lon=123,  lat=3,   area=7.5,  dur=20, I=2.87, note="Longest tracked (20 mo)"),
    dict(key="natl",   name="North Atlantic",     region="N Atlantic", year=2023, lon=-34,  lat=49,  area=6.9,  dur=11, I=3.22, note=""),
    dict(key="spac",   name="South Pacific",      region="S Pacific",  year=2016, lon=-132, lat=-33, area=4.0,  dur=8,  I=3.31, note=""),
    dict(key="gbr",    name="Great Barrier Reef", region="Coral Sea",  year=2022, lon=153,  lat=-16, area=3.3,  dur=9,  I=2.76, note=""),
    dict(key="med",    name="Mediterranean Sea",  region="Med Sea",    year=2003, lon=17,   lat=39,  area=1.3,  dur=4,  I=3.52, note=""),
    dict(key="mad",    name="Madagascar",         region="SW Indian",  year=1987, lon=52,   lat=-22, area=1.0,  dur=8,  I=3.53, note=""),
    dict(key="waus",   name="Western Australia",  region="W Australia",year=2011, lon=110,  lat=-29, area=0.7,  dur=6,  I=3.90, note="Most intense"),
]

INTENSITY_RANGE = (2.5, 4.05)   # colour-scale domain for event intensity

# --- ENSO phases (approximate ONI-based classification) --------------------
NINO_YEARS = {1982, 1983, 1987, 1991, 1992, 1994, 1997, 1998, 2002, 2003,
              2004, 2006, 2009, 2014, 2015, 2016, 2018, 2019, 2023}
NINA_YEARS = {1984, 1985, 1988, 1989, 1995, 1996, 1999, 2000, 2007, 2008,
              2010, 2011, 2012, 2017, 2020, 2021, 2022}

# --- Relative global compound-event area per year (for the 43-year ring) ----
# NOTE: illustrative series. Replace with the real annual OAX n MHW area
# time series to make the ring quantitatively exact.
RING_AREA = {
    1982: .55, 1983: .72, 1984: .20, 1985: .15, 1986: .28, 1987: .50,
    1988: .42, 1989: .22, 1990: .18, 1991: .35, 1992: .40, 1993: .20,
    1994: .30, 1995: .25, 1996: .20, 1997: .60, 1998: .90, 1999: .35,
    2000: .22, 2001: .20, 2002: .40, 2003: .62, 2004: .30, 2005: .28,
    2006: .32, 2007: .30, 2008: .24, 2009: .34, 2010: .42, 2011: .66,
    2012: .40, 2013: .40, 2014: .55, 2015: 1.00, 2016: .78, 2017: .40,
    2018: .35, 2019: .50, 2020: .42, 2021: .45, 2022: .60, 2023: .95,
    2024: .60,
}
YEARS = list(range(1982, 2025))

# Events to annotate around the ring: (year, label)
RING_LABELS = [
    (1987, "Madagascar 1987"),
    (1998, "SE Asia 1998"),
    (2011, "W. Australia 2011"),
    (2015, "The Blob 2015"),
    (2023, "N & C Atlantic 2023"),
]

# --- Size-of-event distribution (donut, paper Fig. 6 buckets) --------------
SIZE_BUCKETS = [("< 1 M km2", 75), ("1-2 M km2", 16), ("> 2 M km2", 9)]


def enso_area_curves(n=300):
    """Schematic 'compound area vs time' curves for El Nino and La Nina.

    Returns (x, el_nino, la_nina) with x in [0, 1]. Illustrative: the message
    is that compound area peaks at the end of / just after El Nino, during the
    following La Nina.
    """
    x = np.linspace(0, 1, n)
    el = 0.30 + 0.72 * np.exp(-((x - 0.27) / 0.12) ** 2) + 0.30 * np.exp(-((x - 0.84) / 0.05) ** 2)
    la = 0.22 + 0.42 * np.exp(-((x - 0.40) / 0.14) ** 2) + 0.95 * np.exp(-((x - 0.85) / 0.06) ** 2)
    return x, el, la

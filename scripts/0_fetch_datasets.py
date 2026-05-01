"""
Downloads OceanSODA-ETHZ and CMEMS-LSCE-FFNNN2-SOCATv2025 datasets.
Also contains function to load the datasets with hplus computed from pH.
"""

import pathlib

import copernicusmarine
import dotenv
import pandas as pd
import pooch
import xarray as xr

from compoundx_figs.convert import ph_to_hplus_nmol

ROOT = pathlib.Path(dotenv.find_dotenv("pyproject.toml")).parent

FNAME_ETHZ = ROOT / "data/raw/OceanSODA_ETHZ-v2025.OCADS.01-1982-2024.nc"
FNAME_CMEMS = ROOT / "data/raw/CMEMS-LSCE-FFNNN2-SOCATv2025-1985_2024-hplus.nc"


def download_oceanSODA_ETHZ(dest: pathlib.Path = FNAME_ETHZ):

    url = "https://data.up.ethz.ch/shared/OceanSODA-ETHZv1/v2025/OceanSODA_ETHZ-v2025.OCADS.01-1982-2024.nc"

    return pooch.retrieve(url, known_hash=None, fname=dest.name, path=dest.parent, progressbar=True)


def download_cmems_ffnnn2(dest: pathlib.Path = FNAME_CMEMS):

    dataset_id = "cmems_obs-mob_glo_bgc-car_my_irr-i"
    variables = ["ph"]
    d14 = pd.Timedelta(days=14)

    ds = copernicusmarine.open_dataset(dataset_id=dataset_id, variables=variables)
    ds = (
        ds.assign_coords(time=lambda x: x.time + d14)  # shift 1st to 15h
        .rename(latitude="lat", longitude="lon")
        .coarsen(lat=4, lon=4)  # 0.25 --> 1 degree
        .mean()
    )

    ds.to_netcdf(dest, mode="w", encoding={"ph": {"zlib": True, "complevel": 5}})

    return ds


def get_oceansoda() -> xr.Dataset:
    fname = FNAME_ETHZ
    ds = xr.open_dataset(fname, chunks="auto")
    ds["hplus"] = ph_to_hplus_nmol(ds["ph_total"])
    return ds


def get_cmems() -> xr.Dataset:
    fname = FNAME_CMEMS
    ds = xr.open_dataset(fname, chunks="auto")
    ds["hplus"] = ph_to_hplus_nmol(ds["ph"])

    return ds


if __name__ == "__main__":
    download_oceanSODA_ETHZ()
    download_cmems_ffnnn2()

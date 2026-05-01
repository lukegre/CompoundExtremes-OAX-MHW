"""
Script computes compound extreme stats for different configurations defined in EXPERIMENTS.
We run two datasets (ETHZ and CMEMS) for each of the experiment configurations.
"""

import importlib
import pathlib

import dotenv
import xarray as xr
from dask.diagnostics.progress import ProgressBar

from compoundx_figs.compound_extremes import get_compound_extremes
from compoundx_figs.extreme_detection import get_extremes
from compoundx_figs.io import ExtremeVariableInput

dataio = importlib.import_module("0_fetch_datasets")

ROOT = pathlib.Path(dotenv.find_dotenv("pyproject.toml")).parent

# we set period from 1985 to 2024 to have the same period for both datasets
PERIOD = slice("1985", "2024")
# Explaination for quantile quirk in this code
# --------------------------------------------
# quantiles are set to (target - 0.01) since we have exactly 40 years,
# we end up with too few extremes if we set target to exactly 0.975, 0.95, 0.9
# this is because we sample from a bucket of 40 values (each month sampled independently)
# so, if we set Q95, then we end up with only 12 extremes instead of the expected 24 for this threshold
# this does not happen if we have 41 years, so we can then set quantiles to their proper values again.
EXPERIMENTS = [
    {"order": 2, "quantile": 0.97},
    # {"order": 2, "quantile": 0.94},
    # {"order": 2, "quantile": 0.89},
    # {"order": 1, "quantile": 0.97},
    {"order": 1, "quantile": 0.94},
    {"order": 1, "quantile": 0.89},
]


FNAME_ETHZ = ROOT / "data/raw/OceanSODA_ETHZ-v2025.OCADS.01-1982-2024.nc"
FNAME_CMEMS = ROOT / "data/raw/CMEMS-LSCE-FFNNN2-SOCATv2025-1985_2024-hplus.nc"
FNAME_MASKS = ROOT / "data/masks.nc"
OUTPUT_FOLDER = ROOT / "data/v2025/baseline_choices/"


def main():
    ds_ethz = dataio.get_oceansoda().sel(time=PERIOD)
    ds_cmems = dataio.get_cmems().sel(time=PERIOD)

    tempX = ExtremeVariableInput(
        name="ETHZ1v2025",
        data=ds_ethz.temperature.persist(),
        data_valid_range=(-2, 50),
    )

    hplusX_ethz = ExtremeVariableInput(
        name="ETHZ1v2025",
        data=ds_ethz.hplus.persist(),
        data_valid_range=(0, 100),
    )

    hplusX_cmems = ExtremeVariableInput(
        name="CMEMS2v2025",
        data=ds_cmems.hplus.persist(),
        data_valid_range=(0, 100),
    )

    OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)
    run_experiments(tempX, hplusX_ethz)
    run_experiments(tempX, hplusX_cmems)

    flist = list(OUTPUT_FOLDER.glob("*cex*.nc"))
    combined_ds = combine_cex_datasets([str(x) for x in flist])
    combined_ds.to_netcdf(OUTPUT_FOLDER.parent / "cexTH_stats_for_baseline_choices.nc", mode="w")


def run_experiments(tempX, hplusX):
    for exp in EXPERIMENTS:
        run_experiment(exp, tempX, hplusX)


def run_experiment(exp: dict, tempX: ExtremeVariableInput, hplusX: ExtremeVariableInput, **kwargs):

    props = exp | kwargs | {"baseline_type": "shifting", "dest": str(OUTPUT_FOLDER)}
    mhw = get_extremes(tempX.data, dataset_name=tempX.name, **props)
    oax = get_extremes(hplusX.data, dataset_name=hplusX.name, **props)

    _ = get_compound_extremes(
        mhw=mhw,
        oax=oax,
        dataset_name=hplusX.name,
        **kwargs,
        overwrite=False,
        with_stats=True,
        dest=OUTPUT_FOLDER,
    )


def process_cex_nc(ds: xr.Dataset) -> xr.Dataset:
    import re

    fname = ds.encoding["source"]
    keep_vars = ["stats", "mask"]

    dims = {
        "Dataset": re.findall("CMEMS|ETHZ", fname),
        "Baseline": re.findall("shift|fixed", fname),
        "Polynomial order": re.findall("poly([12])", fname),
        "Threshold percentile": [ds["quantile"].compute().item() * 100],
    }

    ds = ds[keep_vars].reset_coords(drop=True).expand_dims(dims)  # type: ignore

    return ds


def combine_cex_datasets(fname_list: list[str]):
    masks = xr.open_dataset(FNAME_MASKS)
    area = masks.area
    ds_list = [process_cex_nc(xr.open_dataset(fname)) for fname in fname_list]
    ds = xr.combine_by_coords(ds_list, combine_attrs="override")

    ds["timeseries"] = area.where(ds.mask).sum(dim=["lat", "lon"])
    ds["num_extremes"] = ds.mask.sum(dim="time")

    return ds


if __name__ == "__main__":
    with ProgressBar():
        main()

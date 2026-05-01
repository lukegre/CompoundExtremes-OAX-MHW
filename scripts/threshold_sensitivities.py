import pathlib

import dotenv
import munch
import xarray as xr
from dask.diagnostics.progress import ProgressBar

from compoundx_figs.compound_extremes import get_compound_extremes
from compoundx_figs.data_models import ExtremeVariableInput
from compoundx_figs.extreme_detection import get_extremes

ROOT = pathlib.Path(dotenv.find_dotenv("pyproject.toml")).parent
PERIOD = slice("1985", "2024")
FNAME = munch.Munch(
    oceansoda1=ROOT
    / "data/raw/OceanSODA_ETHZ1v2025.OCADS-1982_2024-temp_hplus_masks-for_extremes.nc",
    cmems=ROOT / "data/raw/CMEMS_FFNN2v2025-1985_2024-hplus-for_extremes.nc",
)

EXPERIMENTS = [
    {"order": 2, "quantile": 0.97},
    {"order": 2, "quantile": 0.94},
    {"order": 2, "quantile": 0.89},
    {"order": 1, "quantile": 0.97},
    {"order": 1, "quantile": 0.94},
    {"order": 1, "quantile": 0.89},
]

OUTPUT_FOLDER = ROOT / "data/v2025/sensitivities/"


def main():
    ds_ethz = get_oceansoda()
    ds_cmems = get_cmems()

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

    run_experiments(tempX, hplusX_ethz)
    run_experiments(tempX, hplusX_cmems)


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


def get_oceansoda() -> xr.Dataset:
    fname = FNAME
    ds = xr.open_dataset(fname.oceansoda1, chunks="auto")
    ds = ds.sel(time=PERIOD)
    return ds


def get_cmems() -> xr.Dataset:
    fname = FNAME
    ds = xr.open_dataset(fname.cmems, chunks="auto")
    ds = ds.sel(time=PERIOD)

    return ds


if __name__ == "__main__":
    with ProgressBar():
        main()

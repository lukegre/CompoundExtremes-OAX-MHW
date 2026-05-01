import importlib
import pathlib

import dotenv
import xarray as xr

from compoundx_figs.compound_extremes import get_compound_extremes
from compoundx_figs.extreme_detection import get_extremes
from compoundx_figs.io import ExtremeVariableInput

dataio = importlib.import_module("0_fetch_datasets")

ROOT = pathlib.Path(dotenv.find_dotenv("pyproject.toml")).parent


EXPERIMENTS = [{"order": 2, "quantile": 0.95}]
PERIOD = slice("1982", "2024")

FNAME_ETHZ = ROOT / "data/raw/OceanSODA_ETHZ-v2025.OCADS.01-1982-2024.nc"

OUTPUT_FOLDER = ROOT / "data/v2025/"


def main():
    ds_ethz = dataio.get_oceansoda()
    ds_ethz = ds_ethz.sel(time=PERIOD)

    # ExtremeVariableInput ensures correct ranges
    temparature = ExtremeVariableInput(
        name="ETHZ1v2025",
        data=ds_ethz.temperature.persist(),
        data_valid_range=(-2, 50),
    )

    hplus = ExtremeVariableInput(
        name="ETHZ1v2025",
        data=ds_ethz.hplus.persist(),
        data_valid_range=(0, 100),
    )

    OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)
    run_experiments(temparature, hplus)


def get_oceansoda() -> xr.Dataset:
    fname = FNAME_ETHZ
    ds = xr.open_dataset(fname, chunks="auto")
    ds = ds.sel(time=PERIOD)
    return ds


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


if __name__ == "__main__":
    main()

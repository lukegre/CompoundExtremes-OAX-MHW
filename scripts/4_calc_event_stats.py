import pathlib

import dotenv
import pandas as pd
import xarray as xr
from loguru import logger

import compoundx_figs as cxf

ROOT = pathlib.Path(dotenv.find_dotenv("pyproject.toml")).parent

OUTPUT_FOLDER = ROOT / "data/v2025/"


def main():

    data = open_data()

    df_event_stats = data.cex["stats"].to_series().unstack(0)
    df_event_stats = add_new_columns(df_event_stats, data.masks.regions_HL, data.masks.basins)

    df_event_stats.to_csv(OUTPUT_FOLDER / "event_stats.csv")
    logger.success(f"Saved event stats to {OUTPUT_FOLDER / 'event_stats.csv'}")


def open_data():
    fname = str(ROOT / "data/sources.yaml")
    return cxf.Datasets.from_yaml(fname, with_cache=False)


def add_new_columns(
    df: pd.DataFrame, regions_HL: xr.DataArray, basins: xr.DataArray
) -> pd.DataFrame:

    dmax = df["duration_max_mon"]
    df["duration_2sigma_mon_clipped"] = df.duration_2sigma_mon.where(lambda x: x < dmax, dmax)
    df["year_start_decimal"] = year_start_decimal(df["month_start_sice_198201"])
    df["area_max_scl"] = (df.area_max_Mkm2 - df.area_max_Mkm2.min() + 2.3) ** 2.6
    df["cex_intensity_norm_p95_clipped"] = df.cex_intensity_norm_p95.clip(0, 10)

    coords = df[["loc_lat_mode", "loc_lon_mode"]]
    da_selector = coords.to_xarray().rename(loc_lat_mode="lat", loc_lon_mode="lon")
    df["loc_region"] = regions_HL.sel(**da_selector).to_series().astype(int)
    df["loc_basin"] = basins.sel(**da_selector).to_series().astype(int)

    return df


def year_start_decimal(x, start_year=1982):
    return (x // 12 + start_year) + (x % 12) / 12


if __name__ == "__main__":
    main()

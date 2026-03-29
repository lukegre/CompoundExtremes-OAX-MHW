import dotenv

dotenv.load_dotenv()
import pandas as pd
import xarray as xr
from loguru import logger

import compoundx_figs as cxf

ROOT = cxf.get_project_root()


def main():

    data = open_data()
    df_event_stats = data.cex["stats"].to_series().unstack()
    df_event_stats = add_new_columns(df_event_stats, data.masks.regions_HL, data.masks.basins)

    df_event_stats.to_csv(ROOT / "data/derived/event_stats.csv")
    logger.success(f"Saved event stats to {ROOT / 'data/derived/event_stats.csv'}")


def open_data():
    fname = str(ROOT / "data/sources.yaml")
    return cxf.Datasets.from_yaml(fname, with_cache=False)


def add_new_columns(
    df: pd.DataFrame, regions_HL: xr.DataArray, basins: xr.DataArray
) -> pd.DataFrame:

    dmax = df["duration_max_mon"]
    df["duration_2sigma_mon_clipped"] = df.duration_2sigma_mon.where(lambda x: x < dmax, dmax)
    df["year_start_decimal"] = year_start_decimal(df["month_start_sice_198201"])
    df["area_max_km2"] = df["area_max_km2"] * 1e-06
    df["area_max_scl"] = (df.area_max_km2 - df.area_max_km2.min() + 2.3) ** 2.6
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

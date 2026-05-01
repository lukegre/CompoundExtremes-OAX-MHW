import pathlib

import dotenv
import numpy as np
import pandas as pd
import xarray as xr
from dask.diagnostics import ProgressBar
from scipy.stats import mode

ROOT = pathlib.Path(dotenv.find_dotenv("pyproject.toml")).parent
PATH = ROOT / "data"
FNAME_AREA = PATH / "masks/mask_area_per_pixel.nc"
FNAME_REGIONS = PATH / "masks/mask_regions_Hseason_latBands.nc"
FNAME_BASINS = PATH / "masks/mask_basins_reccap2.nc"

START_TIME = "1982-01-01"
VARIABLES = [
    "intensity",
    "magnitude",
    "severity",
    "intensity_norm",
    "severity_norm",
]


def get_compound_extremes(
    mhw,
    oax,
    dataset_name="ETHZv2025",
    dest=ROOT / "data/v2025/",
    center_lon=25.5,
    overwrite=False,
    with_stats=True,
):
    import os

    assert mhw.baseline_type == oax.baseline_type, "Cannot mix baseline types"
    assert mhw.threshold_quantile == oax.threshold_quantile, "Thresholds must be the same"

    baseline = mhw.baseline_type[:5]
    threshold = int(mhw.threshold_quantile * 100)

    if baseline.startswith("fix"):
        assert mhw.baseline_period == oax.baseline_period, "Baseline periods must be the same"
    elif baseline.startswith("shift"):
        assert mhw.baseline_poly_order == oax.baseline_poly_order, (
            "Detrending polynomial must be the same order"
        )
        poly_order = mhw.baseline_poly_order

    fname = os.path.abspath(
        os.path.expanduser(
            f"{dest}/{dataset_name}_cexTH_{baseline}_poly{poly_order}_p{threshold}.nc"
        )
    )

    if os.path.isfile(fname) and (not overwrite):
        print(f"Loading {fname}")
        return xr.open_dataset(fname)

    print(f"File will be written to {fname}")
    with ProgressBar():
        mhw = mhw.compute()
        oax = oax.compute()

    ds = calc_compound_extremes(mhw, oax, center_lon=center_lon, with_stats=with_stats)

    ds.to_netcdf(fname, encoding={k: dict(complevel=4, zlib=True) for k in ds})

    return ds


def calc_compound_stats(blob_mask, **datasets):
    """
    Calculates the statistics of extreme events including duration, area,
    region, and location. Further statistics are performed on intensity,
    magnitude, and severity.

    Parameters
    ----------
    blob_mask: xr.DataArray[bool]
        A boolean mask that matches the shape of the datasets
    datasets: key=xr.Dataset
        Each key=value pair will be evaluated. The dataset should contain
        intensity, magnitude and severity variables (includes normalised vars).
        The mean, max, and 95th percentile of each of these will be calculated.
        Normalised severity and intensities are also processed.

    Returns
    -------
    xr.Dataset:
        Contains a table of statsitics [stats], a mask showing the regions,
        a mask showing the basins.
    """

    def filter_vars(
        ds: xr.Dataset,
        vars: list = VARIABLES,
        filter_func=lambda k, vars: any(str(k).endswith(j) for j in vars),
    ):
        return ds[[k for k in ds if filter_func(k, vars)]]

    vars = VARIABLES

    print("Fetching area, region, and basin masks...")
    area = xr.open_dataarray(FNAME_AREA).compute()
    region = xr.open_dataarray(FNAME_REGIONS).compute()
    basins = xr.open_dataarray(FNAME_BASINS).compute()

    ds = xr.Dataset()
    ds["blobs"] = blob_mask
    ds["area"] = area
    ds["region"] = region
    ds["basin"] = basins

    print("Combining datasets...")
    datasets_list = [add_prefix_suffix(v, k) for k, v in datasets.items()]
    datasets_list = [filter_vars(d, vars=vars) for d in datasets_list]
    ds = xr.merge([ds] + datasets_list, compat="override").compute()

    print("Grouping by blobs...")
    groups = ds.groupby(ds.blobs)
    print("Computing per-blob statistics...")
    info = groups.map(single_blob_stats)
    out = (
        info.to_array(dim="metric")
        .rename(blobs="blob_index")
        .assign_coords(blob_index=lambda x: x.blob_index.astype(int))
        .astype("f8")
        .to_dataset(name="stats")
    )

    out["basin"] = basins.astype("i2")
    out["region"] = region.astype("i2")

    return out


def single_blob_stats(grp: xr.Dataset) -> xr.Dataset:

    def nanmode(arr):
        arr = np.asarray(arr)
        arr = arr[~np.isnan(arr)]
        if len(arr) == 0:
            return np.nan
        return mode(arr).mode

    t0 = pd.Timestamp(START_TIME).to_datetime64().astype("datetime64[M]")

    ds = grp.unstack("stacked_time_lat_lon").sortby(["time", "lat", "lon"]).astype("f4")
    ds["mask"] = ds.blobs.notnull()

    count = ds.mask.sum("time")
    blob_area = ds.area.sum(["lat", "lon"]) / 1e6
    blob_time = blob_area.time.values.astype("datetime64[M]")
    y, x = count.stack(coords=["lat", "lon"]).idxmax().values.tolist()

    duration = count.where(lambda x: x != 0)
    duration_avg = duration.mean()
    duration_std = duration.std()

    # create the dictionary for this iteration
    info = xr.Dataset(
        dict(
            month_start_sice_198201=float(blob_time[0] - t0),
            duration_avg_mon=float(duration_avg),
            duration_max_mon=float(count.max()),
            duration_2sigma_mon=float(duration_avg + 2 * duration_std),
            duration_lagrangian_mon=float(blob_time.size),
            loc_lat_mode=y,
            loc_lon_mode=x,
            loc_region=nanmode(ds.region),
            loc_basin=nanmode(ds.basin),
            area_avg_Mkm2=float(blob_area.mean()) / 1e6,
            area_max_Mkm2=float(blob_area.max()) / 1e6,
        )
    )

    # find all variables with end with any of the strings in VARIABLES
    vars = [k for k in ds.data_vars if any(str(k).endswith(j) for j in VARIABLES)]
    # apply grouped stats to these variables
    ds_avg = ds[vars].mean().pipe(add_prefix_suffix, suffix="avg")
    ds_max = ds[vars].max().pipe(add_prefix_suffix, suffix="max")
    ds_p95 = ds[vars].quantile(0.95).pipe(add_prefix_suffix, suffix="p95")

    info = xr.merge([info, ds_avg, ds_max, ds_p95], compat="override")
    info = info.astype("f8").reset_coords(drop=True)

    return info


def calc_compound_extremes(
    mhw, oax, n_largest: int = 500, center_lon: float | int = 25, with_stats=True
):
    """
    Calculates compound extremes for MHWs and OAXs with a table of statistics
    for each of the blobs.

    Parameters
    ----------
    mhw, oax: xr.Dataset
        A dataset that contains the intensity, severity, magnitude of extreme
        events.
    n_largest: int[500]
        The largest N events will be maintained.
    center_lon: float[25.5]
        Shifts the dataset so that the given value is the center of the map.
        This is so that boundaries do not interfere with events that transcend
        E/W map boundaries. Defaults to Tip of Africa as the center.
    with_stats: bool[True]
        Will calculate the statistics for each of the extreme events in the
        blobs mask

    Returns
    -------
    xr.Dataset:
        Contains blobs, mask, intensity_norm, severity_norm, a table of
        statsitics [stats], a mask showing the regions, a mask showing the
        basins.
    """
    from .extreme_detection import calc_severity_rolling, simple_blob_detection

    dx = int(abs(mhw.lon + center_lon).argmin())
    mhw = mhw.roll(lon=dx, roll_coords=True)
    oax = oax.roll(lon=dx, roll_coords=True)

    mask = mhw.mask & oax.mask

    cex = xr.Dataset()
    cex["blobs"] = simple_blob_detection(mask, n_largest=n_largest)
    cex["mask"] = mask & cex.blobs.notnull()
    cex["intensity_norm"] = (mhw.intensity_norm**2 + oax.intensity_norm**2) ** 0.5
    cex["severity_norm"] = calc_severity_rolling(cex.intensity_norm.where(cex.mask))

    if with_stats:
        stats = calc_compound_stats(cex.blobs, cex=cex, mhw=mhw, oax=oax)
        cex = xr.merge([cex, stats])
    cex = cex.sortby("lon")

    return cex


def add_prefix_suffix(
    ds: xr.Dataset | xr.DataArray, prefix: str = "", suffix: str = ""
) -> xr.Dataset | xr.DataArray:

    p = f"{prefix}_" if prefix and not prefix.endswith("_") else prefix
    s = f"_{suffix}" if suffix and not suffix.startswith("_") else suffix

    if isinstance(ds, xr.Dataset):
        renames = {var: f"{p}{var}{s}" for var in ds.data_vars}
        return ds.rename(renames)
    elif isinstance(ds, xr.DataArray):
        if ds.name is not None:
            return ds.rename(f"{p}{ds.name}{s}")
        return ds
    else:
        raise TypeError(f"Unsupported type for add_prefix_suffix: {type(ds)!r}")

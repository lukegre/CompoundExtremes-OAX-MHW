import os
import pathlib

import dotenv
import numpy as np
import xarray as xr

from .compound_extremes import get_compound_extremes  # noqa: F401

ROOT = pathlib.Path(dotenv.find_dotenv("pyproject.toml")).parent


def get_extremes(
    da,
    baseline_type="shifting",
    quantile=0.95,
    baseline_func="mean",
    n_largest_events=1_000,
    order=2,
    period=slice("1985", "2014"),
    dataset_name="ETHZv2025",
    overwrite=False,
    dest="../data/v2025/",
):
    """
    A high level function for calculating and saving extreme data

    Parameters
    ----------
    da: xr.DataArray
        The data array that is used to calculate the extremes
    baseline_type: str[shifting]
        Can be fixed/shifting
    quantile: float[0.95]
        The percentile threshold for extremes
    ocetrack_thresh: float[0.98]
        Will select the largest 2% of extreme events and the small
        events are excluded
    dataset_name: str[ETHZv2025]
        Important for saving the data accurately
    overwrite: bool[False]
        Will return an existing file/data if it exists
    dest: str[../data/v2025/]
        Where data will be written to
    """
    if baseline_type.startswith("shift"):
        baseline_name = f"B{baseline_func}_shift_poly{order}"
    elif baseline_type.startswith("fix"):
        baseline_name = f"B{baseline_func}_fixed_{period.start}-{period.stop}"
    fname = os.path.abspath(
        os.path.expanduser(
            f"{dest}/{dataset_name}_{da.name}_{baseline_name}_p{int(quantile * 100)}.nc"
        )
    )

    if os.path.isfile(fname) and (not overwrite):
        print(f"Loading {fname}")
        return xr.open_dataset(fname, chunks={})

    print(f"File will be written to {fname}")

    ds = detect_extremes(
        da, baseline_type, quantile=quantile, order=order, clim_agg_func=baseline_func
    )

    mask = ds.intensity_norm > 1

    ds["blobs"] = simple_blob_detection(mask, n_largest=n_largest_events)
    ds["mask"] = mask
    ds["severity"] = calc_severity_rolling(ds.intensity.where(ds.mask))
    ds["severity_norm"] = calc_severity_rolling(ds.intensity_norm.where(ds.mask))

    print("Writing file")
    ds.to_netcdf(fname, encoding={k: dict(complevel=4, zlib=True) for k in ds})

    return ds


def fixed_baseline(
    xda, quantile=0.95, period=slice("1985", "2014"), clim_agg_func="mean", **kwargs
):

    baseline = xda.sel(time=period)

    grp = baseline.groupby("time.month")
    thresh = grp.quantile(quantile, "time", method="linear").sel(month=xda.time.dt.month)
    clim = getattr(grp, clim_agg_func)("time").sel(month=xda.time.dt.month)
    attrs = dict(
        baseline_type="fixed",
        baseline_period=f"{period.start}:{period.stop}",
        threshold_quantile=quantile,
    )

    xds = xr.Dataset()
    xds["threshold"] = thresh.assign_attrs(attrs)
    xds["climatology"] = clim.assign_attrs(aggregation_function=clim_agg_func, **attrs)

    xds = xds.assign_attrs(attrs)

    return xds


def detrended_baseline(
    xda, order=1, window=1, quantile=0.95, quantile_method="higher", clim_agg_func="mean", **kwargs
):
    """
    Detrends the data and calculates a shifting baseline

    Parameters
    ----------
    xda: xr.DataArray
        The data array to be detrended and used for extreme detection
    order: int [1]
        The order of the polynomial fit that will define the trend
    window: int [1]
        The size of the rolling window to apply to the detrended data before
        calculating the quantiles. A window of 1 means no rolling window is applied.
        If the window is set to 3, then points either side of the center point are included
        in the quantile calculation.
    quantile: float [0.95]
        The quantile to use for the threshold calculation. Should be between 0 and 1
    quantile_method: str [higher, lower, nearest, linear]
        The method to use for calculating the quantile. See numpy.quantile for more details.
    clim_agg_func: str [mean, median, max, min]
        The function to use for calculating the climatology. Should be a valid
        xarray groupby aggregation function.
    """

    t = np.around(xda.time.size * (1 - quantile), 1)

    if t <= 12:
        raise ValueError(
            f"The quantile {quantile} is too high for the length of the time series. "
            f"No months would be classified as extreme. The quantile should be less than {1 - 12 / xda.time.size:.2f}. "
            f"Consider lowering the quantile or reducing n_largest_events."
        )

    trend = trend_poly(xda, order=order)
    baseline = xda - trend

    # new addition so that a rolling window around the center window can be used
    windowed = baseline.rolling(time=window, center=True).construct("window")
    grp = windowed.groupby("time.month")
    thresh_12mon = grp.quantile(quantile, dim=["window", "time"], method=quantile_method)
    thresh = thresh_12mon.sel(month=xda.time.dt.month)  # tile the output to the full time series
    clim = getattr(grp, clim_agg_func)(["time", "window"]).sel(month=xda.time.dt.month)

    attrs = dict(
        baseline_type="shifting",
        baseline_poly_order=order,
        baseline_period=f"{xda.time.dt.year.values[0]}:{xda.time.dt.year.values[-1]}",
        threshold_quantile=quantile,
    )

    xds = xr.Dataset()
    xds["threshold"] = (thresh + trend).assign_attrs(**attrs)
    xds["climatology"] = (clim + trend).assign_attrs(func=clim_agg_func, **attrs)
    xds = xds.assign_attrs(attrs)

    return xds


def detect_extremes(xda, baseline_type="fixed", quantile=0.95, verbose=True, **kwargs):
    """
    Detects extremes using either a fixed or shifting baseline.

    Use the Hobday et al. (2016, 2018) approach to detect extreme events
    with a relative threshold based on percentile. We use the 95th percentile
    as the default for the 1deg data.

    Parameters
    ----------
    xda: xr.DataArray
        A DataArray of values to detect extreme events
    baseline_type: str [fixed/shifting]
        A string indicating the type of baseline.
        If fixed, kwargs can include period=slice(start_year, end_year)
        If shifting, kwargs can include order=int indicating polynomial
        order for detrending.
    quantile: float [0.95]
        A float between 0 and 1 to indicate the the extreme threshold
    verbose: bool [True]
        prints out progress

    Returns
    -------
    xr.Dataset:
        A dataset that contains data, intensity, magnitude, and
        normalised_intensity.

    See also
    --------
    lagrangian_event_filter
    """

    def vprint(*args, **kwargs):
        if verbose:
            print(*args, **kwargs)

    vprint("Creating baseline climatology and thresholds")
    if baseline_type == "fixed":
        xds = fixed_baseline(xda, quantile=quantile, **kwargs).compute()
    elif baseline_type == "shifting":
        xds = detrended_baseline(xda, quantile=quantile, **kwargs).compute()
    else:
        raise KeyError("`baseline_type` can only be: [fixed, shifting]")

    # compute the intensity and magnitude of extremes
    xda = xda.compute()

    vprint("Doing some extreme statistics")
    magnitude = xda - xds.climatology
    intensity = xda - xds.threshold
    scaler = xds.threshold - xds.climatology
    normalised_intensity = magnitude / scaler

    xds["data"] = xda
    xds["intensity"] = intensity.assign_attrs(description="peak over threshold")
    xds["magnitude"] = magnitude.assign_attrs(description="peak over mean")
    xds["intensity_norm"] = normalised_intensity.assign_attrs(
        description="(x - threshold) / (threshold - climatology)"
    )

    xds = xds.assign_attrs(
        description=(
            "Extremes detected in the methods described in Hobday et al. "
            "(2016, 2018). If a shifting baseline is used, we detrend the "
            "data rather than using a true shifting baseline, as this "
            "allows for a longer baseline. Further, the full period is then "
            "used as the baseline. A fixed baseline uses a 30-year period. "
            "See global attributes for more details. "
        )
    )

    return xds.astype("float32")


def lagrangian_event_filter(
    masked_intensity, land_mask, n_largest_events=1000, radius=1, min_size_quartile=0.98
):
    """
    A wrapper for OceTrack to set default values and write a description.
    This function may take a while to run.

    Note
    ----
    The default `min_size_quartile` does not work for fixed baselines
    where all events past a certain period become extreme (e.g. pCO2, pH, H+,
    etc). That is, those with a strong long-term temporal trend.

    Parameters
    ----------
    masked_intensity: xr.DataArray [float]
        An array that contains extreme values, where non-extreme pixels are
        masked as nans.
    land_mask: xr.DataArray [bool]
        An array that has True for ocean and False for land
    radius: int [1]
        The minimum radius of blobs - set to 1 to allow for smoother outputs
    min_size_quartile: float [0.98]
        The threshold below which extreme events are excluded. For shifting
        baselines, a high quartile works. For fixed baselines where the data
        has a strong trend (e.g. H+), adjust the min threshold downwards a lot
        If extreme blob detection still fails, then the largest 1000 events are
        picked using scipy.ndimage.label.

    Returns
    -------
    xr.DataArray
        An array of event numbers marked 0-num_events

    See also
    --------
    detect_extremes
    """

    print("Tracking extreme events with OceTrack")
    dims = masked_intensity.dims
    props = dict(
        radius=radius,
        min_size_quartile=min_size_quartile,
        timedim=dims[0],
        xdim=dims[2],
        ydim=dims[1],
    )

    blobs = simple_blob_detection(masked_intensity.notnull(), n_largest=n_largest_events)
    #     try:
    #         blobs = ot.Tracker(
    #             da=masked_intensity,
    #             mask=land_mask,
    #             **props).track()
    #         blobs = blobs.assign_attrs(
    #             description='Blobs are created using the `OceTrack` package.')
    #     except ValueError:
    #         print('Failed to locate blobs with OceTrack, reverting to simpler '
    #               'method. Choosing top 1000 largest blobs')
    #         blobs = simple_blob_detection(masked_intensity.notnull())

    return blobs.astype("float32")


def calc_severity_rolling(da, period=12):

    rolled = da.rolling(time=period, min_periods=1, center=True)
    units = da.attrs.get("units", "units")
    severity = (
        rolled.sum()
        .assign_coords(rolling_period=period)
        .assign_attrs(
            description="A rolling sum of intensity over a period",
            units=f"{units} . {period} months",
        )
    )

    return severity


def simple_blob_detection(bool_mask, n_largest=1_000):
    """
    Get the n largest blobs from a boolean mask and give them labels

    Uses the scipy.ndimage.label function to assign blob event labels.

    Parameters
    ----------
    bool_mask: xr.DataArray(dtype=bool)
        A boolean mask that indicates where extremes are
    n_largest: int[1000]
        Choose only the n_largest events. Note that area per pixel is not
        taken into account, only pixel count.

    Returns
    -------
    xr.DataArray(dtype=float32)
        An array that contains labels of events. Non-events are masked as nans
    """
    import xarray as xr
    from scipy.ndimage import label

    blobs, n_blobs = label(bool_mask)
    print(n_blobs, "blobs detected before filtering")

    # returning the values and counts. Exclude the 1st value (not extremes)
    values, counts = np.array(np.unique(blobs, return_counts=True))[:, 1:]
    largest_n = values[counts.argsort()[-n_largest:]]
    mask = np.isin(blobs, largest_n)

    blobs = label(mask)[0]

    blobs = xr.DataArray(
        data=blobs,
        dims=bool_mask.dims,
        coords=bool_mask.coords,
        attrs=dict(
            description=(
                "Blobs were created with scipy.ndimage.label with the "
                f"largest {n_largest} events being picked. No binary opening "
                "and closing is performed (as in the OceTrack package)."
            )
        ),
    ).where(mask)

    return blobs.astype("float32")


def trend_poly(da, order=1, dim="time", verbose=True):
    """
    Calculates a trend based on a polynomial fit

    Uses polyfit to fit the data and then calculates the trend from
    that data.

    Parameters
    ----------
    da: xr.DataArray / xr.Dataset
        An array with dimension that matches `dim`
    order: int [1]
        The order of the polynomial fit that will define the trend
    verbose: bool [True]
        if the input is a dataset, will print the variable keys

    Returns
    -------
    xr.Dataset/xr.DataArray:
        Trends of all the data

    See also
    --------
    detrend_poly
    """
    import numpy as np

    if isinstance(da, xr.DataArray):
        x = xr.DataArray(np.arange(da[dim].size), dims=[dim]).assign_coords(**{dim: da[dim]})

        coef = da.assign_coords({dim: x}).polyfit(dim, order).polyfit_coefficients

        X = xr.concat([x**p for p in range(coef.degree.size)], "degree").assign_coords(
            degree=range(coef.degree.size)
        )

        trend = (coef * X).sum("degree").transpose(*da.dims)
        return trend

    elif isinstance(da, xr.Dataset):
        out = xr.Dataset()
        for key in da:
            if verbose:
                print(key, end=", ")
            out[key] = trend_poly(da[key], order=order)
        return out

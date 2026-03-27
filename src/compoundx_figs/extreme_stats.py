import numpy as np
import xarray as xr
from loguru import logger


def calc_severity_sum_max(intensity: xr.DataArray, mask):
    logger.info(
        f"Calculating severities for {intensity.name} using max of event severities"
    )
    intensity = intensity.compute()
    return _event_based_stats_2d_agg(
        intensity.where(mask),
        intra_extreme_func=np.nansum,
        inter_extreme_func=np.nanmax,
    )


def calc_intensity_mean_max(intensity: xr.DataArray, mask):
    intensity = intensity.compute()
    logger.info(
        f"Calculating intensities for {intensity.name} using average of event maxima"
    )
    return _event_based_stats_2d_agg(
        intensity.where(mask),
        intra_extreme_func=np.nanmax,
        inter_extreme_func=np.nanmean,
    )


def calc_intensity_ann_max(intensity: xr.DataArray, mask):
    intensity = intensity.compute()
    logger.info(
        f"Calculating intensities for {intensity.name} using average of annual maxima"
    )
    return intensity.where(mask).resample(time="1YS").max().mean("time")


def calc_severity_ann_max(intensity: xr.DataArray, mask):
    intensity = intensity.compute()
    logger.info(
        f"Calculating severities for {intensity.name} using average of annual sums"
    )
    return (
        intensity.where(mask)
        .resample(time="1YS")
        .sum()
        .mean("time")
        .where(lambda x: x != 0)
    )


def calc_duration_ann_avg(mask: xr.DataArray):
    mask = mask.compute()
    logger.info("Calculating durations using average of annual durations")
    return (
        mask.chunk({"lat": 90, "lon": 90})
        .resample(time="1YS")
        .sum()
        .where(lambda x: x > 0)
        .mean("time")
        # .rolling(lat=3, lon=3, min_periods=2, center=True).mean()
        .compute()
    )


def calc_duration(mask):
    mask = mask.compute()
    logger.info("Calculating durations using average of event durations")
    n_events = (mask.astype(int).diff("time") > 0).sum("time")
    n_months = mask.astype(int).sum("time")
    duration = n_months / n_events
    return duration


def _event_aggregator(a, inter_event_agg_func=np.max, intra_event_agg_func=np.sum):
    """
    Calculates the event-based statistics over a single dimension.
    """

    def split_clumps_by_nan(a):
        masked = np.ma.masked_invalid(a)
        indicies = np.ma.clump_unmasked(masked)
        list_of_clumps = [a[s] for s in indicies]
        return list_of_clumps

    def aggregate_clumps(clumps, func=np.sum):
        clump_aggrates = np.array([func(clump) for clump in clumps])
        return clump_aggrates

    clumps = split_clumps_by_nan(a)
    severity = aggregate_clumps(clumps, func=intra_event_agg_func)
    aggregated_over_events = inter_event_agg_func(severity)
    return aggregated_over_events


def quantile_95(x):
    """returns the 95th percentile of the data - does not work with nans"""
    return np.quantile(x, 0.95)


def _event_based_stats_2d_agg(
    da,
    dim="time",
    intra_extreme_func=np.sum,
    inter_extreme_func=quantile_95,
):
    """
    Calculates event-based statistics and aggregates over the first
    dimension (presumably time).

    Can be used to calculate the 95th % of severity [default] or intensity.
    Extremes are defined as continuous values over the first dimension
    (separated by NaNs). For intensity, the intra_extreme_func should be
    mean/max/percentile.

    Parameters
    ----------
    da: xr.DataArray
        A masked array of intensity - if severity and intensity stats want
        to be calculated. The masked areas are non-extreme.
    intra_extreme_func: callable
        Applied within an extreme event. This function must operate over
        a single dimension and aggregate to a single value. It is not
        recommended to use a lambda function since the function name is
        not intelligible.
    inter_extreme_func: callable
        Applied between extreme events to aggregate over the first dimension
        in the dataarray. The function must operate over a single dimension
        and aggregate to a single value.

    Returns
    -------
    xr.DataArray:
        A 2D DataArray that has been aggregated over the first dimension
        (e.g. `time`). The output DataArray will have two new dimensions
        that represent the intra- and inter-extreme aggregating functions.

    Note
    ----
    This was tested on a small dataset (468, 180, 360) and might not work
    on larger datasets.
    """

    # first get the dimensions
    dims = list(da.dims)
    other_dims = dims.copy()
    other_dims.remove(dim)

    da = da.transpose(*([dim] + other_dims))

    # we have to remove the nans
    mask = da.notnull().any("time").values.flatten()

    # the dataarray is unraveled on the first dim
    # transposed so that we iterate over the stacked dims
    arr = da.values.reshape([da[dim].size, -1]).T
    assert mask.size == arr.shape[0]
    placeholder = np.ndarray(mask.size) * np.nan

    func = _event_aggregator
    results = [func(s, inter_extreme_func, intra_extreme_func) for s in arr[mask]]
    # place the results in our placeholder that is not masked
    placeholder[mask] = np.array(results)

    # place the results in a data array and add coords/dims
    dims = dims[1:]
    results = xr.DataArray(
        data=placeholder.reshape(*da.shape[1:]),
        coords={k: da.coords[k] for k in dims},
        dims=dims,
    )
    # add coordinates that show the aggregation functions
    # we choose coordinates over attributes as these are
    # shown in xarray plots making it immediately clear what
    # the results show
    results = results.assign_coords(
        intra_event_func=intra_extreme_func.__name__,
        inter_event_func=inter_extreme_func.__name__,
    )

    return results

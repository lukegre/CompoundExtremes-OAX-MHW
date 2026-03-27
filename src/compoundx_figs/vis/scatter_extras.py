import matplotlib.pyplot as plt
import numpy as np
from matplotlib.axes import Axes
from matplotlib.collections import PathCollection
from matplotlib.colorbar import Colorbar


def scatter_x_distribution(ax: Axes, **kwargs):

    collection = get_scatter_collection(ax)
    data = _get_scatter_x_data(collection)

    x, y = _get_distribution(data)

    ax.set_zorder(1)
    ax.set_facecolor("none")

    ax2 = plt.twinx(ax)
    ax2.set_zorder(0)
    ax2.set_facecolor("none")

    props = {"color": "grey", "lw": 5, "zorder": -1, "alpha": 0.5} | kwargs
    ax2.plot(x, y, **props)

    ax2.spines["right"].set_visible(True)
    ax2.spines["right"].set_color("grey")
    ax2.yaxis.tick_right()

    return ax2


def buffer_axis_limits(ax: Axes, which="x", scaler=0.05):
    lims = ax.get_xlim() if which == "x" else ax.get_ylim()
    lims = np.asarray(lims).tolist()

    scale = (lims[1] - lims[0]) * scaler
    lim0 = float(lims[0] - scale)
    lim1 = float(lims[1] + scale)

    if which == "x":
        ax.set_xlim(lim0, lim1)
    else:
        ax.set_ylim(lim0, lim1)


def _get_scatter_x_data(collection: PathCollection):
    data: np.ma.MaskedArray = collection.get_offsets()[:, 0]
    data = data.data[~data.mask]
    return data


def _get_distribution(data):
    from scipy.stats.distributions import genextreme

    dmax = data.max()

    dist = genextreme.fit(data)
    x = np.linspace(1, dmax, 100)
    y = genextreme.pdf(x, *dist)

    return x, y


def scatter_colorbar_distribution(ax: Axes, bins=None) -> Colorbar:
    collection = get_scatter_collection(ax)
    data = get_scatter_colors(collection)

    if bins is None:
        bins = _make_bins_from_collection(collection)
    centers = np.convolve(bins, [0.5, 0.5], mode="valid")
    percent = _make_bin_percent(bins, data)

    cbar = plt.colorbar(
        collection,
        ax=ax,
        location="top",
        aspect=30,
        pad=0.01,
        extendfrac=0.01,
        extend="max",
        ticks=bins[:-1],
    )

    vmin, vmax = collection.get_clim()
    for x_colour, pct in zip(centers, percent):
        pct = _round_tick_value(pct)
        c = _get_text_color(x_colour, vmin, vmax)
        cbar.ax.text(x_colour, 0.5, f"{pct}%", ha="center", va="center", color=c)

    def set_label_right_yaxis(text, x=0.02, y=0.5, **kwargs):
        props = dict(ha="left", va="center", color="k")
        props.update(kwargs)
        brange = bins.max() - bins.min()
        return cbar.ax.text(bins[-1] + brange * x, y, text, **props)

    cbar.set_secondary_label = set_label_right_yaxis

    return cbar


def _make_bin_percent(bins: np.ndarray, data: np.ndarray) -> np.ndarray:
    bins = np.asarray(bins * 1)  # create a copy to avoid modifying the original
    bins[-1] = data.max() + 1
    counts = np.bincount(np.digitize(data, bins, right=True))[1:]
    percent = counts / counts.sum() * 100

    assert len(percent) == len(bins) - 1, (
        "Percent array should have one less element than bins, "
        f"but got {len(percent)} and {len(bins)}"
    )

    return percent


def _make_bins_from_collection(collection: PathCollection):
    vmin, vmax = collection.get_clim()
    cmap = collection.get_cmap()
    N = cmap.N  # type: ignore
    bins = np.linspace(vmin, vmax, N + 1)
    return bins


def _round_tick_value(value):
    if value < 1:
        return round(value, 2)
    elif value < 10:
        return round(value, 1)
    else:
        return round(value)


def _get_text_color(value, vmin, vmax, c0="k", c1="w"):
    if value < (vmin + vmax) / 2:
        return c0
    else:
        return c1


def get_scatter_colors(collection: PathCollection):
    data = collection.get_array().reshape(-1)  # get the colors of the points
    data = data[~np.isnan(data)]  # remove NaN values
    return data


def get_scatter_collection(ax: plt.Axes):
    for collection in ax.collections:
        if isinstance(collection, PathCollection):
            return collection
    raise ValueError("No scatter collection found in the axes")

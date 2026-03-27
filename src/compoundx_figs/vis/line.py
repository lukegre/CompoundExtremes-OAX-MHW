from typing import Callable

import numpy as np
import xarray as xr
from matplotlib.axes import Axes
from matplotlib.axes._secondary_axes import SecondaryAxis
from matplotlib.axis import Axis

from .utils import set_props


def smooth(da: xr.DataArray, w: int = 12) -> xr.DataArray:
    return da.rolling(time=w, center=True).mean().rolling_exp(time=7).mean()


ArrayLike = np.ndarray | list
AxesLike = Axes | SecondaryAxis


def add_secondary_yaxis_with_custom_values(
    ax: Axes,
    color="#aaaaaa",
    ticks: ArrayLike | None = None,
    tick_inverter: Callable | None = None,
):
    ax_second: Axes = ax.secondary_yaxis("right")  # type: ignore
    spine_props = {"visible": True, "linewidth": 0.5, "color": color}
    set_props(ax_second.spines["right"], **spine_props)
    ax_second.tick_params(axis="y", colors=color)

    if ticks is not None and tick_inverter is not None:
        custom_tick_values(ax_second.yaxis, ticks, tick_inverter)

    return ax_second


def custom_tick_values(
    axis: Axis, ticks: ArrayLike, tick_inverter: Callable, label: str | None = None, **label_kwargs
):
    """
    Set custom tick values on axis that don't match the data coordinates

    This is useful when the secondary axis shares the same data, but
    may be useful to show in different units.
    e.g., showing area in both million km^2 and percentage of ocean area.

    Parameters
    ----------
    axis : matplotlib.axis.Axis
        The axis on which to set custom tick values.
    ticks : array-like
        The tick values to display.
    tick_inverter : callable
        A function that converts the tick values to the axis coordinates.
    label : str, optional
        The label for the axis, by default None.
    label_kwargs : dict
        Additional keyword arguments for the axis label, passed to `set_label_text`.
    """
    ticks = np.asarray(ticks)
    ticks_right = tick_inverter(ticks)
    tick_labels = [f"{t:g}" for t in ticks]
    axis.set_ticks(ticks_right)
    axis.set_ticklabels(tick_labels)  # type: ignore

    if label is not None:
        axis.set_label_text(label, **label_kwargs)


def set_fig_ylabel(axs: dict[str, Axes] | list[Axes], labels: str, x=-0.01, y=0.5, **kwargs):
    props = {"rotation": 90, "va": "center", "ha": "center", "zorder": 100}

    axs = list(axs.values()) if isinstance(axs, dict) else axs
    if x > 0.5:
        props["rotation"] = -90

    upper_y = max(ax.get_position().y1 for ax in axs)
    lower_y = min(ax.get_position().y0 for ax in axs)
    y = lower_y + y * (upper_y - lower_y)
    x = axs[0].get_position().x0 + x

    fig = axs[0].get_figure()

    props |= kwargs
    fig.text(x, y, labels, **props)

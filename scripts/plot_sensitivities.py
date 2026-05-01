import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
import xarray as xr

import compoundx_figs as cxf

plt.rcParams["mathtext.rm"] = "rm"
plt.rcParams["mathtext.fontset"] = "dejavuserif"

ROOT = cxf.get_project_root()

COLORS = [
    "#1f77b4",
    "#ff7f0e",
    "#2ca02c",
    "#d62728",
    "#9467bd",
    "#8c564b",
    "#e377c2",
    "#7f7f7f",
    "#bcbd22",
    "#17becf",
]
DEFAULT_VIOLIN_PROPS = {
    "x": "Threshold percentile",
    "split": True,
    "inner": "quart",
    "gap": 0.1,
}
VIOLINPLOT_Y_KEYS = [
    "duration_2sigma_mon",
    "area_max_Mkm2",
    "oax_intensity_p95",
    "cex_intensity_norm_p95",
]


def main() -> tuple[plt.Figure, plt.Figure]:
    keys = VIOLINPLOT_Y_KEYS
    colors = COLORS

    ds = open_data()

    with color_context(colors[:2]):  # first, color by polynomial order
        hue = "Polynomial order"
        suptitle_text = (
            "Distributions of 12 x 500 most extreme events for CMEMS and ETHZ\n"
            "showing the impact of threshold percentile (x-axis) and polynomial order (color)"
        )
        fig_hue_polyorder, axs = plot_violinplots_2x2(
            ds, keys, suptitle_text=suptitle_text, hue=hue
        )
        axs["d"].legend(ncol=2, title=hue, loc=0, edgecolor="none")

    with color_context(colors[2:5:2][::-1]):
        hue = "Dataset"
        suptitle_text = (
            "Distributions of 12 x 500 most extreme events for CMEMS and ETHZ\n"
            "showing the impact of threshold percentile (x-axis) and dataset (color)"
        )
        fig_hue_dataset, axs = plot_violinplots_2x2(ds, keys, suptitle_text=suptitle_text, hue=hue)
        axs["d"].legend(ncol=1, title=hue, loc=0, edgecolor="none")
    return fig_hue_polyorder, fig_hue_dataset


def open_data():
    fname = str(ROOT / "data/v2025/sensitivities/cexTH_stats_for_sensitivities.nc")
    return xr.open_dataset(fname)


def get_pretty_names():

    Q95 = r"^{\ Q95}"
    I = r"\it{I}"
    In = r"\it{\widetilde{I}}"
    MHW = r"_{\it{\,MHW}}"
    OAX = r"_{\it{\,OAX}}"

    pretty_names_metrics = {
        "duration_2sigma_mon": "Duration Q$_{97.5}$ [months]",
        "mhw_intensity_p95": rf"${I}{MHW}{Q95}$ [°C]",
        "oax_intensity_p95": rf"${I}{OAX}{Q95}$ [nmol kg$^{{{-1}}}$]",
        "mhw_intensity_norm_p95": rf"${In}{MHW}{Q95}$",
        "oax_intensity_norm_p95": rf"${In}{OAX}{Q95}$",
        "cex_intensity_norm_p95": rf"${In}{OAX}{Q95}$",
        "area_max_km2": "Max area cover [km$^2$]",
        "area_max_Mkm2": "Max area cover [Mkm$^2$]",
    }

    return pretty_names_metrics


def get_metric_data(ds, metric_name) -> pd.Series:
    key = metric_name

    ser = ds.sel(metric=key).stats.rename(key).to_series()
    return ser


def plot_violin_metrics(ser, ylims_Q: tuple[float, float] = (0, 0.975), **kwargs):
    default_props = DEFAULT_VIOLIN_PROPS

    key = ser.name
    df = ser.reset_index()

    if "ax" not in kwargs:
        kwargs["ax"] = plt.axes()

    ylim = df[key].quantile(ylims_Q)
    df[key] = df[key].clip(*ylim)

    props = default_props | {"data": df, "y": key} | kwargs
    ax = sns.violinplot(**props)

    y0 = max(0, ylim[0])
    ax.set_ylim(y0, None)

    pretty_names_metrics = get_pretty_names()
    ax.set_ylabel(pretty_names_metrics[key], size="medium")

    return ax


def plot_violinplots_2x2(
    ds: xr.Dataset, keys: list[str], legend_subplot: str = "d", suptitle_text="", **kwargs
) -> tuple:
    fig, axs = plt.subplot_mosaic("ab\ncd", figsize=(8, 5), sharex=True)
    pretty_names = get_pretty_names()

    for key, subplot_label in zip(keys, axs, strict=False):
        ax = axs[subplot_label]
        df = get_metric_data(ds, key)
        draw_legend = True if subplot_label == legend_subplot else False
        plot_violin_metrics(df, ax=ax, legend=draw_legend, **kwargs)

        pretty_name = pretty_names[key].split("[")[0]
        subplot_label = f"{ax.get_label()}) {pretty_name}"
        ax.set_title(subplot_label, loc="left")

    fig.tight_layout()

    if suptitle_text:
        suptitle_x = axs["a"].get_position().x0
        suptitle_y = axs["a"].get_position().y1 + 0.07
        fig.suptitle(suptitle_text, x=suptitle_x, y=suptitle_y, ha="left", va="bottom", weight=1)

    return fig, axs


def color_context(colors):
    import matplotlib.pyplot as plt
    from cycler import cycler

    custom_cycler = cycler(color=colors)

    return plt.rc_context({"axes.prop_cycle": custom_cycler})


def process_cex_nc(ds: xr.Dataset) -> xr.Dataset:
    import re

    keep_vars = ["stats"]
    fname = ds.encoding["source"]

    attrs = {
        "Dataset": re.findall("CMEMS|ETHZ", fname),
        "Baseline": re.findall("shift|fixed", fname),
        "Polynomial order": re.findall("poly([12])", fname),
        "Threshold percentile": [ds["quantile"].compute().item() * 100],
    }

    ds = ds[keep_vars].reset_coords(drop=True).expand_dims(attrs)

    return ds

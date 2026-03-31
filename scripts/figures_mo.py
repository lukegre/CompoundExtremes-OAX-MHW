# ruff: noqa: E501
# fmt: off

import marimo

__generated_with = "0.21.1"
app = marimo.App(width="full")

with app.setup:
    import marimo as mo

    import pathlib
    import warnings
    from typing import Any, Literal

    import matplotlib.pyplot as plt
    import numpy as np
    import pandas as pd
    import plot_extreme_event_drivers as peed
    import scipy.stats.distributions as dists
    import seaborn as sns
    import xarray as xr
    from cartopy import crs, feature
    from dask.diagnostics.progress import ProgressBar
    from dataclasses import dataclass
    from dataclasses import field as dataclass_field
    from scipy.ndimage import label, binary_dilation

    import compoundx_figs as cxf
    from compoundx_figs import vis
    import plot_global_extreme_drivers as ged
    import plot_extreme_event_drivers as eed

    npdt = np.datetime64

    sns.set_palette("colorblind", n_colors=4)
    root = cxf.get_project_root()

    plt.style.use(root / "scripts/plotting.mplstyle")


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    # Load Data
    """)
    return


@app.cell
def load_data():
    data = cxf.Datasets.from_yaml(root / "data/sources.yaml", with_cache=True)
    ds_spatial_stats: xr.Dataset = xr.open_zarr(root / "data/derived/spatial_stats.zarr")
    df_event_stats = pd.read_csv(root / "data/derived/event_stats.csv", index_col=0).assign(year_start=lambda x: x.year_start_decimal // 1)
    drivers = ged.calc_drivers(data)
    return data, df_event_stats, drivers, ds_spatial_stats


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    # Figure 1
    """)
    return


@app.cell
def _():
    @dataclass
    class ExtremeTimeseriesData:
        mhw: pd.DataFrame
        oax: pd.DataFrame
        cex: pd.Series
        other: dict[str, Any] = dataclass_field(default_factory=dict)


    def get_timeseries_exremes(mhw: xr.Dataset, oax: xr.Dataset, cex: xr.Dataset, **sel: Any) -> ExtremeTimeseriesData:

        def calc_extreme_cat(df):
            out = pd.DataFrame(
                dict(
                    data=df.data,
                    scaling=df.threshold - df.climatology,
                    threshold=df.threshold,
                    base=df.climatology,
                    normed=df.intensity_norm,
                )
            )

            out["cat1"] = out.base + out.scaling * 1
            out["cat2"] = out.base + out.scaling * 2
            out["cat3"] = out.base + out.scaling * 3

            out = out.set_index(df.to_dataframe().index)

            return out

        keys = ["data", "threshold", "climatology", "intensity_norm"]
        y1_mhw: xr.Dataset = mhw[keys].sel(**sel).resample(time="1D").interpolate()
        y2_oax: xr.Dataset = oax[keys].sel(**sel).resample(time="1D").interpolate()
        y3_cex: xr.DataArray = (y1_mhw.intensity_norm**2 + y2_oax.intensity_norm**2) ** 0.5

        return ExtremeTimeseriesData(mhw=calc_extreme_cat(y1_mhw), oax=calc_extreme_cat(y2_oax), cex=y3_cex.to_series())

    return ExtremeTimeseriesData, get_timeseries_exremes


@app.cell
def _(ExtremeTimeseriesData, data, get_timeseries_exremes):
    if "collapse_data_prep":
        ts_extremes = get_timeseries_exremes(data.mhw, data.oax, data.cex, lat=46.5, lon=-133.5, time=slice("2013-09", "2016-01"))

        ts = ExtremeTimeseriesData(
            mhw=ts_extremes.mhw.rolling(window=7, center=True, min_periods=1).mean(),
            oax=ts_extremes.oax.rolling(window=7, center=True, min_periods=1).mean(),
            cex=ts_extremes.cex.rolling(window=7, center=True, min_periods=1).mean(),
        )
        ts.cex = ts.cex.where((ts.mhw.normed > 1) & (ts.oax.normed > 1))
        ts.other["cex_clipped"] = ts.cex.where((ts.mhw.normed > 0) & (ts.oax.normed > 0)).fillna(0)

    if "collapse_figure_layout":
        fig1, axs1 = plt.subplot_mosaic(
            "\n".join("aaabbbccddee"),
            figsize=(5.2, 6),
            sharex=True,
            sharey=False,
            gridspec_kw=dict(left=0.1, right=0.95, top=0.98, bottom=0.08, hspace=0.5),
        )

        axs1_fill_props = dict(interpolate=True)

    if "collapse_plot_MHW":
        ts.mhw.data.plot(ax=axs1["a"], c="C1", lw=1.5)
        ts.mhw.cat1.plot(ax=axs1["a"], c="k", lw=1.5)
        ts.mhw.cat2.plot(ax=axs1["a"], c="0.5", lw=0.5)
        ts.mhw.cat3.plot(ax=axs1["a"], c="0.8", lw=0.5)
        ts.mhw.normed.plot(ax=axs1["c"], c="C1", lw=1.5)
        ts.mhw.normed.plot(ax=axs1["c"], c="k", lw=1.5, alpha=0.2)

        mhw_gt_cat1 = ts.mhw.data > ts.mhw.cat1
        axs1_fill_props_mhw = axs1_fill_props | dict(color="C1")
        axs1["a"].fill_between(ts.mhw.index, ts.mhw.data, ts.mhw.cat1, where=mhw_gt_cat1, **axs1_fill_props_mhw)
        axs1["c"].fill_between(ts.mhw.index, ts.mhw.normed, 1, where=mhw_gt_cat1, **axs1_fill_props_mhw)

    if "collapse_plot_OAX":
        ts.oax.data.plot(ax=axs1["b"], c="C0", lw=1.5)
        ts.oax.cat1.plot(ax=axs1["b"], c="k", lw=1.5)
        ts.oax.cat2.plot(ax=axs1["b"], c="0.5", lw=0.5)
        ts.oax.cat3.plot(ax=axs1["b"], c="0.8", lw=0.5)
        ts.oax.normed.plot(ax=axs1["d"], c="C0", lw=1.5)
        ts.oax.normed.plot(ax=axs1["d"], c="k", lw=1.5, alpha=0.2)

        oax_gt_cat1 = ts.oax.data > ts.oax.cat1
        axs1_fill_props_oax = axs1_fill_props | dict(color="C0")
        axs1["b"].fill_between(ts.oax.index, ts.oax.data, ts.oax.cat1, where=oax_gt_cat1, **axs1_fill_props_oax)
        axs1["d"].fill_between(ts.oax.index, ts.oax.normed, 1, where=oax_gt_cat1, **axs1_fill_props_oax)

    if "collapse_plot_CEX":
        axs1["e"].fill_between(ts.cex.index, ts.cex, 1, color="C2", interpolate=True, alpha=0.9)

        for _i in ["c", "d", "e"]:
            ax = axs1[_i]
            _y0, _y1 = 0, 3.5
            ax.set_ylim(_y0, _y1)
            ax.axhline(1, c="k", lw=0.5)
            ax.fill_between(
                ts.cex.index,
                _y0,
                _y1,
                where=ts.cex.notnull(),
                interpolate=True,
                color="0.95",
                zorder=0,
                clip_on=False,
            )
            ax.set_yticks([1, 2, 3])

    if "collapse_labelling":
        axs1["a"].set_ylabel("Temperature (°C)")
        axs1["b"].set_ylabel(r"[H$^+$] (nmol/kg)")
        axs1["d"].set_ylabel(r"Normalized intensities ($\widetilde{I}\,$)")
        axs1["e"].set_xlabel("")

        vis.number_subplots(
            axs1.values(),
            [
                r"(a) Temperature",
                r"(b) [H$^{+}$]",
                r"(c) MHW",
                r"(d) OAX",
                r"(e) OAX$\cap$MHW",
            ],
        )

    if "collapse_save_figure":
        fig1.savefig(root / "figures/figure1_schematic_w5.2.png", dpi=300, transparent=True)
        fig1.savefig(root / "figures/figure1_schematic_w5.2.pdf")

    fig1
    return


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    # Figure 2
    """)
    return


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    ## Figure 2 top
    """)
    return


@app.cell
def _(data, ds_spatial_stats: xr.Dataset):
    if "collapse_figure_layout":
        fig2_top = plt.figure(figsize=[7.5, 5.1], dpi=100)
        props_imshow = {
            "cbar_kwargs": {"orientation": "horizontal", "shrink": 0.6},
            "proj": crs.EqualEarth(-155),
        }

    if "collapse_plotting":
        img2_top = [
            ds_spatial_stats.mhw_I.geo.imshow(pos=221, **props_imshow, levels=np.arange(0.2, 1.3, 0.2)),
            ds_spatial_stats.mhw_D.geo.imshow(pos=222, **props_imshow, levels=np.arange(1, 4.1, 0.5)),
            ds_spatial_stats.oax_I.geo.imshow(pos=223, **props_imshow, levels=np.arange(0.03, 0.09, 0.01)),
            ds_spatial_stats.oax_D.geo.imshow(pos=224, **props_imshow, levels=np.arange(1, 4.1, 0.5)),
        ]
        [cxf.vis.plot_contours(data.masks.regions_HL, img.axes) for img in img2_top]

    if "collapse_labels":
        props_text = dict(rotation=90, weight="bold", ha="center", va="center", zorder=10)
        img2_top[0].axes.text(-0.03, 0.5, "MHW", transform=img2_top[0].axes.transAxes, **props_text)
        img2_top[2].axes.text(-0.03, 0.5, "OAX", transform=img2_top[2].axes.transAxes, **props_text)
        cxf.vis.number_subplots([img.axes for img in img2_top], space=0.02)

        for _img in img2_top:
            _ax = _img.axes
            _ax.spines["top"].set_visible(False)

    if "collapse_saving":
        plt.subplots_adjust(left=0.05, right=0.98, top=0.99, bottom=0.1)
        fig2_top.savefig(root / "figures/figure2_top_w7.5.png", dpi=300, transparent=True)
    fig2_top
    return (fig2_top,)


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    ## Figure 2 bottom
    """)
    return


@app.cell
def _(data):
    if "collapse_data_prep":
        # Figure 2 e-f: area of HL and LL regions, and area of MHW and OAX in those regions
        mask_HL = (data.masks.regions_HL == 1) & data.masks.ice_mask
        mask_LL = (data.masks.regions_HL == 2) & data.masks.ice_mask
        area_HL_Mkm2 = (data.masks.area * mask_HL).sum().compute() / 1e12
        area_LL_Mkm2 = (data.masks.area * mask_LL).sum().compute() / 1e12

        def compute_area(da, mask):
            return data.masks.area.where(da.mask & mask).sum(["lat", "lon"]).compute().pipe(cxf.vis.line.smooth, w=12) / 1e12

        mhw_HL_area = compute_area(data.mhw, mask_HL)
        mhw_LL_area = compute_area(data.mhw, mask_LL)
        oax_HL_area = compute_area(data.oax, mask_HL)
        oax_LL_area = compute_area(data.oax, mask_LL)
        # for Figure 3
        cex_HL_area = compute_area(data.cex, mask_HL)
        cex_LL_area = compute_area(data.cex, mask_LL)

        def hl_pct_to_area(x):
            return x / 100 * area_HL_Mkm2.values

        def ll_pct_to_area(x):
            return x / 100 * area_LL_Mkm2.values


    if "collapse_figure_layout":
        fig2_bot, axs2_bot = plt.subplot_mosaic("e\nf\nf", figsize=(7.5, 2.5), sharex=True)
        fig2_bot.subplots_adjust(hspace=0.2, left=0.1, right=0.92, top=0.98, bottom=0.15)

    if "collapse_plot_data":
        with plt.rc_context({"lines.linewidth": 4}):
            mhw_HL_area.plot(ax=axs2_bot["e"], label="MHW", c="C1")
            oax_HL_area.plot(ax=axs2_bot["e"], label="OAX", c="C0")
            mhw_LL_area.plot(ax=axs2_bot["f"], label="MHW", c="C1")
            oax_LL_area.plot(ax=axs2_bot["f"], label="OAX", c="C0")
            _x: Any = data.masks.el_nino_mask.time
            _bar_props: dict[str, Any] = dict(lw=0, zorder=0)
            axs2_bot["f"].fill_between(_x, data.masks.el_nino_mask * 55, color="0.75", **_bar_props)
            axs2_bot["f"].fill_between(_x, data.masks.la_nina_mask * 55, color="0.93", **_bar_props)

    if "collapse_secondary_axes_ticks":
        axs2_bot_2nd: dict[str, plt.Axes] = {}
        axs2_bot_2nd["e"] = vis.line.add_secondary_yaxis_with_custom_values(axs2_bot["e"], ticks=[10, 20], tick_inverter=hl_pct_to_area)
        axs2_bot_2nd["f"] = vis.line.add_secondary_yaxis_with_custom_values(axs2_bot["f"], ticks=[5, 10, 15, 20], tick_inverter=ll_pct_to_area)

    if "collapse_legend_labels":
        text_props: dict[str, Any] = {
            "weight": 1000,
            "size": "large",
            "ha": "center",
            "family": "arial black",
        }
        _text_x = pd.Timestamp("2006")
        axs2_bot["f"].text(_text_x, 45, "MHW", c="C1", **text_props)
        axs2_bot["f"].text(_text_x, 35, "OAX", c="C0", **text_props)

    if "collapse_axes_ticks":
        axs2_bot["f"].set_xlim(pd.Timestamp("1982-01-01"), pd.Timestamp("2025-01-01"))
        axs2_bot["e"].set_ylim(0, 20)
        axs2_bot["f"].set_ylim(0, 60)
        axs2_bot["f"].set_yticks([0, 15, 30, 45, 60])
        axs2_bot["f"].set_yticklabels(["0", "15", "30", "45", ""])
        axs2_bot["f"].set_xticks(pd.date_range("1985-01-01", "2025-01-01", freq="5YS"))
        axs2_bot["f"].set_xticklabels(np.arange(1985, 2026, 5))

    if "collapse_axes_labels":
        vis.clear_labels(axs2_bot["e"])
        vis.clear_labels(axs2_bot["f"])
        vis.line.set_fig_ylabel(axs2_bot, "Extreme event area (10$^6$ km$^2$)", x=-0.05)
        vis.line.set_fig_ylabel(axs2_bot, "Area cover (%)", color="#aaaaaa", x=0.88)
        vis.number_subplots(
            axs2_bot.values(),
            ["(e) High latitudes", "(f) Mid-Low latitudes"],
            bbox=dict(facecolor="white", edgecolor="none", pad=2),
            space=0.04,
        )

    if "collapse_save_figure":
        # fig2_bot.savefig(root / "figures/figure2_bot_w7.5.pdf")
        # fig2_bot.savefig(root / "figures/figure2_bot_w7.5.png", dpi=300, transparent=True)
        ...

    fig2_bot
    return cex_HL_area, cex_LL_area, fig2_bot, hl_pct_to_area, ll_pct_to_area


@app.cell
def _(fig2_bot, fig2_top):
    _ = vis.utils.combine_figures_vertically(fig2_top, fig2_bot, "./figures/figure2_w7.5.png", dpi=300)
    return


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    # Figure 3
    """)
    return


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    ## Figure 3 top
    """)
    return


@app.cell
def _(data):
    if "collapse_data_prep":
        num_extremes = data.cex.mask.sum("time").compute()
        num_extremes_seasonal = data.cex.mask.groupby("time.season").sum("time").compute()
        num_extremes_smmmer_sh = num_extremes_seasonal.sel(season="DJF", lat=slice(-90, 0))
        num_extremes_smmmer_nh = num_extremes_seasonal.sel(season="JJA", lat=slice(0, 90))
        num_extremes_winter_sh = num_extremes_seasonal.sel(season="JJA", lat=slice(-90, 0))
        num_extremes_winter_nh = num_extremes_seasonal.sel(season="DJF", lat=slice(0, 90))
        num_extremes_summer = xr.concat([num_extremes_smmmer_sh, num_extremes_smmmer_nh], dim="lat", coords="all")
        num_extremes_winter = xr.concat([num_extremes_winter_sh, num_extremes_winter_nh], dim="lat", coords="all")
        quantile = 0.95
        expected_num_compound_extremes = (1 - quantile) ** 2 * data.cex.time.size
        num_years = np.unique(data.cex.time.dt.year).size

        def make_cbar_secondary_xaxis(img):
            return img.colorbar.ax.secondary_xaxis("top").xaxis

        def inverse_lmf(x):
            return x * expected_num_compound_extremes

        def inverse_freq(x):
            return x * num_years


    if "collapse_figure_layout":
        fig3_top, axs3 = plt.subplot_mosaic(
            "aa\naa\naa\nbc\nbc",
            figsize=(7.5, 6.8),
            subplot_kw={"projection": crs.EqualEarth(central_longitude=205)},
        )
        fig3_top.subplots_adjust(hspace=0.1)
        img3_top: dict[str, plt.Axes] = {}

    if "collapse_plot_maps":
        props = {
            "transform": crs.PlateCarree(),
            "cmap": "bone_r",
            "cbar_kwargs": {
                "pad": 0.13,
                "fraction": 0.1,
                "location": "bottom",
                "aspect": 20,
                "shrink": 0.45,
                "extendfrac": 0.05,
                "label": "Number of compound extremes",
            },
        }
        img3_top["top"] = num_extremes.plot.imshow(ax=axs3["a"], **props)

        props["cbar_kwargs"] |= {"shrink": 0.58, "pad": 0.03}
        img3_top["left"] = num_extremes_summer.plot.imshow(ax=axs3["b"], vmax=8, **props)
        img3_top["right"] = num_extremes_winter.plot.imshow(ax=axs3["c"], vmax=8, **props)

    if "collapse_add_map_features":
        [ax.add_feature(feature.LAND, facecolor="0.9", zorder=2) for ax in axs3.values()]
        [ax.coastlines(lw=0.5, color="k", zorder=3) for ax in axs3.values()]

    if "collapse_labels":
        [cxf.vis.clear_labels(ax) for ax in axs3.values()]
        img3_top["top"].axes.set_title("(a) Full period [1982 - 2020]", size="medium")
        img3_top["left"].axes.set_title("(b) Summer", x=0.3, ha="center", size="medium")
        img3_top["right"].axes.set_title("(c) Winter", x=0.7, ha="center", size="medium")

    if "collapse_colorbar_labels":
        expected_label = "$\\frac{\\text{Number of compound extremes}}{\\text{Expected number of compound extremes}}$"
        number_events = "Number of compound extremes"
        events_per_year = "Number of compound extremes per year"

        vis.line.custom_tick_values(
            axis=img3_top["top"].colorbar.ax.xaxis, ticks=[0, 5, 10, 15, 20], tick_inverter=inverse_lmf, label=expected_label, size="large"
        )
        vis.line.custom_tick_values(
            make_cbar_secondary_xaxis(img3_top["top"]),
            ticks=np.arange(0, 0.61, 0.1),
            tick_inverter=inverse_freq,
            label=events_per_year,
        )

    if "collapse_save_figure":
        fig3_top.savefig(root / "figures/figure3_top_w7.5.png", dpi=300, transparent=False)
        fig3_top.savefig(root / "figures/figure3_top_w7.5.pdf", dpi=300, transparent=False)
        ...
    fig3_top
    return (fig3_top,)


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    ## Figure 3 bottom
    """)
    return


@app.cell
def _(cex_HL_area, cex_LL_area, data, hl_pct_to_area, ll_pct_to_area):
    if "collapse_figure_layout":
        fig3_bot, axs3_bot = plt.subplot_mosaic("e\nf\nf", figsize=(7.5, 2.5), sharex=True)
        fig3_bot.subplots_adjust(hspace=0.2, left=0.1, right=0.93, top=0.98, bottom=0.15)

    if "collapse_plot_data":
        with plt.rc_context({"lines.linewidth": 4}):
            cex_HL_area.plot(ax=axs3_bot["e"], label="CEX", c="C2")
            cex_LL_area.plot(ax=axs3_bot["f"], label="CEX", c="C2")

            axs3_bot_x = data.masks.el_nino_mask.time
            ax3_bot_y1 = axs3_bot["f"].get_ylim()[1] * 0.95

            axs3_bot_bar_props: dict[str, Any] = dict(lw=0, zorder=0)
            axs3_bot["f"].fill_between(
                axs3_bot_x,
                data.masks.el_nino_mask * ax3_bot_y1,
                color="0.75",
                **axs3_bot_bar_props,
            )
            axs3_bot["f"].fill_between(
                axs3_bot_x,
                data.masks.la_nina_mask * ax3_bot_y1,
                color="0.93",
                **axs3_bot_bar_props,
            )

    if "collapse_secondary_axes_ticks":
        axs3_bot_2nd: dict[str, Any] = {}
        axs3_bot_2nd["e"] = vis.line.add_secondary_yaxis_with_custom_values(axs3_bot["e"], ticks=[1, 2], tick_inverter=hl_pct_to_area)
        axs3_bot_2nd["f"] = vis.line.add_secondary_yaxis_with_custom_values(axs3_bot["f"], ticks=[2, 4, 6], tick_inverter=ll_pct_to_area)

    if "collapse_legend_labels":
        axs3_bot_text_props: dict[str, Any] = {
            "weight": 1000,
            "size": "large",
            "ha": "center",
            "family": "arial black",
        }
        axs3_bot["f"].text(pd.Timestamp("2005"), 10, "CEX", c="C2", **axs3_bot_text_props)  # type: ignore

    if "collapse_axes_ticks":
        axs3_bot["f"].set_xlim(pd.Timestamp("1982-01-01"), pd.Timestamp("2025-01-01"))  # type: ignore
        axs3_bot["e"].set_ylim(0, 2.1)
        axs3_bot["f"].set_ylim(0, 18)
        axs3_bot["f"].set_yticks([0, 4, 8, 12, 16])
        axs3_bot["f"].set_xticks(pd.date_range("1985-01-01", "2025-01-01", freq="5YS"))
        axs3_bot["f"].set_xticklabels(np.arange(1985, 2026, 5))

    if "collapse_axes_labels":
        vis.clear_labels(axs3_bot["e"])
        vis.clear_labels(axs3_bot["f"])
        vis.line.set_fig_ylabel(axs3_bot, "Extreme event area (10$^6$ km$^2$)", x=-0.05)
        vis.line.set_fig_ylabel(axs3_bot, "Area cover (%)", color="#aaaaaa", x=0.88)
        vis.number_subplots(
            axs3_bot.values(),
            [
                "(d) High latitudes (seasonally stratified regions)",
                "(e) Mid-Low latitudes (permanently stratified regions)",
            ],
            bbox=dict(facecolor="white", edgecolor="none", pad=2),
            space=0.04,
        )

    if "collapse_save_figure":
        # fig3_bot.savefig(root / "figures/figure3_bot_w7.5.pdf")
        # fig3_bot.savefig(root / "figures/figure3_bot_w7.5.png", dpi=300, transparent=True)
        ...
    fig3_bot
    return (fig3_bot,)


@app.cell
def _(fig3_bot, fig3_top):
    _ = vis.utils.combine_figures_vertically(fig3_top, fig3_bot, "./figures/figure3_w7.5.png", dpi=300)
    return


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    # Figure 4
    """)
    return


@app.cell
def _(data, ds_spatial_stats: xr.Dataset):
    if "collapse_figure_layout":
        fig4 = plt.figure(figsize=[7.5, 5.3], dpi=100)
        fig4.subplots_adjust(left=0.05, right=0.95, top=0.95, bottom=0.1)

    if "collapse_plotting":
        props_fig4: dict[str, Any] = {
            "cbar_kwargs": {"orientation": "horizontal", "shrink": 0.6},
            "proj": crs.EqualEarth(-155),
        }
        img4: list[Any] = [
            ds_spatial_stats.cex_I.geo.imshow(pos=221, levels=6, **props_fig4),
            ds_spatial_stats.cex_D.geo.imshow(pos=222, levels=np.arange(0.5, 3.1, 0.5), vmin=0.5, **props_fig4),
            ds_spatial_stats.cex_mhw_I.geo.imshow(pos=223, levels=6, **props_fig4),
            ds_spatial_stats.cex_oax_I.geo.imshow(pos=224, levels=np.arange(0.03, 0.18, 0.03), **props_fig4),
        ]

        [cxf.vis.plot_contours(data.masks.regions_HL, img.axes) for img in img4]

    if "collapse_labels":
        cxf.vis.number_subplots([img.axes for img in img4], space=0.02)

    if "collapse_savefig":
        fig4.savefig(root / "figures/figure4_w7.5.png", dpi=300, transparent=True)
        ...
    fig4
    return


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    # Figure 5
    """)
    return


@app.function
def plot_distribution(
    y: np.ndarray | None = None,
    dist_func: dists.rv_continuous = dists.genextreme,
    bins=30,
    ax=None,
    annot=True,
    **hist_kwargs,
):
    if y is None:
        raise ValueError("y must be provided")

    args = dist_func.fit(y)
    dist = dist_func(*args)

    if ax is None:
        fig, ax = plt.subplots()

    hist_kwargs: dict[str, Any] = dict(density=True, color="k", lw=0) | hist_kwargs
    hist_kwargs["width"] = np.diff(bins).mean() * hist_kwargs.get("width", 1)
    ybin, xbin, _ = ax.hist(y, bins=bins, **hist_kwargs)

    x = np.linspace(xbin.min(), xbin.max(), 100)
    yhat = dist.pdf(np.convolve(xbin, [0.5] * 2, mode="valid"))
    yhat_plot = dist.pdf(x)
    ax.plot(x, yhat_plot)

    description = {
        "name": dist_func.__class__.__name__.replace("_gen", ""),
        "args": args,
        "rmse": ((ybin - yhat) ** 2).mean() ** 0.5,
        "mean": dist.stats(moments="m"),
        "var": dist.stats(moments="v"),
        "mode": x[yhat_plot.argmax()],
    }

    txt = ""
    for key, val in description.items():
        if isinstance(val, (float, np.ndarray)):
            txt += f"{key} = {val:.2f}\n"
        elif isinstance(val, (list, tuple)):
            val = [np.around(v, 2) for v in val]
            txt += f"{key} = {val}\n"
        else:
            txt += f"{key} = {val}\n"
    txt = txt.replace("[", "").replace("]", "")

    if annot:
        ax.text(0.95, 0.95, txt, ha="right", va="top", transform=ax.transAxes)

    if hasattr(y, "name"):
        ax.set_title(y.name)

    ax.description = description

    return ax


@app.cell
def _(df_event_stats):
    if "collapse_data_prep":
        from matplotlib.patches import Rectangle

        df_event_stats["area_max_mil"] = df_event_stats["area_max_km2"]

        big = (df_event_stats.area_max_mil > 2) & df_event_stats.loc_region.isin([2, 3, 4])
        sml = (df_event_stats.area_max_mil <= 2) & df_event_stats.loc_region.isin([2, 3, 4])

    if "collapse_figure_layout":
        fig5, axs5 = plt.subplots(2, 3, figsize=[7.5, 4.5], sharex=False)
        axs5 = axs5.T.flatten()

    if "collapse_plot_distributions":
        axs5_props: dict[str, Any] = dict(annot=False, dist_func=dists.genextreme)
        axs5[0] = plot_distribution(
            ax=axs5[0],
            bins=np.arange(0, 2.1, 0.1),
            **axs5_props,
            y=df_event_stats[sml | big].area_max_mil,
        )
        axs5[2] = plot_distribution(
            ax=axs5[2],
            bins=np.arange(1, 8, 0.25),
            **axs5_props,
            y=df_event_stats[sml].duration_2sigma_mon.where(lambda x: x != 1).dropna(),
        )
        axs5[4] = plot_distribution(
            ax=axs5[4],
            bins=np.arange(2, 4, 0.2),
            **axs5_props,
            y=df_event_stats[sml].cex_intensity_norm_p95,
        )

        axs5[1] = plot_distribution(
            ax=axs5[1],
            bins=np.arange(0, 9, 1),
            **axs5_props,
            y=df_event_stats[sml | big].area_max_mil,
        )
        axs5[3] = plot_distribution(
            ax=axs5[3],
            bins=np.arange(1, 8, 0.5),
            **axs5_props,
            y=df_event_stats[big].duration_2sigma_mon.where(lambda x: x != 1).dropna(),
        )
        axs5[5] = plot_distribution(
            ax=axs5[5],
            bins=np.arange(2, 4, 0.2),
            **axs5_props,
            y=df_event_stats[big].cex_intensity_norm_p95,
        )

    if "collapse_annotations":
        for i, a in enumerate(axs5):
            _d = a.description
            txt = r"GEV ($\mu, \sigma, \xi$)\n"
            txt += r"$\mu$" + f" = {_d['args'][1]:.2f}\n"
            txt += r"$\sigma$" + f" = {_d['args'][2]:.2f}\n"
            txt += r"$\xi$" + f" = {-_d['args'][0]:.2f}\n"  # notation of Scipy flips C

            txt += f"mode = {_d['mode']:.2f}\n"
            txt += f"mean = {_d['mean']:.2f}"
            a.text(0.98, 0.98, txt, transform=a.transAxes, fontsize=8, va="top", ha="right")

    if "collapse_axes_ticks":
        axs5[1].set_xticks([2, 4, 6, 8])
        axs5[1].set_ylim(0, 0.14)
        axs5[1].set_xlim(2, 8)
        axs5[2].set_xlim(1, 8)
        axs5[3].set_xlim(1, 8)
        axs5[4].set_xlim(2, 4)
        axs5[5].set_xlim(2, 4)

    if "collapse_axes_labels":
        [a.set_title("") for a in axs5]
        axs5[1].set_xlabel(r"Area (10$^6$ km$^2$)")
        axs5[3].set_xlabel(r"Duration (months)")
        axs5[5].set_xlabel(r"$\widetilde{I}^{\ Q95}_{\rm{OAX}\cap\rm{MHW}}\,$", size="large")

    if "collapse_line_and_bar_properties":
        axs5[0].get_lines()[0].set_color("C1")
        axs5[1].get_lines()[0].set_color("C1")
        axs5[1].get_lines()[0].set_linestyle("--")

        for a in axs5:
            [b.set_facecolor("0.78") for b in a.get_children()[:-1] if isinstance(b, Rectangle)]
            [b.set_linewidth(0.5) for b in a.get_children()[:-1] if isinstance(b, Rectangle)]

    if "collapse_labelling":
        # number subplots requires that this is run first
        fig5.tight_layout()

        axs5[0].set_ylabel(r"Small events dist.\n(Area < 2 million km$^2$)")
        axs5[1].set_ylabel(r"Large events dist.\n(Area $\geq$ 2 million km$^2$)")

        vis.number_subplots(axs5.reshape(-1, 2).T.flatten(), space=0.03)

    if "collapse_save_figure":
        fig5.savefig(root / "figures/figure5_distsGEV_w7.5.pdf", bbox_inches="tight")
    fig5
    return


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    # Figure 6
    """)
    return


@app.function
def plot_extreme_events_scatter(
    df: pd.DataFrame,
    ax: plt.Axes,
    x="duration_avg_mon",
    y="cex_intensity_norm_p95",
    c="area_max_km2",
    s="area_max_km2",
    cmap="cividis_r",
    highlight_index=None,
    n_colors=10,
    **kwargs,
) -> None:

    cmap = plt.cm.get_cmap(cmap, n_colors)

    _props = {
        "x": x,
        "y": y,
        "c": c,
        "s": s,
        "cmap": cmap,
        "vmin": 0,
        "vmax": cmap.N,
        "edgecolor": "k",
        "linewidth": 0.3,
        "colorbar": False,
    } | kwargs

    df_sorted = df.sort_values(_props["c"], ascending=False)
    df_sorted.plot.scatter(ax=ax, **_props)

    if highlight_index is not None:
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=UserWarning, message=".*colormapping.*")

            df_sorted_highlighted = df_sorted.loc[highlight_index]

            _props.update(linewidth=4, zorder=5, c="none", edgecolor="w")
            df_sorted_highlighted.plot.scatter(ax=ax, **_props)

            _props.update(linewidth=1.5, zorder=5, c="none", edgecolor="k")
            df_sorted_highlighted.plot.scatter(ax=ax, **_props)

    vis.scatter_extras.buffer_axis_limits(ax)


@app.cell
def _(data, df_event_stats):
    if "collapse_data_prep":
        fig6_chosen_events: list[dict[str, Any]] = [
            dict(idx=24, text="Madagascar\n(1987)", dx=0.3, dy=0.45, ha="center"),
            dict(idx=231, text="Mediterranean\nSea (2003)", dx=-0.4, dy=0.7, ha="center"),
            dict(idx=294, text="Western\nAustralia\n(2011)", dx=0, dy=0.6, ha="left"),
            dict(idx=330, text="The Blob (2015)", dx=-0, dy=1, ha="center"),
            dict(idx=352, text="South Pacific\n(2015)", dx=0.3, dy=-0.8, ha="center"),
            dict(idx=437, text="Barrier Reef\n(2022)", dx=-0.3, dy=-0.45, ha="center"),
            dict(idx=450, text="Atlantic\n(2023)", dx=-0.2, dy=1.0, ha="center"),
            # dict(idx=154, text="Northern \nEq. Pacific \n(1998)", dx=0.1, dy=0.5, ha="center"),
            # dict(idx=159, text="SE Asia\n(1998)", dx=0.2, dy=-0.5),
            # dict(idx=449, text="Indian Ocean\n(2023)", dx=0.3, dy=0.75, ha='left'),
            # dict(idx=463, text="Blob 2 (2019)", dx=0, dy=+0.5, ha="center"),
            # dict(idx=484, text="Kuriosho\nCurrent (2024)", dx=-0.7, dy=0.9, ha="right"),
        ]

        event_idxs: list[int] = [v["idx"] for v in fig6_chosen_events]

        most_extreme: xr.DataArray = data.cex.blobs.isin(event_idxs).compute()
        most_intense_avg: xr.DataArray = data.cex.intensity_norm.where(most_extreme & data.cex.mask).quantile(0.95, dim="time")
        most_extreme_contours: xr.DataArray = most_extreme.any("time").astype(int)

        _df_events = df_event_stats.assign(chosen=lambda x: x.index.isin(event_idxs))

    if "collapse_figure_layout":
        fig6 = plt.figure(figsize=(7, 8.3))
        axs6: list[plt.Axes] = [
            fig6.add_subplot(211),
            fig6.add_subplot(212, projection=crs.PlateCarree(205)),
        ]
        fig6.subplots_adjust(hspace=0.15)

    if "collapse_plot_scatter":
        plot_extreme_events_scatter(
            _df_events,
            c="area_max_mil",
            s="area_max_scl",
            x="duration_2sigma_mon_clipped",
            y="cex_intensity_norm_p95",
            highlight_index=event_idxs,
            cmap="cividis_r",
            ax=axs6[0],
        )

    if "collapse_scatter_annotations":

        def plot_arrow(idx, text, dx, dy, **kwargs):  # collapse_scatter_plotting
            y, _x = _df_events.loc[idx, ["cex_intensity_norm_p95", "duration_2sigma_mon_clipped"]]
            ty = y + dy
            tx = _x + dx
            _props = dict(
                size=9,
                va="center",
                ha="left",
                color="grey",
                zorder=0,
                arrowprops=dict(arrowstyle="-", lw=0.5, color="k"),
                bbox={"facecolor": "white", "alpha": 0.6, "lw": 0},
            )
            _props.update(kwargs)
            axs6[0].annotate(text, xy=(_x, y), xytext=(tx, ty), **_props)

        for arrow in fig6_chosen_events:
            plot_arrow(**arrow)

    if "collapse_plot_additional_features":
        ax2 = vis.scatter_extras.scatter_x_distribution(axs6[0])
        _cb = vis.scatter_extras.scatter_colorbar_distribution(axs6[0])
        _cb.set_label("Event area maximum (Mkm$^2$)")
        _cb.set_secondary_label("Distribution\nof event size", size="small")

    if "collapse_scatter_labelling":
        compound_intensity_q95 = "$\\widetilde{\\mathit{I}}^{\\ Q95}_{\\rm{OAX}\\cap\\rm{MHW}}$"
        axs6[0].set_ylabel(compound_intensity_q95, size=12)
        axs6[0].set_xlabel("Duration [$\\mu + 2\\sigma$] (months)")
        ax2.set_ylabel("Event duration PDF", color="#aaaaaa", va="top", loc="bottom")

    if "collapse_scatter_axes_ticks":
        axs6[0].set_ylim(1.7, 4.73)
        ax2.set_ylim(0, 0.8)
        ax2.set_yticks([])

    if "collapse_plot_map":
        axs6[1].coastlines(resolution="110m", color="k", lw=0.5, zorder=3)
        axs6[1].add_feature(feature.LAND.with_scale("110m"), facecolor="0.85", zorder=2)
        da = cxf.vis.fill_lon_gap(most_intense_avg)
        img = da.plot.contourf(
            ax=axs6[1],
            transform=crs.PlateCarree(),
            levels=np.arange(1.6, 4.7, 0.4),
            cmap="Greens",
            cbar_kwargs=dict(orientation="horizontal", shrink=1, aspect=30, fraction=0.06, pad=0.01),
        )

    if "collapse_map_contours":
        img.axes.contour(
            most_extreme_contours.lon,
            most_extreme_contours.lat,
            most_extreme_contours,
            transform=crs.PlateCarree(),
            levels=[0.5, 1.5],
            colors=["k"],
            linewidths=[0.5],
        )
        img.axes.set_title("")
        label_compound_intensity = "$\\widetilde{\\mathit{I}}^{\\ Q95}_{\\rm{OAX}\\cap\\rm{MHW}}$"
        img.colorbar.set_label(label_compound_intensity, size=12)

    if "collapse_map_annotations":
        bf: dict[str, Any] = dict(size=11, weight="bold", va="bottom", zorder=7)
        sf: dict[str, Any] = dict(size=7.5, va="top", zorder=7)

        _props: dict[str, Any] = dict(ha="right", transform=crs.PlateCarree())
        axs6[1].text(-155, 44, "again in 2019", size=sf["size"], **_props)
        axs6[1].text(-155, 34, "2015", size=13, weight="bold", **_props)
        axs6[1].text(-155, 32, "The Blob", style="italic", **sf, **_props)

        _props = dict(ha="left", transform=crs.PlateCarree())
        axs6[1].text(150, -1, "2022", **bf, **_props)
        axs6[1].text(150, -1, "     Great Barrier Reef", **sf, **_props)

        _props = dict(transform=crs.PlateCarree())
        axs6[1].text(-140, -40, "2015", ha="left", **bf, **_props)
        axs6[1].text(-140, -40, "South Pacific", ha="left", **sf, **_props)

        _props = dict(transform=crs.PlateCarree())
        axs6[1].text(50, -3, "1987", **bf, **_props)
        axs6[1].text(50, -3, "Madagascar", **sf, **_props)

        _props = dict(transform=crs.PlateCarree(), va="center")
        axs6[1].text(-20, -41, "2023 ", **bf | _props | {"ha": "right"})
        axs6[1].text(-20, -41, "Tropical\nAtlantic", **sf | _props | dict(ha="left"))

        _props = dict(transform=crs.PlateCarree(), va="center")
        axs6[1].text(120, -45, "2011 ", **bf | _props | dict(ha="right"))
        axs6[1].text(120, -45, "Western\nAustralia", **sf | _props | dict(ha="left"))

        _props = dict(transform=crs.PlateCarree())
        axs6[1].text(-8, 23, "2003", **bf, **_props)
        axs6[1].text(-8, 23, "MedSea", **sf, **_props)

    if "collapse_map_extent":
        axs6[1].set_extent([-180, 180, -90, 90], crs=crs.PlateCarree())  # type: ignore

    if "collapse_save_figure":
        fig6.savefig(root / "figures/figure6-with_annotations.pdf", bbox_inches="tight")
    fig6
    return event_idxs, fig6_chosen_events


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    ## Table with stats
    """)
    return


@app.cell
def _(
    df_event_stats,
    event_idxs: list[int],
    fig6_chosen_events: list[dict[str, Any]],
):
    if "collapse_data_prep":
        df_table = df_event_stats.loc[event_idxs].sort_index()

        df_table["year_start"] = 1982 + 1 / 12 + df_table.month_start_sice_198201 / 12
        df_table["year_end"] = df_table.year_start + df_table.duration_lagrangian_mon / 12

        year = df_table.year_start // 1
        doy = ((df_table.year_start % 1) * 365.25).astype(int) + 1
        df_table["time_start"] = pd.to_datetime(year.astype(str).str[:-1] + doy.astype(str), format="%Y.%j")
        df_table.loc[:, "time_end"] = df_table.time_start + df_table.duration_lagrangian_mon.astype(int).astype("timedelta64[M]").values


    def clean_up_text(text):
        import re

        # remove (year)
        pattern = r"\(\d{4}\)"
        text = re.sub(pattern, "", text)
        return text.replace("\n", " ").replace("  ", " ")


    if "collapse_make_table":
        df_final = pd.DataFrame()
        df_final["Description"] = {event["idx"]: clean_up_text(event["text"]) for event in fig6_chosen_events}
        df_final[("Start", "Year")] = df_table["time_start"].dt.year.astype(int)
        df_final[("End", "Year")] = df_table["time_end"].dt.year.astype(int)
        df_final[(r"Duration (mon)", r"[$\mu \pm \sigma$]")] = df_table.duration_2sigma_mon.round(2)
        df_final[(r"Duration (mon)", r"Total")] = df_table.duration_lagrangian_mon.astype(int)
        df_final[(r"Area (Mi km)", r"Avg.")] = df_table.area_avg_km2.pipe(lambda x: x / 1e6).round(2)
        df_final[(r"Area (Mi km)", r"Max.")] = df_table.area_max_km2.round(2)
        df_final[(r"MHW $I_{Q95}$", r"(°C)")] = df_table.mhw_intensity_p95.round(2)
        df_final[(r"MHW $I_{Q95}$", r"($\psi$)")] = df_table.mhw_intensity_norm_p95.round(2)
        df_final[(r"OAX $I_{Q95}$", r"(nmol kg$^{-1}$)")] = df_table.oax_intensity_p95.round(2)
        df_final[(r"OAX $I_{Q95}$", r"($\psi$)")] = df_table.oax_intensity_norm_p95.round(2)
        df_final[(r"OAX$\cap$MHW", r"$I_{Q95}$")] = df_table.cex_intensity_norm_p95.round(2)
        df_final[(r"OAX$\cap$MHW", r"$S_{Q95}$")] = df_table.cex_severity_norm_p95.round(2)
        df_final = df_final.set_index("Description")

        df_final.columns = pd.MultiIndex.from_tuples(df_final.columns)

    df_final_disp = df_final.style.format("{:.2f}")
    df_final_disp
    # print(df_final.to_latex(float_format='%.2f'))
    return


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    # Figure 7
    """)
    return


@app.cell
def _(data):
    if "collapse_data_prep":
        blob_region = dict(time=slice("2015-03", "2016-03"), lat=slice(5, 50), lon=slice(-170, -110))

        blob_extreme = peed.get_event_data(data, event_idx=330, event_region=blob_region)
        blob_extreme.drivers = blob_extreme.drivers.drop_sel(driver="FW")
        print(blob_extreme.xy)

    if "collapse_main_plotting":
        fig7, axs7 = peed.create_figure_layout()
        peed.plot_drivers_of_oax(
            blob_extreme.oax.squeeze(),
            blob_extreme.drivers.squeeze(),
            smoothen_radius_days=30,
            axs=axs7[-2:],
        )
        peed.plot_event_maps(blob_extreme.geo, axs7[:3])
        peed.plot_legend_with_dummy_lines(axs7[-2:])
        for _ax in axs7:
            _ax.plot(*blob_extreme.xy, marker="o", color="none", mec="k", mew=2)

    if "collapse_annotations":
        lines7 = axs7[4].get_lines()
        peed.annotate_hplus_driver(lines7[1], "C", npdt("2015-02-08"), size=14, ha="center", va="top")
        peed.annotate_hplus_driver(lines7[2], "T", npdt("2015-07-08"), size=14, ha="right")
        peed.annotate_hplus_driver(lines7[3], "A", npdt("2016-06-28"), size=14, ha="left", va="top")
        peed.annotate_hplus_driver(lines7[4], "", npdt("2015-07-15"), size=14, ha="left", va="bottom")

    if "collapse_axes_lims_ticks_and_labels":
        axs7[3].set_ylim(-1.41, 1.41)
        axs7[4].set_ylim(-1.2, 1.2)

        fig7_xlim = pd.to_datetime(["2013-07", "2016-10"])
        fig7_xdates = pd.date_range("2013-07", "2016-11", freq="6MS")
        peed.add_nice_date_labels(axs7[-2:], fig7_xdates)

        for _ax in axs7[-2:]:
            _ax.set_xlim(fig7_xlim)
            peed.add_vertical_bars(_ax, zorder=-1, offset=5, color="#f0f0f0")

    if "collapse_labelling":
        fig7_map_dates = blob_extreme.geo.cex.time[:3].to_index()
        fig7_date_labels = peed.get_season_abbreviations(fig7_map_dates)
        vis.number_subplots(axs7[:3], fig7_date_labels, x="right", y="top", space=0.02, braces=False)
        vis.number_subplots(axs7, y="top")

    if "collapse_save_figure":
        fig7.savefig(root / "figures/figure7_multi_5_drivers_Hplus_Blob.pdf")
        fig7.savefig(root / "figures/figure7_multi_5_drivers_Hplus_Blob.png", dpi=300)
        ...

    fig7
    return


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    # Figure 8
    """)
    return


@app.cell
def _(data):
    if "collapse_data_prep":
        namhw_region = dict(time=slice("2023-04", "2023-12"), lat=slice(0, 60), lon=slice(-77, -3))

        namhw_extreme = peed.get_event_data(data, event_idx=450, event_region=namhw_region, find_most_intense_point_var="oax.intensity")
        namhw_extreme.drivers = namhw_extreme.drivers.drop_sel(driver="FW")
        print(namhw_extreme.xy)

    if "collapse_main_plotting":
        fig8, axs8 = peed.create_figure_layout()
        peed.plot_drivers_of_oax(
            namhw_extreme.oax.squeeze(),
            namhw_extreme.drivers.squeeze(),
            smoothen_radius_days=30,
            axs=axs8[-2:],
        )
        peed.plot_event_maps(namhw_extreme.geo, axs8[:3])
        peed.plot_legend_with_dummy_lines(axs8[-2:])
        for _ax in axs8:
            _ax.plot(*namhw_extreme.xy, marker="o", color="none", mec="k", mew=2)

    if "collapse_annotations":
        lines8 = axs8[4].get_lines()
        peed.annotate_hplus_driver(lines8[1], "C", npdt("2024-05-08"), size=14, ha="right", va="bottom")
        peed.annotate_hplus_driver(lines8[2], "T", npdt("2023-06-08"), size=14, ha="right")
        peed.annotate_hplus_driver(lines8[3], "A", npdt("2024-08-28"), size=14, ha="center", va="top")
        peed.annotate_hplus_driver(lines8[4], "", npdt("2023-08-15"), size=14, ha="left", va="bottom")

    if "collapse_axes_lims_ticks_and_labels":
        axs8[3].set_ylim(-1.71, 1.71)
        axs8[4].set_ylim(-0.9, 0.9)

        fig8_xlim = pd.to_datetime(["2021-12", "2024-12"])
        fig8_xdates = pd.date_range("2021-01", "2024-12", freq="6MS")
        peed.add_nice_date_labels(axs8[-2:], fig8_xdates)

        for _ax in axs8[-2:]:
            _ax.set_xlim(fig8_xlim)
            peed.add_vertical_bars(_ax, zorder=-1, offset=0, color="#f0f0f0")

    if "collapse_labelling":
        fig8_map_dates = namhw_extreme.geo.cex.time[:3].to_index()
        fig8_date_labels = peed.get_season_abbreviations(fig8_map_dates)
        vis.number_subplots(axs8[:3], fig8_date_labels, x="right", y=0.86, space=0.02, braces=False)
        vis.number_subplots(axs8, y="top")

    if "collapse_save_figure":
        fig8.savefig(root / "figures/figure8_multi_5_drivers_Hplus_namhw.pdf")
        fig8.savefig(root / "figures/figure8_multi_5_drivers_Hplus_namhw.png", dpi=300)
        ...

    fig8
    return


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    # Figure 9
    """)
    return


@app.cell
def _(data, drivers):
    if "collapse_data_prep":
        lowlat_agg_drivers = ged.get_figure_data(data, drivers)

    if "collapse_figure_layout":
        fig9, axs9 = plt.subplots(2, 2, figsize=(7.8, 5), sharex=True, sharey="row")
        axs9 = axs9.flatten()

    if "collapse_main_plotting":
        ged.plot_top_row_axes(lowlat_agg_drivers["oax_extreme"], lowlat_agg_drivers["not_oax_extreme"], name="OAX", ax=axs9[0])
        ged.plot_top_row_axes(lowlat_agg_drivers["compound_extreme"], lowlat_agg_drivers["not_compound_extreme"], name="CEX", ax=axs9[1])
        ged.plot_bot_row_axes(lowlat_agg_drivers["oax_extreme"], lowlat_agg_drivers["not_oax_extreme"], name="OAX", ax=axs9[2])
        ged.plot_bot_row_axes(lowlat_agg_drivers["compound_extreme"], lowlat_agg_drivers["not_compound_extreme"], name="CEX", ax=axs9[3])

        [eed.add_vertical_bars(ax, bar_width=3, dtype=float, offset=0, zorder=-2) for ax in axs9]

    if "collapse_axes_limits":
        axs9[0].set_ylim(-0.75, 1.25)
        axs9[2].set_ylim(-0.4, 0.7)

    if "collpase_labelling":
        axs9[0].set_title("OAX-only Extremes")
        axs9[1].set_title("Compound  MHW$\\cap$OAX  Extremes")
        axs9[0].set_ylabel("[H$^+$] climatology [nmol kg$^{-1}$]")
        axs9[2].set_ylabel("[H$^+$] magnitude [nmol kg$^{-1}$]")
        vis.number_subplots(axs9, y="bottom")

    if "collapse_annotations":
        annot_props = {"size": 14, "va": "bottom", "ha": "center"}

        lines9_a = axs9[0].get_lines()
        eed.annotate_hplus_driver(lines9_a[0], "C", 4, **annot_props)
        eed.annotate_hplus_driver(lines9_a[2], "T", 9, **annot_props)
        eed.annotate_hplus_driver(lines9_a[4], "A", 8, **annot_props)
        eed.annotate_hplus_driver(lines9_a[6], ".", 2.2, **annot_props)

        lines9_d = axs9[3].get_lines()
        eed.annotate_hplus_driver(lines9_d[0], "C", 7, **annot_props)
        eed.annotate_hplus_driver(lines9_d[1], "T", 9, **annot_props)
        eed.annotate_hplus_driver(lines9_d[2], "A", 8, **annot_props)
        eed.annotate_hplus_driver(lines9_d[3], ".", 3.3, **annot_props)

    fig9.savefig("./figures/figure9_multi_drivers_Hplus_OAX_CEX.pdf")
    fig9
    return


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    # Figure 11
    """)
    return


@app.cell
def _(data):
    if "collapse_data_prep":
        cex_intensity = data.cex.intensity_norm.where(data.cex.mask).fillna(0).compute()
        oni = cxf.io.get_oni_data().to_xarray().assign_coords(time=lambda x: x.time + pd.Timedelta(days=14))
        corr_cex_oni = xr.corr(cex_intensity, oni, dim="time").where(data.cex.mask.any("time"))
        contours = data.masks.regions_HL.where(lambda x: x > 0)

    if "collapse_main_plotting":
        levels = np.arange(0.05, 0.26, 0.05)
        levels = np.r_[-levels, [-0.01, 0.01], levels]

        img10 = corr_cex_oni.geo.contourf(
            extend="both",
            proj=crs.EqualEarth(205),
            levels=levels,
            cbar_kwargs=dict(spacing="proportional", orientation="horizontal", label="", pad=0.02, shrink=0.45),
        )

        fig10 = img10.figure
        ax10 = img10.axes

    if "collapse_contours":
        contours.plot.contour(levels=[1], ax=img10.axes, transform=crs.PlateCarree(), colors=["k"], linewidths=[1])

    if "collapse_labelling":
        fig10_cbar_props = dict(transform=img10.colorbar.ax.transAxes, va="center")
        img10.colorbar.set_ticks([-0.2, -0.1, 0, 0.1, 0.2])
        img10.colorbar.ax.text(0.5, -1.4, "$\\rho\,(I_{CEX}$, ONI)", ha="center", **fig10_cbar_props)
        img10.colorbar.ax.text(0.0, -1.4, "$\leftarrow$ La Niña", ha="left", **fig10_cbar_props)
        img10.colorbar.ax.text(1.0, -1.4, "El Niño $\\rightarrow$", ha="right", **fig10_cbar_props)

    if "collapse_savefig":
        fig10.savefig("./figures/figure10_nino_cex_corr.pdf", bbox_inches="tight")
    fig10
    return


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    # Figure 12

    This may be dropped from the manuscript since it is not referenced in the text at all.
    """)
    return


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    # Figure 13
    """)
    return


@app.cell
def _(data):
    @cxf.disk_cache("./data/cache_hashed/")
    def compute_frac_robust(deseas, uncert, mask):
        n_extremes = mask.sum("time")
        signal = deseas.pipe(abs)
        noise = uncert * 1.5
        robust = (signal > noise).where(mask).sum("time") / n_extremes
        percent = robust * 100
        return percent.assign_attrs(long_name=" (%)").compute()


    if "collapse_prep_data":
        detrended = data.aux - data.aux.map(eed.calc_trend)
        season_grp = detrended.groupby("time.month")

        deasonalised = (season_grp - season_grp.mean("time")).chunk({"lat": 90, "lon": 90, "time": 60})
        mask = data.cex.mask

        dic_robust = compute_frac_robust(deasonalised.dic, data.aux.dic_uncert, mask)
        alk_robust = compute_frac_robust(deasonalised.talk, data.aux.talk_uncert, mask)
        temp_robust = compute_frac_robust(deasonalised.temperature, 0.25, mask)

    if "collapse_fig_layout":
        fig13 = plt.figure(figsize=(7.8, 4.3))
        fig13_props = {"levels": 6, "add_colorbar": False}

    if "collapse_plotting":
        imgs13 = {
            "a": dic_robust.geo.contourf(pos=221, **fig13_props),
            "b": alk_robust.geo.contourf(pos=222, **fig13_props),
            "c": temp_robust.geo.contourf(pos=223, **fig13_props),
        }

        axs13 = [img.axes for img in imgs13.values()]
        p = vis.utils.center_image(axs13[2], axs13[:2])

    if "collapse_colorbar":
        w = 0.08
        cax13 = plt.axes([p[0] + w, p[1] - 0.05, p[2] - w * 2, 0.03])
        plt.colorbar(mappable=imgs13["c"], cax=cax13, orientation="horizontal", label="Robustness of driver signal (%)")

    if "collapse_labelling":
        [ax.set_title("") for ax in axs13]
        axs13[0].set_title("(a) sDIC", size="medium", x=0.2, ha="left")
        axs13[1].set_title("(b) sAlk", size="medium", x=0.2, ha="left")
        axs13[2].set_title("(c) Temperature", size="medium", x=0.2, ha="left")

    if "collapse_savefig":
        fig13.savefig("./figures/figure13_robustness_of_drivers.pdf", bbox_inches="tight")
    fig13
    return


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    # Appendix Figures

    - Figures A1 through A3 remain exactly the same
    - A4: updated but same (but will likely drop the figure)
    - A5 - A8: new sensitivity plots showing impact of choices
    - A9 = old A7
    - A10 = old A8
    """)
    return


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    ## Figure A4
    """)
    return


@app.cell
def _(data, drivers):
    if "collapse_data_prep":
        highlat_agg_drivers = ged.get_figure_data(data, drivers, region_mask_value=1)

    if "collapse_figure_layout":
        figA4, axsA4 = plt.subplots(2, 2, figsize=(7.8, 5), sharex=True, sharey="row")
        axsA4 = axsA4.flatten()

    if "collapse_main_plotting":
        ged.plot_top_row_axes(highlat_agg_drivers["oax_extreme"], highlat_agg_drivers["not_oax_extreme"], name="OAX", ax=axsA4[0])
        ged.plot_top_row_axes(highlat_agg_drivers["compound_extreme"], highlat_agg_drivers["not_compound_extreme"], name="CEX", ax=axsA4[1])
        ged.plot_bot_row_axes(highlat_agg_drivers["oax_extreme"], highlat_agg_drivers["not_oax_extreme"], name="OAX", ax=axsA4[2])
        ged.plot_bot_row_axes(highlat_agg_drivers["compound_extreme"], highlat_agg_drivers["not_compound_extreme"], name="CEX", ax=axsA4[3])

        [eed.add_vertical_bars(ax, bar_width=3, dtype=float, offset=0, zorder=-2) for ax in axsA4]

    if "collapse_axes_limits":
        axsA4[0].set_ylim(-0.75, 1.25)
        axsA4[2].set_ylim(-0.4, 0.7)

    if "collpase_labelling":
        axsA4[0].set_title("OAX-only Extremes")
        axsA4[1].set_title("Compound  MHW$\\cap$OAX  Extremes")
        axsA4[0].set_ylabel("[H$^+$] climatology [nmol kg$^{-1}$]")
        axsA4[2].set_ylabel("[H$^+$] magnitude [nmol kg$^{-1}$]")
        vis.number_subplots(axsA4, y="bottom")

    if "collapse_annotations":
        annot_propsA4 = {"size": 14, "va": "bottom", "ha": "center"}

        linesA4_a = axsA4[0].get_lines()
        eed.annotate_hplus_driver(linesA4_a[0], "C", 4, **annot_propsA4)
        eed.annotate_hplus_driver(linesA4_a[2], "T", 9, **annot_propsA4)
        eed.annotate_hplus_driver(linesA4_a[4], "A", 8, **annot_propsA4)
        eed.annotate_hplus_driver(linesA4_a[6], ".", 2.2, **annot_propsA4)

        linesA4_d = axsA4[3].get_lines()
        eed.annotate_hplus_driver(linesA4_d[0], "C", 7, **annot_propsA4)
        eed.annotate_hplus_driver(linesA4_d[1], "T", 9, **annot_propsA4)
        eed.annotate_hplus_driver(linesA4_d[2], "A", 8, **annot_propsA4)
        eed.annotate_hplus_driver(linesA4_d[3], ".", 3.3, **annot_propsA4)

    # figA4.savefig("./figures/figureA4_multi_drivers_Hplus_OAX_CEX_high_lats.pdf")
    figA4
    return


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    ## Figure A7
    """)
    return


@app.cell
def _():
    oni6 = cxf.get_oni_data()
    oni6.index = oni6.index.year + oni6.index.dayofyear / 366
    oni6_mask = (oni6 > 1.5).astype(float).where(lambda x: x > 0)
    return (oni6_mask,)


@app.cell
def _(df_event_stats, oni6_mask):
    small_thresh = 2_000_000 / 1e6
    weak_thresh = 3

    if "collapse_data_prep":
        small = df_event_stats["area_max_km2"] < small_thresh
        weak = df_event_stats["cex_intensity_norm_p95"] < weak_thresh

        small_or_weak = df_event_stats.where(small | weak).dropna()
        strong_and_big = df_event_stats.where(~small & ~weak).dropna()

        strong_and_big_pcnt = strong_and_big.groupby("year_start").count().area_avg_km2.cumsum().pipe(lambda x: x / x.max() * 100)
        small_or_weak_pcnt = small_or_weak.groupby("year_start").count().area_avg_km2.cumsum().pipe(lambda x: x / x.max() * 100)

        strong_and_big_pcnt = strong_and_big_pcnt.reindex_like(small_or_weak_pcnt).ffill().fillna(0)

    if "collapse_plotting":
        figA6 = plt.figure(figsize=(5, 2))

        small_or_weak_pcnt.plot(lw=6, label="Small OR Weak")
        axA6 = strong_and_big_pcnt.plot(lw=6, label="Large AND Intense")

        axA6.fill_between(oni6_mask.index, oni6_mask * 100, color="0.90")
        vis.utils.clear_labels(axA6)
        axA6.legend(loc="upper left", frameon=True, fancybox=1, facecolor="1", framealpha=1)

        axA6.set_ylabel("Percentage of events occurred")

    figA6.savefig("./figures/figureA9_rate_of_compound_extremes.pdf")
    figA6
    return


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    ## Figure A8
    """)
    return


@app.cell
def _():
    def series_to_text(title, series, space_after={"Q25", "Mean"}):
        text = f"{title}\n\n"
        for key, value in series.to_dict().items():
            text += f"{key} = {value:.2f}\n"
            if key in space_after:
                text += "\n"

        return text


    def plot_hist_bar_and_density(da: xr.DataArray, line_multiplier: float = 1.0, **kwargs):

        bins = kwargs.pop("bins", None)
        if "ax" in kwargs:
            ax = kwargs.pop("ax")
        else:
            ax = plt.axes()

        freq, bins, plot = da.plot.hist(**kwargs, bins=bins, ax=ax)

        bin_centers = (bins[:-1] + bins[1:]) / 2
        freq = (freq / freq.sum()) * ax.get_ylim()[1] * line_multiplier

        ax.plot(bin_centers, freq, **kwargs)

        return ax

    return plot_hist_bar_and_density, series_to_text


@app.cell
def _(data, plot_hist_bar_and_density, series_to_text):
    if "collapse_data_prep":
        df = (
            xr.merge(
                [
                    data.oax[["intensity", "mask"]].rename(mask="oax_mask", intensity="oax_intensity"),
                    data.mhw[["intensity", "mask"]].rename(mask="mhw_mask", intensity="mhw_intensity"),
                    data.cex[["mask"]].rename(mask="cex_mask"),
                ]
            )
            .reset_coords(drop=True)
            .to_dataframe()
        )

        df_events = pd.concat(
            [
                df.oax_intensity.where(df.oax_mask).rename("oax"),
                df.oax_intensity.where(df.oax_mask & df.cex_mask).rename("oax_cex"),
                df.mhw_intensity.where(df.mhw_mask).rename("mhw"),
                df.mhw_intensity.where(df.mhw_mask & df.cex_mask).rename("mhw_cex"),
            ],
            axis=1,
        ).dropna(how="all")

        summary = df_events.describe(percentiles=[0.05, 0.25, 0.50, 0.75, 0.95])
        cols = {
            "min": "Min",
            "5%": "Q05",
            "25%": "Q25",
            "50%": "Median",
            "mean": "Mean",
            "75%": "Q75",
            "95%": "Q95",
            "max": "Max",
            "std": "Std",
        }
        summary = summary.loc[list(cols)].rename(index=cols).round(2)

    if "collapse_plotting":
        figA8, axsA8 = plt.subplots(1, 2, figsize=(7.7, 3), sharey=True)

        mhw_props = {"bins": np.arange(0.05, 1.5, 0.05), "color": "C1", "ax": axsA8[0]}
        plot_hist_bar_and_density(data.mhw.intensity.where(data.mhw.mask), **mhw_props, alpha=0.5, line_multiplier=5.7)
        plot_hist_bar_and_density(data.mhw.intensity.where(data.cex.mask), **mhw_props, alpha=1.0, line_multiplier=4.5)

        oax_props = {"bins": np.arange(0.01, 0.25, 0.01), "color": "C0", "ax": axsA8[1]}
        plot_hist_bar_and_density(data.oax.intensity.where(data.oax.mask), **oax_props, alpha=0.5, line_multiplier=4.3)
        plot_hist_bar_and_density(data.oax.intensity.where(data.cex.mask), **oax_props, alpha=1.0, line_multiplier=3.1)

    if "collapse_annotation":
        props_text_mhw = dict(y=0.95, color="C1", ha="right", va="top", transform=axsA8[0].transAxes)
        axsA8[0].text(x=0.6, s=series_to_text("MHW$\cap$OAX", summary.mhw_cex.abs()), **props_text_mhw)
        axsA8[0].text(x=0.9, s=series_to_text("MHW", summary.mhw.abs()), **props_text_mhw, alpha=0.5)

        props_text_oax = dict(y=0.95, color="C0", ha="right", va="top", transform=axsA8[1].transAxes)
        axsA8[1].text(x=0.6, s=series_to_text("OAX$\cap$MHW", summary.oax_cex.abs()), **props_text_oax)
        axsA8[1].text(x=0.9, s=series_to_text("OAX", summary.oax.abs()), **props_text_oax, alpha=0.5)


    if "collapse_labelling":
        [vis.utils.clear_labels(ax) for ax in axsA8]
        axsA8[0].set_ylabel("Frequency")
        axsA8[0].set_xlabel(r"$I_{\sf{MHW\cap OAX}}$ MHW [°C]")
        axsA8[1].set_xlabel(r"$I_{\sf{OAX\cap MHW}}$ OAX [nmol kg$^{-1}$]")

        axsA8[0].set_title("a) Marine Heatwaves", loc="left", size="medium")
        axsA8[1].set_title("b) Ocean Acidification Extremes", loc="left", size="medium")

    figA8.savefig("./figures/figureA10_compare_compounds.pdf", bbox_inches="tight")
    figA8
    return


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    ## A5, A6 Experiment violin plots
    """)
    return


@app.cell
def _():
    import plot_sensitivities as ps

    return (ps,)


@app.cell
def _(ps):
    if "collapse_data_prep":
        keys = ps.VIOLINPLOT_Y_KEYS
        colors = ps.COLORS

        ds = ps.open_data()


    if "collapse_plot_polyorder_hue":
        with ps.color_context(colors[:2]):  # first, color by polynomial order
            hue = "Polynomial order"
            suptitle_text = (
                "Distributions of 12 x 500 most extreme events for CMEMS and ETHZ\n"
                "showing the impact of threshold percentile (x-axis) and polynomial order (color)"
            )
            fig_sens_polyorder, axs_sens_polyorder = ps.plot_violinplots_2x2(ds, keys, suptitle_text=suptitle_text, hue=hue)
            axs_sens_polyorder["d"].legend(ncol=2, title=hue, loc=0, edgecolor="none")

            fig_sens_polyorder.savefig("./figures/figureA5_sensitivities_violins-hue_polyorder.pdf", bbox_inches="tight")

    if "collapse_plot_dataset_hue":
        with ps.color_context(colors[2:5:2][::-1]):
            hue = "Dataset"
            suptitle_text = "Distributions of 12 x 500 most extreme events for CMEMS and ETHZ\nnshowing the impact of threshold percentile (x-axis) and dataset (color)"
            fig_sens_dataset, axs_sens_dataset = ps.plot_violinplots_2x2(ds, keys, suptitle_text=suptitle_text, hue=hue)
            axs_sens_dataset["d"].legend(ncol=1, title=hue, loc=0, edgecolor="none")

            fig_sens_dataset.savefig("./figures/figureA6_sensitivities_violins-hue_datasets.pdf", bbox_inches="tight")

    fig_sens_polyorder, fig_sens_dataset
    return


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    ## A7 Experiment Maps
    """)
    return


@app.cell
def _():
    if "collapse_prep_data":
        ds_num_extremes = xr.open_dataset("./data/sensitivities/cexTH_num_extremes_for_sensitivities.nc").num_extremes_map

        counts = (
            ds_num_extremes.squeeze(drop=True)
            .reset_coords(drop=True)
            .stack(
                Experiments=[
                    "Dataset",
                    "Polynomial order",
                    "Threshold percentile",
                ]
            )
            .where(lambda x: x > 0)
            .transpose("Experiments", "lat", "lon")
        )

    if "collapse_figure_layout":
        fig, axs = plt.subplots(4, 3, figsize=(9, 6), subplot_kw={"projection": crs.PlateCarree(205)})
        axs = axs.flatten()

    if "collapse_main_plotting":
        for _ax, _da in zip(axs, counts):
            _img = _da.plot.imshow(ax=_ax, vmin=0, vmax=28, cmap="bone_r", transform=crs.PlateCarree(), add_colorbar=False, rasterized=True)
            _ax.set_title("")
            _ax.add_feature(feature.LAND, facecolor="#cccccc")
            _ax.coastlines(lw=0.5)

        fig.tight_layout()

    if "collapse_labels":
        axs[0].set_title("90$^{th}$ precentile threshold")
        axs[1].set_title("95$^{th}$ precentile threshold")
        axs[2].set_title("99$^{th}$ precentile threshold")

        subplot_props = dict(rotation=90, va="center")
        axs[0].text(-0.06, 0.5, "1st order poly", transform=axs[0].transAxes, **subplot_props)
        axs[3].text(-0.06, 0.5, "2nd order poly", transform=axs[3].transAxes, **subplot_props)
        axs[6].text(-0.06, 0.5, "1st order poly", transform=axs[6].transAxes, **subplot_props)
        axs[9].text(-0.06, 0.5, "2nd order poly", transform=axs[9].transAxes, **subplot_props)

        x = axs[0].get_position().x0 - 0.04
        y0 = (axs[0].get_position().y1 + axs[3].get_position().y0) / 2
        y1 = (axs[6].get_position().y1 + axs[9].get_position().y0) / 2
        subplot_props = dict(rotation=90, va="center", ha="center", size="large")
        fig.text(x, y0, "CMEMS-FFNNv2", **subplot_props)
        fig.text(x, y1, "OceanSODA-ETHZv1", **subplot_props)

    if "collapse_colorbar":
        plt.colorbar(mappable=_img, ax=axs, location="right", pad=0.02, label=r"Total number of  MHW$\cap$OAX  compound extremes [months]")

    if "collapse_save":
        fig.savefig("./figures/figureA7_sensitivities_maps-num_compound_extreme_months.pdf", bbox_inches="tight")

    fig
    return


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    ## A8: Experiment time series
    """)
    return


@app.cell
def _():
    if "collapse_prep_data":
        df_timeseries = pd.read_csv("./data/sensitivities/cexTH_timeseries_extremes_for_sensitivities.csv")
        df_timeseries["time"] = pd.to_datetime(df_timeseries.time)

        timeseries = (
            df_timeseries.drop(columns=["Baseline"])
            .set_index(["Dataset", "Polynomial order", "Threshold percentile", "time"])
            .drop_duplicates()
            .to_xarray()
            .stack(Experiment=["Polynomial order", "Dataset"])
            .num_extremes_timeseries.sortby("time")
            .pipe(lambda x: x / 1e12)
            .assign_attrs(units="Mkm$^2$", long_name="Area")
        )

        ts_smooth = timeseries.rolling(time=12, center=True, min_periods=3).mean().rolling_exp(time=3).mean()

    if "collapse_main_plotting":
        fg_sens_timeseries = ts_smooth.plot.line(col="Experiment", col_wrap=2, x="time", size=2.5, aspect=1.7, add_legend=1, lw=3)
        fig_sens_timeseries = fg_sens_timeseries.fig
        axs_sens_timeseries = fg_sens_timeseries.axs.flatten()

    if "collapse_labelling":
        fg_sens_timeseries.set_titles("")

        [a.set_xlabel("") for a in axs_sens_timeseries]
        first_order = r"1$^{\sf{st}}$ order polynomial"
        second_order = r"2$^{\sf{nd}}$ order polynomial"
        names = [
            f"{first_order} CMEMS",
            f"{first_order} ETHZ",
            f"{second_order} CMEMS",
            f"{second_order} ETHZ",
        ]
        labels = [f"{c}) {lbl}" for c, lbl in zip("abcd", names)]
        vis.number_subplots(axs_sens_timeseries, labels, y=1)

    if "collapse_savefig":
        fig_sens_timeseries.savefig("./figures/figureA8_sensitivities_timeseries-global_area.pdf", bbox_inches="tight")

    fig_sens_timeseries
    return


@app.cell
def _():
    return


@app.cell(hide_code=True)
def _():
    mo.md(r"""
 
    """)
    return


if __name__ == "__main__":
    app.run()

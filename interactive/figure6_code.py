import warnings
from typing import Any

import cartopy.crs as crs
import cartopy.feature as feature
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import xarray as xr


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

            for _i in highlight_index:
                df_sorted_highlighted = df_sorted.loc[[_i]]

                _props.update(linewidth=3, zorder=5, c=c, edgecolor="w", marker="o")
                df_sorted_highlighted.plot.scatter(ax=ax, **_props)

                _props.update(linewidth=1.5, zorder=5, c="none", edgecolor="k")
                df_sorted_highlighted.plot.scatter(ax=ax, **_props)

    vis.scatter_extras.buffer_axis_limits(ax)


def _(data, df_event_stats):
    if "collapse_data_prep":
        fig6_chosen_events: list[dict[str, Any]] = [
            dict(idx=156, text="SE Asia\n(1998)", dx=-0.2, dy=-0.5, ha="right"),
            # dict(idx=151, text="Equatorial Pacific\n(1998)", dx=0.2, dy=-0.5),
            dict(idx=222, text="Mediterranean\nSea (2003)", dx=0, dy=0.5, ha="center"),
            dict(idx=289, text="Western\nAustralia\n(2011)", dx=-0.4, dy=0.4, ha="right"),
            dict(idx=318, text="The Blob (2015)", dx=-0, dy=1, ha="center"),
            dict(idx=350, text="South\nPacific\n(2015)", dx=0.4, dy=-0.8, ha="center"),
            dict(idx=26, text="Madagascar\n(1987)", dx=0.45, dy=0.45, ha="center"),
            dict(idx=435, text="Barrier\nReef\n(2022)", dx=0.2, dy=-0.45, ha="right"),
            dict(idx=450, text="North\nAtlantic\n(2023)", dx=-0.25, dy=0.2, ha="right"),
            dict(idx=460, text="South\nAtlantic\n(2023)", dx=0.4, dy=0.6, ha="center"),
        ]

        event_idxs: list[int] = [v["idx"] for v in fig6_chosen_events]
        drop_from_map = [156]
        event_idxs_for_map = list(set(event_idxs) - set(drop_from_map))

        most_extreme: xr.DataArray = data.cex.blobs.isin(event_idxs_for_map).compute()
        most_intense_avg: xr.DataArray = data.cex.intensity_norm.where(
            most_extreme & data.cex.mask
        ).quantile(0.95, dim="time")
        most_extreme_contours: xr.DataArray = most_extreme.any("time").astype(int)

        _df_events = df_event_stats.assign(chosen=lambda x: x.index.isin(event_idxs))

    if "collapse_figure_layout":
        fig6 = plt.figure(figsize=(7, 8.3), dpi=300)
        axs6: list[plt.Axes] = [
            fig6.add_subplot(211),
            fig6.add_subplot(212, projection=crs.PlateCarree(205)),
        ]
        fig6.subplots_adjust(hspace=0.15)

    if "collapse_plot_scatter":
        plot_extreme_events_scatter(
            _df_events,
            c="area_max_Mkm2",
            s="area_max_scl",
            x="duration_2sigma_mon",
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
            cbar_kwargs=dict(
                orientation="horizontal", shrink=1, aspect=30, fraction=0.06, pad=0.01
            ),
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
        axs6[1].text(-48, 45, "2023 ", **bf | _props | {"ha": "left", "va": "bottom"})
        axs6[1].text(-48, 45, "North\nAtlantic", **sf | _props | dict(ha="left", va="top"))

        _props = dict(transform=crs.PlateCarree(), va="center")
        axs6[1].text(-20, -30, "2023 ", **bf | _props | {"ha": "right", "va": "top"})
        axs6[1].text(-20, -30, "South\nAtlantic", **sf | _props | dict(ha="left", va="top"))

        _props = dict(transform=crs.PlateCarree(), va="center")
        axs6[1].text(120, -45, "2011 ", **bf | _props | dict(ha="right"))
        axs6[1].text(120, -45, "Western\nAustralia", **sf | _props | dict(ha="left"))

        _props = dict(transform=crs.PlateCarree())
        axs6[1].text(-8, 23, "2003", **bf, **_props)
        axs6[1].text(-8, 23, "MedSea", **sf, **_props)

    if "collapse_map_extent":
        axs6[1].set_extent([-180, 180, -90, 90], crs=crs.PlateCarree())  # type: ignore

    if "collapse_save_figure":
        # fig6.savefig(root / "figures/figure6-with_annotations.pdf", bbox_inches="tight")
        fig6.savefig(root / "figures/figure6-with_annotations.png", bbox_inches="tight", dpi=120)
        ...
    fig6
    return event_idxs, fig6_chosen_events

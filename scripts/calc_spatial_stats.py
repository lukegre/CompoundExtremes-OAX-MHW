import dotenv

dotenv.load_dotenv()

import xarray as xr

import compoundx_figs as cxf

ROOT = cxf.get_project_root()

FUNC_INTENSITY = cxf.suppress_warnings(cxf.sumstats.calc_intensity_mean_max)
FUNC_SEVERITY = cxf.suppress_warnings(cxf.sumstats.calc_severity_sum_max)
FUNC_DURATION = cxf.suppress_warnings(cxf.sumstats.calc_duration_ann_avg)

UNITS_nMLKG = "nmol.kg$^{-1}$"
CMAP_MHW = "Oranges"
CMAP_OAX = "Blues"
CMAP_CEX = "Greens"
NAME_MHW_INTENSITY = "MHW Intensity (°C)"
NAME_OAX_INTENSITY = f"OAX Intensity ({UNITS_nMLKG})"

PLOT_ARGS = {
    "mhw_I": {"cmap": CMAP_MHW, "pretty_name": NAME_MHW_INTENSITY},
    "mhw_In": {"cmap": CMAP_MHW, "pretty_name": r"${\widetilde{I}}_{MHW}$ (units)"},
    "mhw_Iann": {"cmap": CMAP_MHW, "pretty_name": NAME_MHW_INTENSITY},
    "oax_I": {"cmap": CMAP_OAX, "pretty_name": NAME_OAX_INTENSITY},
    "oax_In": {"cmap": CMAP_OAX, "pretty_name": r"${\widetilde{I}}_{OAX}$ (units)"},
    "cex_mhw_I": {"cmap": CMAP_MHW, "pretty_name": NAME_MHW_INTENSITY},
    "cex_mhw_S": {"cmap": CMAP_MHW, "pretty_name": "MHW Severity (°C.month)"},
    "cex_oax_I": {"cmap": CMAP_OAX, "pretty_name": NAME_OAX_INTENSITY},
    "cex_oax_S": {"cmap": CMAP_OAX, "pretty_name": f"OAX Severity ({UNITS_nMLKG}.month)"},
    "cex_I": {"cmap": CMAP_CEX, "pretty_name": "Normalized Intensity (units)"},
    "cex_S": {"cmap": CMAP_CEX, "pretty_name": "Severity (units.month)"},
    "mhw_D": {"cmap": CMAP_MHW, "pretty_name": "MHW duration (months)"},
    "oax_D": {"cmap": CMAP_OAX, "pretty_name": "OAX duration (months)"},
    "cex_D": {"cmap": CMAP_CEX, "pretty_name": r"OAX$\cap$MHW duration (months)"},
}


def main():
    fname_out = ROOT / "data/derived/spatial_stats.zarr"

    data = open_data()
    stats = calc_stats(data)
    stats = add_plot_attrs(stats)

    fname_out.parent.mkdir(parents=True, exist_ok=True)
    stats.to_zarr(fname_out, mode="w")


def open_data():
    fname = str(ROOT / "data/sources.yaml")
    return cxf.Datasets.from_yaml(fname, with_cache=False)


def calc_stats(data: cxf.Datasets):
    calc_intensity = FUNC_INTENSITY
    calc_severity = FUNC_SEVERITY
    calc_duration = FUNC_DURATION

    stats_dict = {
        "mhw_I": calc_intensity(data.mhw.intensity, data.mhw.mask),
        "mhw_In": calc_intensity(data.mhw.intensity_norm, data.mhw.mask),
        "mhw_Iann": cxf.sumstats.calc_intensity_ann_max(data.mhw.intensity, data.mhw.mask),
        "oax_I": calc_intensity(data.oax.intensity, data.oax.mask),
        "oax_In": calc_intensity(data.oax.intensity_norm, data.oax.mask),
        "cex_mhw_I": calc_intensity(data.mhw.intensity, data.cex.mask),
        "cex_mhw_S": calc_severity(data.mhw.intensity, data.cex.mask),
        "cex_oax_I": calc_intensity(data.oax.intensity, data.cex.mask),
        "cex_oax_S": calc_severity(data.oax.intensity, data.cex.mask),
        "cex_I": calc_intensity(data.cex.intensity_norm, data.cex.mask),
        "cex_S": calc_severity(data.cex.intensity_norm, data.cex.mask),
        "mhw_D": calc_duration(data.mhw.mask),
        "oax_D": calc_duration(data.oax.mask),
        "cex_D": calc_duration(data.cex.mask),
    }

    stats_list = [v.rename(k).compute() for k, v in stats_dict.items()]

    extreme_spatial_stats = xr.merge(
        stats_list,
        compat="override",
    )
    return extreme_spatial_stats


def add_plot_attrs(ds: xr.Dataset):
    for var in ds.data_vars:
        if var in PLOT_ARGS:
            ds[var].attrs.update(PLOT_ARGS[var])
    return ds


if __name__ == "__main__":
    main()

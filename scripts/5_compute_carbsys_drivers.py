import pathlib

import dotenv
import xarray as xr
from dask.diagnostics.progress import ProgressBar

import compoundx_figs as cf

ROOT = pathlib.Path(dotenv.find_dotenv("pyproject.toml")).parent

OUTPUT_FOLDER = ROOT / "data/v2025/carbsys_drivers/"


def main():
    data = open_data()
    calc_drivers(data)


def open_data() -> cf.Datasets:
    fname = str(ROOT / "data/sources.yaml")
    return cf.Datasets.from_yaml(fname, with_cache=False)


def calc_drivers(data: cf.Datasets) -> xr.DataArray:

    OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)

    fname_sens = OUTPUT_FOLDER / "carbsys_sensitivities_full_area.zarr"
    fname_drivers = OUTPUT_FOLDER / "carbsys_drivers_full_area.zarr"

    if fname_sens.exists():
        sens = xr.open_zarr(fname_sens)
    else:
        sens = cf.calc_sensitivities(
            alk=data.aux.talk,
            dic=data.aux.dic,
            temp=data.aux.temperature,
            sal=data.aux.salinity,
            normalize_to_sal=True,
            batch_size=6,
            verbose=5,
            n_jobs=4,
        )

        sens.to_zarr(fname_sens, zarr_format=2, mode="w")

    if fname_drivers.exists():
        event_drivers = xr.open_zarr(fname_drivers).Hplus_drivers
    else:
        with ProgressBar():
            event_drivers = calc_hplus_drivers(
                hplus=data.oax.data,
                dic=data.aux.dic,
                alk=data.aux.talk,
                salinity=data.aux.salinity,
                temp=data.aux.temperature,
                sensitivities_beta=sens.beta,
            ).compute()
        event_drivers.to_dataset(name="Hplus_drivers").to_zarr(fname_drivers, mode="w")

    return event_drivers


def calc_hplus_drivers(
    hplus: xr.DataArray,
    dic: xr.DataArray,
    alk: xr.DataArray,
    salinity: xr.DataArray,
    temp: xr.DataArray,
    sensitivities_beta: xr.Dataset,
    salinity_norm=34.5,
) -> xr.DataArray:

    drivers = xr.Dataset()
    drivers["dic"] = dic
    drivers["alk"] = alk
    drivers["salt"] = salinity
    drivers["temp"] = temp
    drivers["sdic"] = drivers.dic / drivers.salt * salinity_norm
    drivers["salk"] = drivers.alk / drivers.salt * salinity_norm

    trend = drivers.map(calc_trend, deg=2)
    change = drivers - trend
    beta = sensitivities_beta.to_dataset(dim="driver")

    delta_driver = xr.Dataset()
    delta_driver["sDIC"] = hplus / drivers.sdic * beta["C"] * change.sdic
    delta_driver["sALK"] = hplus / drivers.salk * beta["A"] * change.salk
    delta_driver["TEMP"] = hplus / drivers.temp * beta["T"] * change.temp
    delta_driver["FW"] = hplus / drivers.salt * beta["FW"] * change.salt

    # ∆driver is the response of [H+] to each driver. The change variable
    # is the change in each driver with the second order trend removed.
    # This is equivalent to the shifting baseline.
    delta_driver = (
        delta_driver.to_array(name="seasonal_drivers", dim="driver")
        .sel(driver=["sDIC", "TEMP", "sALK", "FW"])
        .reindex_like(drivers)
        .transpose("driver", "time", "lat", "lon")
    )

    return delta_driver


def calc_trend(da: xr.DataArray, dim="time", deg=2) -> xr.DataArray:
    p = da.polyfit(dim=dim, deg=deg).polyfit_coefficients
    x = da[dim]

    trend = xr.polyval(x, p)
    return trend


if __name__ == "__main__":
    main()

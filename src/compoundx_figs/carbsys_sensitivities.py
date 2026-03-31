"""
Find the carbonate system sensitivities for:
    - pCO2
    - H+
    - OmegaAR/CA

DIC and TA sensitivities are calculated using PyCO2SYS
Freshwater sensitivity is calculated as: FW = C + A + 1
Temperature sensitivity is calculated empiricially; see
the TemperatureSensitivity class.
"""

import os
from typing import Any

import numpy as np
import pandas as pd
import xarray as xr
from joblib import Parallel, delayed
from PyCO2SYS.api import CO2SYS_wrap

CO2SYS_PARAMS = {"K1K2_constants": 10, "opt_buffers_mode": 1, "KSO4_constants": 1}
N_CPUS = os.cpu_count() or 1


def get_sensitivities(
    dic: xr.DataArray,
    alk: xr.DataArray,
    sal: xr.DataArray,
    temp: xr.DataArray,
    dataset_name="ETHZv2021",
    dest="../data/organised/",
    overwrite=False,
):
    """
    A high level function that loads co2sys_sensitivities if they exist,
    else will calculate, save and return the output.

    Calls calc_sensitivities with salinity normalisation.
    """
    normalize_to_sal = False

    normed = "_normed" if normalize_to_sal else "_notnormed"
    fname = os.path.abspath(
        os.path.expanduser(f"{dest}/{dataset_name}_carbsys_sensitivities{normed}.nc")
    )

    if os.path.isfile(fname) & (not overwrite):
        print(f"Loading {fname}")
        return xr.open_dataset(fname, chunks={})

    print(f"File will be written to {fname}")

    ds = calc_sensitivities(dic, alk, sal, temp, normalize_to_sal=normalize_to_sal)
    ds.to_netcdf(fname, encoding={k: dict(complevel=4, zlib=True) for k in ds})

    return ds


def calc_sensitivities(
    dic: xr.DataArray,
    alk: xr.DataArray,
    sal: xr.DataArray,
    temp: xr.DataArray,
    normalize_to_sal: bool = True,
    **kwargs,
) -> xr.Dataset:
    """
    Find the carbonate system sensitivities of pCO2, H+, Omega to
    drivers DIC, TA, temperature, and salinity.

    Use PyCO2SYS and empirical estimates of the sensitivities for the
    marine carbonate system.

    Parameters
    ----------
    dic, alk, sal, temp: xr.DataArrays
        DataArrays that share the same dims/coords.
    normalize_to_sal: bool[True]
        Will normalise dic and alk to the time averaged salinity, meaning
        that all freshwater fluxes will only be represented in salinity.
        Set to True to follow best practices from Sarmiento and Gruber (2006).

    Returns
    -------
    xr.Dataset:
        A dataset containing a DataArray for each of the three sensitivities
        for pCO2 (gamma), H (beta), and Omega (omega). The first dimension
        (driver) represents the drivers sDIC (C), sALK (A), Freshwater (FW),
        and Temperature (T). The C and A senstivities are based on
        PyCO2SYS. The FW senstivity is C + A + 1. The T sensitivity is
        determined empirically for each of the variables.

    See also
    --------
    TemperatureSensitivity to calculate the empirical relationships between
    the variables and temperature over a range of DIC and TA.

    """

    keep = ["gammaTCin", "gammaTAin", "omegaTCin", "omegaTAin", "betaTCin", "betaTAin"]

    ds = solve_carbsys(dic, alk, sal, temp, keep=keep, **kwargs)

    out = xr.Dataset()
    # convert from Egleston style (Buffer capacity) to Landschuetzer style (elasticity)
    # elasticities are unitless but have to be normalised by the driver
    # gamma_DIC_hat = buffer_capacity
    # gamma_DIC_hat = gamma_DIC / DIC
    #   and
    gamma = xr.Dataset()
    gamma["C"] = dic / (ds.gammaTCin * 1e6)  # mol --> umol
    gamma["A"] = alk / (ds.gammaTAin * 1e6)
    gamma["FW"] = gamma.C + gamma.A + 1
    gamma["T"] = temp * 0.0423  # Takahashi et al. 1993
    out["gamma"] = gamma.to_array(dim="driver").assign_attrs(
        temp_sensitivity=0.0423,
        description="pCO2 sensitivities. Units for DIC/TA are in umol/kg",
        software="PyCO2SYS",
    )

    beta = xr.Dataset()
    beta["C"] = dic / (ds.betaTCin * 1e6)
    beta["A"] = alk / (ds.betaTAin * 1e6)
    beta["FW"] = beta.C + beta.A + 1
    beta["T"] = temp * 0.0356  # empirically calculated
    out["beta"] = beta.to_array(dim="driver").assign_attrs(
        temp_sensitivity=0.0356,
        description="[H+] sensitivities. Units for DIC/TA are in umol/kg",
        software="PyCO2SYS",
    )

    omega = xr.Dataset()
    omega["C"] = dic / (ds.omegaTCin * 1e6)
    omega["A"] = alk / (ds.omegaTAin * 1e6)
    omega["FW"] = omega.C + omega.A + 1
    omega["T"] = temp * 0.0052  # empirically calculated
    out["omega"] = omega.to_array(dim="driver").assign_attrs(
        temp_sensitivity=0.0052,
        description="OmegaAR sensitivities. Units for DIC/TA are in umol/kg",
        software="PyCO2SYS",
    )

    normed = "DIC and TA have been normalized to local long-term mean salinity."
    normed = normed if normalize_to_sal else ""
    out = out.transpose("driver", "time", "lat", "lon").assign_attrs(
        contact="gregorl@ethz.ch",
        date=pd.Timestamp.today().strftime("%Y-%m-%d"),
        description=(
            "Landschuetzer et al. (2018) style sensitivities. "
            "DIC (C) and TA (A) are calculated using PyCO2SYS with "
            "Freshwater (FW = C + A + 1), and temperature (T) is "
            "is determined empirically from a grid of DIC and TA "
            "over a range of temperatures (-2 : 32 degC). While there "
            "is some varibility with changing DIC/TA, we weight the "
            "temperature sensitivity based on the distribution of "
            "data in the OceanSODA-ETHZ dataset. Fringe cases might "
            "thus suffer from higher uncertainties. "
            "To get to a change in a variable due to a driver, "
            "use the equation below. "
            "d_var = var / driver * driver_sensitivity * d_driver. "
            "Note that even temperature takes this form. " + normed
        ),
    )

    return out.astype("float32")


def solve_carbsys(
    dic: xr.DataArray,
    alk: xr.DataArray,
    sal: xr.DataArray,
    temp: xr.DataArray,
    keep: list[str] | None = None,
    verbose: bool = True,
    n_jobs: int = N_CPUS,
    batch_size: int = 12,
    pardim: str = "time",
) -> xr.Dataset:
    f"""
    Returns the full marine carbonate system if DIC and TA are given

    Processing is done in parallel using `joblib`

    Parameters
    ----------
    dic, alk, sal, temp: xr.DataArrays
        DataArrays that share the same dims/coords.
    keep: list[str] | None = None
        Which of the output columns should be kept from PyCO2SYS.
        See the PyCO2SYS documentation to find the column names.
        Defaults to None, which returns all the variables
    verbose: bool = True
        Will print out progress using joblib's parallel processing
    batch_size: int = 12
        The size of each batch along the parallel dimension (pardim)
    n_jobs: int = {N_CPUS}
        The number of cores that the processing will be split over
    pardim: str = "time"
        The dimension along which to split the job up. Defaults to time

    Returns
    -------
    xr.Dataset
        A dataset that contains the solved marine carbonate system variables.
        Will return only those in [keep] if specified.
    """

    def solve(ds: xr.Dataset, keep=None) -> xr.Dataset:

        df = ds.to_dataframe(["time", "lat", "lon"]).dropna()

        co2sys_inputs: dict[str, Any] = {k: df[k] for k in df}
        co2sys_inputs.update(CO2SYS_PARAMS)

        carbsys = CO2SYS_wrap(**co2sys_inputs, verbose=False)

        if keep is not None:
            carbsys = carbsys[keep]

        out = carbsys.set_index(df.index).to_xarray()

        return out

    ds = xr.merge(
        [dic.rename("dic"), alk.rename("alk"), sal.rename("sal"), temp.rename("temp_in")]
    ).load()

    n = ds[pardim].size
    s = n if n < batch_size else batch_size

    slices = [slice(t, t + s) for t in range(0, n, s)]
    if verbose:
        print(
            f"CO2SYS will process the dataset {str(dic.shape)} in {len(slices)} parts with {n_jobs} workers. "
        )

    for dim in ds.dims:
        ds = ds.dropna(dim, how="all")

    func = delayed(solve)
    pool = Parallel(n_jobs=n_jobs, verbose=True)
    out = pool([func(ds.isel(**{pardim: t}), keep=keep) for t in slices])
    out = xr.concat(out, pardim).sortby(pardim)

    return out


class TemperatureSensitivity:
    def __init__(self, dic: xr.DataArray, alk: xr.DataArray, n_vals=50):
        """
        A class that calculates the sensitivities of H+, pCO2, and Omega
        to changes in temperature (T).

        Parameters
        ----------
        dic, alk: xr.DataArray
            DIC and TA data who's distribution will be used to weight the
            trend distributions

        Returns
        -------
        object:
            Has several defaults that are initialised
            `[alk,dic,temp]_range` to determine range over which sensitivity
            is calculated
            `var_names` is used for plotting all variables.
            Also contains methods for a table / plots of values.
        """
        import numpy as np

        self.dic = dic
        self.alk = alk

        dmin, dmax = dic.quantile([0.005, 0.995]).values
        amin, amax = alk.quantile([0.005, 0.995]).values
        self.alk_range = np.linspace(amin, amax, n_vals)  # ALK
        self.dic_range = np.linspace(dmin, dmax, n_vals)  # DIC
        self.temp_range = np.linspace(-2, 31, 20)  # SST

        self.var_names = [
            ["OmegaARin", r"$\Omega _{{ar}}$"],
            ["pHinTOTAL", "H$^{{+}}$"],
            ["pCO2in", "pCO$_2$"],
        ]

    def calc(self, target: str, return_figure=True):

        def rbin(x):
            diff = np.nanmedian(np.diff(x))
            hdiff = diff / 2.0
            x0 = x.min() - hdiff
            x1 = x.max() + diff
            range = np.arange(x0, x1, diff)
            return range

        x = self.alk_range
        y = self.dic_range
        z = self.temp_range
        zz, yy, xx = np.meshgrid(z, y, x, indexing="ij")

        print(f"calculating sensitivity for n = {zz.size}")
        df = CO2SYS_wrap(temp_in=zz, dic=yy, alk=xx, verbose=False)

        out = xr.DataArray(
            df[target].values.reshape(xx.shape),
            dims=["temp", "dic", "alk"],
            coords=dict(temp=z, dic=y, alk=x),
        )
        self.results_df_ = df
        self.results_ds_ = out

        if "pH" in target:
            target = target.replace("pHin", "H+")
            print(f"`target` ({target}) is now [H+] instead of pH (10**(-pH) * 1e9)")
            out = 10 ** (-out) * 1e9
        outL = np.log(out)

        trends = outL.polyfit("temp", 1).polyfit_coefficients[0]
        weights = xr.DataArray(
            np.histogram2d(
                self.dic.values.flatten(), self.alk.values.flatten(), bins=[rbin(y), rbin(x)]
            )[0],
            dims=["dic", "alk"],
            coords=dict(dic=y, alk=x),
        )
        avg = trends.weighted(weights).mean().values
        std = ((trends - avg) ** 2).weighted(weights).mean().values ** 0.5

        trends = trends.assign_attrs(
            description="Sensitivity of target to changes in temperature",
            target=target,
            dic_range=y[[0, -1]],
            alk_range=x[[0, -1]],
            temp_range=z[[0, -1]],
            data_weighted_average=np.around(avg, 5),
            data_weighted_std=np.around(std, 6),
        )

        self.trends_ = trends

        if return_figure:
            img = self.plot(trends)
            return trends, img
        else:
            return trends

    def plot(self, trends: xr.DataArray, ax=None, **kwargs):
        import seaborn as sns
        import xarray as xr
        from matplotlib import pyplot as plt

        thinned = (
            xr.merge([self.dic.rename("dic"), self.alk.rename("alk")])
            .to_dataframe()
            .dropna()[500::10000]
        )

        if ax is None:
            fig, ax = plt.subplots(dpi=120, figsize=[5.2, 4.5])

        props = dict(levels=21, cmap=plt.cm.viridis)
        props.update(kwargs)
        img = trends.plot.contourf(ax=ax, cbar_kwargs=dict(pad=0.02, aspect=15), **props)

        xlim, ylim = ax.get_xlim(), ax.get_ylim()
        sns.kdeplot(
            ax=ax, y="dic", x="alk", data=thinned, clip=[1800, 2500], linewidths=1, color="k"
        )

        ax.set_xlim(xlim)
        ax.set_ylim(ylim)
        ax.set_xlabel("Total alkalinity (µmol/kg)")
        ax.set_ylabel("DIC (µmol/kg)")
        ax.set_title(f"Temperature sensitivity of {trends.attrs['target']}")

        title = f"{trends.attrs['data_weighted_average']: .4f} ± {trends.attrs['data_weighted_std']: .4f} / °C"
        ax.text(
            0.98, 0.03, title, transform=ax.transAxes, ha="right", bbox=dict(fc="w"), clip_on=True
        )

        return img

    def plot_all(self):
        from matplotlib import pyplot as plt

        fig, ax = plt.subplots(3, 1, figsize=[4, 8])
        for i, (key, name) in enumerate(self.var_names):
            trends = self.calc(target=key)
            img = self.plot(trends, ax=ax[i], levels=11)
            img.colorbar.set_label(f"∆ log({name}) / °C")
            img.axes.set_title(f"Temperature / {name} relationship")

        fig.tight_layout()
        return fig, ax

    def table_of_sensitivities(self):
        import pandas as pd

        df = pd.DataFrame()
        cols = ["avg", "std"]
        keys = ["data_weighted_average", "data_weighted_std"]
        func = lambda d, l: [d[k] for k in l]

        df.loc["betaT", cols] = func(self.calc("pHinTOTAL").attrs, keys)
        df.loc["omegaT", cols] = func(self.calc("OmegaARin").attrs, keys)
        df.loc["gammaT", cols] = func(self.calc("pCO2in").attrs, keys)

        return df

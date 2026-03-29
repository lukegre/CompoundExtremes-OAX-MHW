import pathlib
import warnings
from dataclasses import dataclass
from typing import Literal, Self

import xarray as xr
import yaml
from zarr.errors import ZarrUserWarning


@dataclass(frozen=False, match_args=False)
class DataFnames:
    oax: str
    mhw: str
    cex: str
    masks: str
    aux: str

    @classmethod
    def from_yaml(cls, path: str | pathlib.Path) -> Self:
        with open(path) as f:
            data = yaml.safe_load(f)
        return cls(**data)

    def add_caching(self, cache_type: Literal["simplecache", "filecache"] = "simplecache") -> Self:
        def add_cache_prefix(path: str) -> str:
            return f"{cache_type}::{path}"

        return self.__class__(
            oax=add_cache_prefix(self.oax),
            mhw=add_cache_prefix(self.mhw),
            cex=add_cache_prefix(self.cex),
            masks=add_cache_prefix(self.masks),
            aux=add_cache_prefix(self.aux),
        )


@dataclass
class Datasets:
    oax: xr.Dataset
    mhw: xr.Dataset
    cex: xr.Dataset
    masks: xr.Dataset
    aux: xr.Dataset

    def __getitem__(self, name: str) -> xr.Dataset:
        return getattr(self, name)

    @classmethod
    def from_fnames(cls, fnames: DataFnames, with_cache: bool = False) -> Self:
        if with_cache:
            fnames = fnames.add_caching()
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=ZarrUserWarning)
            return cls(
                oax=xr.open_zarr(fnames.oax),
                mhw=xr.open_zarr(fnames.mhw),
                cex=xr.open_zarr(fnames.cex),
                masks=xr.open_zarr(fnames.masks),
                aux=xr.open_zarr(fnames.aux),
            )

    @classmethod
    def from_yaml(cls, path: str | pathlib.Path, with_cache: bool = False) -> Self:
        fnames = DataFnames.from_yaml(path)
        return cls.from_fnames(fnames, with_cache=with_cache)

    def sel(self, **sel_kwargs) -> Self:
        return self.__class__(
            oax=self.oax.sel(**sel_kwargs),
            mhw=self.mhw.sel(**sel_kwargs),
            cex=self.cex.sel(**sel_kwargs),
            masks=self.masks.sel(**sel_kwargs),
            aux=self.aux.sel(**sel_kwargs),
        )

    def apply(self, func: str, **kwargs) -> Self:
        return self.__class__(
            oax=getattr(self.oax, func)(**kwargs),
            mhw=getattr(self.mhw, func)(**kwargs),
            cex=getattr(self.cex, func)(**kwargs),
            masks=getattr(self.masks, func)(**kwargs),
            aux=getattr(self.aux, func)(**kwargs),
        )

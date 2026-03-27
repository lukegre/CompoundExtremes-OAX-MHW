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

    @classmethod
    def from_yaml(cls, path: str) -> Self:
        with open(path) as f:
            data = yaml.safe_load(f)
        return cls(**data)

    def add_caching(
        self, cache_type: Literal["simplecache", "filecache"] = "simplecache"
    ) -> Self:
        def add_cache_prefix(path: str) -> str:
            return f"{cache_type}::{path}"

        return self.__class__(
            oax=add_cache_prefix(self.oax),
            mhw=add_cache_prefix(self.mhw),
            cex=add_cache_prefix(self.cex),
            masks=add_cache_prefix(self.masks),
        )


@dataclass
class Datasets:
    oax: xr.Dataset
    mhw: xr.Dataset
    cex: xr.Dataset
    masks: xr.Dataset

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
            )

    @classmethod
    def from_yaml(cls, path: str, with_cache: bool = False) -> Self:
        fnames = DataFnames.from_yaml(path)
        return cls.from_fnames(fnames, with_cache=with_cache)

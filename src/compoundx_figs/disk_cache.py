"""
A simple disk cache decorator for Python functions that
uses the same style as functools.lru_cache, but persists
xarray results to disk as zarr. Cache keys are derived
from a fast hash of argument metadata — safe for stable
scientific workflows where the same inputs reliably
produce the same outputs.

Usage
-----
    from xrzarr import disk_cache

    @disk_cache(cache_dir="~/.cache/my_project")
    def compute_frac_robust(deseas, uncert, mask) -> xr.DataArray:
        ...

"""

from __future__ import annotations

import functools
import hashlib
import inspect
from pathlib import Path
from typing import Any, Callable

import numpy as np
import xarray as xr
from loguru import logger


class XRZarrCache:
    """
    Persist xarray function results to disk as zarr stores.

    The instance itself is callable and can be used directly as a decorator.
    Cache keys are derived from the wrapped function identity and a stable
    hash of the bound arguments.
    """

    _RESULT_TYPE_ATTR = "_xrzarr_cache_result_type"
    _DATAARRAY_NAME_ATTR = "_xrzarr_cache_dataarray_name"
    _DATAARRAY_DEFAULT_NAME = "__xrzarr_cache_dataarray__"

    def __init__(self, cache_dir: str | Path):
        self.cache_dir = Path(cache_dir).expanduser().resolve()

    def __call__(self, fn: Callable) -> Callable:
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            self.cache_dir.mkdir(parents=True, exist_ok=True)

            key = self.make_cache_key(fn, args, kwargs)
            cache_path = self.cache_dir / key

            if cache_path.exists():
                try:
                    logger.debug(f"Loading cached zarr result: {cache_path}")
                    return self.load(cache_path)

                except Exception as e:
                    logger.warning(f"Error loading cached result: {e}")

            result = fn(*args, **kwargs)
            self.save(cache_path, result)
            return result

        setattr(wrapper, "cache_dir", self.cache_dir)
        setattr(wrapper, "cache_backend", self)
        return wrapper

    @classmethod
    def hash_value(cls, value: Any) -> str:
        h = hashlib.sha256()
        h.update(type(value).__qualname__.encode())

        if isinstance(value, xr.DataArray):
            h.update(str(value.dims).encode())
            h.update(str(value.shape).encode())
            h.update(str(value.dtype).encode())
            h.update(repr(value.name).encode())
            h.update(repr(value.attrs).encode())
            for name, coord in value.coords.items():
                h.update(str(name).encode())
                h.update(np.asarray(coord.values).tobytes())
            return h.hexdigest()

        if isinstance(value, xr.Dataset):
            h.update(str(value.dims).encode())
            h.update(repr(sorted(value.data_vars)).encode())
            h.update(repr(value.attrs).encode())
            for name, variable in value.data_vars.items():
                h.update(str(name).encode())
                h.update(str(variable.dims).encode())
                h.update(str(variable.shape).encode())
                h.update(str(variable.dtype).encode())
            for name, coord in value.coords.items():
                h.update(str(name).encode())
                h.update(np.asarray(coord.values).tobytes())
            return h.hexdigest()

        if isinstance(value, np.ndarray):
            h.update(str(value.shape).encode())
            h.update(str(value.dtype).encode())
            h.update(value.tobytes())
            return h.hexdigest()

        h.update(repr(value).encode())
        return h.hexdigest()

    @classmethod
    def make_cache_key(cls, fn: Callable, args: tuple[Any, ...], kwargs: dict[str, Any]) -> str:
        h = hashlib.sha256()
        fn_module = getattr(fn, "__module__", type(fn).__module__)
        fn_name = getattr(fn, "__qualname__", getattr(fn, "__name__", repr(fn)))
        h.update(f"{fn_module}.{fn_name}".encode())

        try:
            signature = inspect.signature(fn)
            bound = signature.bind(*args, **kwargs)
            bound.apply_defaults()
            items = bound.arguments.items()
        except (TypeError, ValueError):
            items = [*enumerate(args), *sorted(kwargs.items())]

        for key, value in items:
            h.update(str(key).encode())
            h.update(cls.hash_value(value).encode())

        return h.hexdigest()

    def load(self, cache_path: str | Path) -> xr.DataArray | xr.Dataset:
        cache_path = Path(cache_path)
        ds = xr.open_zarr(cache_path)
        result_type = ds.attrs.get(self._RESULT_TYPE_ATTR, "dataset")

        if result_type == "dataarray":
            name = ds.attrs.get(self._DATAARRAY_NAME_ATTR, self._DATAARRAY_DEFAULT_NAME)
            return ds[name]

        return ds

    def save(self, cache_path: str | Path, result: xr.DataArray | xr.Dataset) -> Path:
        cache_path = Path(cache_path)

        if not isinstance(result, xr.DataArray | xr.Dataset):
            raise TypeError("XRZarrCache only supports xarray DataArray or Dataset results")

        if isinstance(result, xr.DataArray):
            name = result.name or self._DATAARRAY_DEFAULT_NAME
            ds = result.to_dataset(name=name)
            ds.attrs = dict(ds.attrs)
            ds.attrs[self._RESULT_TYPE_ATTR] = "dataarray"
            ds.attrs[self._DATAARRAY_NAME_ATTR] = name
        else:
            ds = result.copy(deep=False)
            ds.attrs = dict(ds.attrs)
            ds.attrs[self._RESULT_TYPE_ATTR] = "dataset"

        logger.debug(f"Caching zarr result to: {cache_path}")
        ds.to_zarr(cache_path, mode="w", zarr_format=2)
        return cache_path


def disk_cache(cache_dir: str | Path) -> XRZarrCache:
    return XRZarrCache(cache_dir)

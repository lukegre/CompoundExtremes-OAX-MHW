"""
disk_cache.py
=============
A decorator that persists function outputs to disk as pickle files.
Cache keys are derived from a fast hash of argument metadata — safe for
stable scientific workflows where the same inputs reliably produce the
same outputs.

Usage
-----
from disk_cache import disk_cache

@disk_cache(cache_dir="~/.cache/my_project")
def compute_frac_robust(deseas, uncert, mask) -> xr.DataArray:
    ...
"""

import functools
import hashlib
import inspect
import pickle
from pathlib import Path
from typing import Any, Callable

from loguru import logger

# ---------------------------------------------------------------------------
# Hashing helpers
# ---------------------------------------------------------------------------


def _hash_value(value: Any) -> str:
    """
    Return a hex-digest string for *value*.

    Strategy per type
    -----------------
    xarray.DataArray / Dataset
        shape, dtype, dimension names, coordinate values, and attrs.
        Fast — avoids loading the full underlying array into memory.
    numpy.ndarray
        shape, dtype, and the raw bytes of the array.
    Anything else
        repr() string — handles scalars, strings, slices, dicts, etc.
    """
    h = hashlib.sha256()

    type_name = type(value).__qualname__
    h.update(type_name.encode())

    # ---- xarray ---------------------------------------------------------
    try:
        import xarray as xr  # only imported if present in the environment

        if isinstance(value, (xr.DataArray, xr.Dataset)):
            h.update(str(value.dims).encode())
            h.update(str(value.shape).encode())
            if hasattr(value, "dtype"):  # DataArray
                h.update(str(value.dtype).encode())
            h.update(str(value.attrs).encode())
            for name, coord in value.coords.items():
                h.update(str(name).encode())
                h.update(str(coord.values.tobytes()).encode())
            return h.hexdigest()
    except ImportError:
        pass

    # ---- numpy ----------------------------------------------------------
    try:
        import numpy as np

        if isinstance(value, np.ndarray):
            h.update(str(value.shape).encode())
            h.update(str(value.dtype).encode())
            h.update(value.tobytes())
            return h.hexdigest()
    except ImportError:
        pass

    # ---- fallback -------------------------------------------------------
    h.update(repr(value).encode())
    return h.hexdigest()


def _make_cache_key(fn: Callable, args: tuple, kwargs: dict) -> str:
    """
    Build a single SHA-256 hex digest that uniquely identifies a call to
    *fn* with the given positional and keyword arguments.

    The key encodes:
        - the fully-qualified function name (module + qualname)
        - each positional argument (via _hash_value)
        - each keyword argument name and value (sorted for stability)
    """
    h = hashlib.sha256()

    # Function identity
    fn_id = f"{fn.__module__}.{fn.__qualname__}"
    h.update(fn_id.encode())

    # Normalise: bind *args + **kwargs to the function signature so that
    #   fn(a, b=2)  and  fn(a, b=2)  always collide, even if one is passed
    #   positionally and the other as a keyword.
    try:
        sig = inspect.signature(fn)
        bound = sig.bind(*args, **kwargs)
        bound.apply_defaults()
        items = list(bound.arguments.items())
    except (ValueError, TypeError):
        # Fallback: treat positional and keyword args separately
        items = list(enumerate(args)) + sorted(kwargs.items())

    for key, value in items:
        h.update(str(key).encode())
        h.update(_hash_value(value).encode())

    return h.hexdigest()


# ---------------------------------------------------------------------------
# Decorator
# ---------------------------------------------------------------------------


def disk_cache(cache_dir: str | Path):
    """
    Decorator factory — persist the return value of the wrapped function to
    *cache_dir* as a pickle file named ``<sha256>.pkl``.

    On subsequent calls with identical inputs the cached result is returned
    without executing the function body.

    Parameters
    ----------
    cache_dir : str | Path
        Directory in which cache files are stored.  Created automatically if
        it does not exist.  Supports ``~`` expansion.

    Example
    -------
    >>> @disk_cache(cache_dir="~/.cache/my_project")
    ... def compute_frac_robust(deseas, uncert, mask):
    ...     ...
    """
    cache_path = Path(cache_dir).expanduser().resolve()

    def decorator(fn: Callable) -> Callable:
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            cache_path.mkdir(parents=True, exist_ok=True)

            key = _make_cache_key(fn, args, kwargs)
            fpath = cache_path / f"{key}.pkl"

            if fpath.exists():
                logger.debug(f"Loading cached result: {fpath}")
                with fpath.open("rb") as f:
                    return pickle.load(f)

            result = fn(*args, **kwargs)

            with fpath.open("wb") as f:
                logger.debug(f"Caching result to: {fpath}")
                pickle.dump(result, f, protocol=pickle.HIGHEST_PROTOCOL)

            return result

        # Attach the resolved cache directory for easy inspection
        wrapper.cache_dir = cache_path
        return wrapper

    return decorator

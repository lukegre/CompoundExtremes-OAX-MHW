from dataclasses import dataclass

import xarray as xr
from loguru import logger


@dataclass
class ExtremeVariableInput:
    name: str
    data: xr.DataArray
    data_valid_range: tuple[float, float]

    def __post_init__(self):
        lower = self.data_valid_range[0]
        upper = self.data_valid_range[1]
        if lower >= upper:
            raise ValueError("data_valid_range must be a tuple of (min, max) with min < max")

        logger.info("Persisting data for faster computation")
        self.data = self.data.compute()

        self._validate_data(self.data, lower, upper)

    def _validate_data(self, data: xr.DataArray, lower: float, upper: float):
        name = data.name
        logger.info(
            f"Validating data for variable `{name}` against valid range ({lower}, {upper})..."
        )

        min = data.min().values
        max = data.max().values

        if not ((min >= lower) & (max <= upper)):
            raise ValueError(
                f"Data for variable `{name}` contains values "
                f"outside the valid range ({lower}, {upper}). "
                f"Found min: {min}, max: {max}"
            )

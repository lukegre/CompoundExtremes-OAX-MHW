# ruff: noqa: E402  - ignore module level import not at top of file
# need to load .env before importing any other modules, to make sure S3 credentials are available before xarray import
import dotenv

dotenv.load_dotenv()

from . import extreme_detection as ex
from . import extreme_summary_stats as sumstats  # noqa: E402
from . import vis
from .carbsys_sensitivities import calc_sensitivities
from .convert import ph_to_hplus_nmol
from .disk_cache import disk_cache
from .io import Datasets, get_oni_data
from .utils import get_project_root, suppress_warnings

__all__ = [
    "Datasets",
    "sumstats",
    "suppress_warnings",
    "get_project_root",
    "get_oni_data",
    "calc_sensitivities",
    "ph_to_hplus_nmol",
    "vis",
    "disk_cache",
    "ex",
]

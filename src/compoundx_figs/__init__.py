import dotenv

dotenv.load_dotenv()

from . import extreme_stats as stats
from . import vis
from .io import Datasets
from .utils import get_project_root, suppress_warnings

__all__ = ["Datasets", "stats", "suppress_warnings", "get_project_root"]

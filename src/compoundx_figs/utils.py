import pathlib
import warnings

import dotenv


def suppress_warnings(func):

    def wrapper(*args, **kwargs):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            return func(*args, **kwargs)

    return wrapper


def get_project_root(ref_file="pyproject.toml") -> pathlib.Path:
    """Get the project root directory."""

    fname = dotenv.find_dotenv(ref_file)

    return pathlib.Path(fname).parent.absolute().resolve()

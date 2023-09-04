
from pathlib import Path

with open(Path(__file__).parent / "version.py") as _version_file:
    __version__ = _version_file.read().strip()


from .floris_interface import WCompFloris
from .foxes_interface import WCompFoxes
from .pywake_interface import WCompPyWake

"""cummand — lightweight HTTP tunnel server and client."""

from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("cummand")
except PackageNotFoundError:
    __version__ = "0.0.0"

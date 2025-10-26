"""PowRAR - a next-generation file compression toolkit."""

from .compression import (
    CompressionSettings,
    DecompressionSettings,
    OperationCancelled,
    compress,
    decompress,
    default_archive_name,
)
from .gui import PowRARApp, run_app

__all__ = [
    "CompressionSettings",
    "DecompressionSettings",
    "OperationCancelled",
    "compress",
    "decompress",
    "default_archive_name",
    "PowRARApp",
    "run_app",
]

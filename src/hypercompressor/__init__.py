"""Hypercompressor - high-performance modular compression toolkit."""

from .core import Compressor, CompressionSettings
from .strategies import AVAILABLE_CODECS

__all__ = [
    "Compressor",
    "CompressionSettings",
    "AVAILABLE_CODECS",
]

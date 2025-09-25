"""Codec strategies available for the Hypercompressor pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, Protocol
import lzma


class Codec(Protocol):
    """Protocol for codec implementations."""

    name: str

    def compress(self, data: bytes) -> bytes:
        """Compress a block of data and return the compressed bytes."""

    def decompress(self, data: bytes) -> bytes:
        """Decompress a block of data and return the original bytes."""


@dataclass(frozen=True)
class LZMACodec:
    """LZMA codec using the built-in Python implementation."""

    name: str = "lzma"
    preset: int = 6

    def compress(self, data: bytes) -> bytes:  # noqa: D401 - short description inherited
        return lzma.compress(data, preset=self.preset, format=lzma.FORMAT_XZ)

    def decompress(self, data: bytes) -> bytes:  # noqa: D401 - short description inherited
        return lzma.decompress(data, format=lzma.FORMAT_XZ)


AVAILABLE_CODECS: Iterable[Codec] = (LZMACodec(),)

CODEC_BY_NAME: Dict[str, Codec] = {codec.name: codec for codec in AVAILABLE_CODECS}


def get_codec(name: str) -> Codec:
    """Return a codec implementation by name.

    Raises:
        KeyError: If the codec name is unknown.
    """

    try:
        return CODEC_BY_NAME[name]
    except KeyError as exc:  # pragma: no cover - defensive branch
        raise KeyError(f"Codec '{name}' is not registered") from exc

"""Core compression pipeline for Hypercompressor."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import BinaryIO, List, Tuple
from concurrent.futures import Future, ThreadPoolExecutor
import os
import struct

from .strategies import Codec, LZMACodec, get_codec

MAGIC = b"HCZ1"
VERSION = 1
HEADER_FORMAT = "<4sBQIHB"
CHUNK_HEADER = struct.Struct("<I")


@dataclass(slots=True)
class CompressionSettings:
    """Configuration for compression operations."""

    codec: Codec = field(default_factory=LZMACodec)
    chunk_size: int = 1024 * 1024  # 1 MiB
    max_workers: int | None = None

    def __post_init__(self) -> None:
        if self.chunk_size <= 0:
            msg = "chunk_size must be positive"
            raise ValueError(msg)


class Compressor:
    """High-level API for compressing and decompressing streams."""

    def __init__(self, settings: CompressionSettings | None = None) -> None:
        self.settings = settings or CompressionSettings()

    def compress_file(self, source: os.PathLike[str] | str, target: os.PathLike[str] | str) -> None:
        """Compress ``source`` into ``target`` using the configured settings."""

        source_path = Path(source)
        target_path = Path(target)
        codec = self.settings.codec

        chunk_futures: List[Tuple[int, Future[bytes]]] = []
        with source_path.open("rb") as src, target_path.open("wb") as dst:
            original_size = _stream_size(src)
            _write_header(dst, codec, self.settings.chunk_size, original_size)
            with ThreadPoolExecutor(max_workers=self.settings.max_workers) as executor:
                index = 0
                while True:
                    chunk = src.read(self.settings.chunk_size)
                    if not chunk:
                        break
                    future = executor.submit(codec.compress, chunk)
                    chunk_futures.append((index, future))
                    index += 1

                for _, future in chunk_futures:
                    compressed = future.result()
                    dst.write(CHUNK_HEADER.pack(len(compressed)))
                    dst.write(compressed)

    def decompress_file(self, source: os.PathLike[str] | str, target: os.PathLike[str] | str) -> None:
        """Decompress ``source`` archive into ``target`` file."""

        source_path = Path(source)
        target_path = Path(target)

        with source_path.open("rb") as src, target_path.open("wb") as dst:
            codec, expected_size = _read_header(src)
            total_written = 0
            while True:
                chunk_header = src.read(CHUNK_HEADER.size)
                if not chunk_header:
                    break
                if len(chunk_header) != CHUNK_HEADER.size:
                    raise ValueError("Truncated chunk header encountered")
                (chunk_size,) = CHUNK_HEADER.unpack(chunk_header)
                compressed_data = src.read(chunk_size)
                if len(compressed_data) != chunk_size:
                    raise ValueError("Unexpected end of file while reading compressed chunk")
                data = codec.decompress(compressed_data)
                dst.write(data)
                total_written += len(data)

        if expected_size is not None and total_written != expected_size:
            raise ValueError(
                "Decompressed size does not match header metadata: "
                f"expected {expected_size}, wrote {total_written}"
            )


def _stream_size(stream: BinaryIO) -> int | None:
    """Return the size of the file behind ``stream`` without consuming the cursor."""

    try:
        current = stream.tell()
        stream.seek(0, os.SEEK_END)
        size = stream.tell()
        stream.seek(current)
        return size
    except (OSError, AttributeError):  # pragma: no cover - stream not seekable
        return None


def _write_header(dst: BinaryIO, codec: Codec, chunk_size: int, original_size: int | None) -> None:
    """Write the archive header."""

    codec_name = codec.name.encode("utf-8")
    original_size_value = original_size if original_size is not None else 0
    has_size_flag = 1 if original_size is not None else 0
    header = struct.pack(
        HEADER_FORMAT,
        MAGIC,
        VERSION,
        chunk_size,
        original_size_value,
        len(codec_name),
        has_size_flag,
    )
    dst.write(header)
    dst.write(codec_name)


def _read_header(src: BinaryIO) -> tuple[Codec, int | None]:
    """Read archive metadata and return codec + expected size."""

    header_size = struct.calcsize(HEADER_FORMAT)
    header_prefix = src.read(header_size)
    if len(header_prefix) != header_size:
        raise ValueError("Invalid or truncated header")
    magic, version, chunk_size, original_size, name_length, has_size_flag = struct.unpack(
        HEADER_FORMAT, header_prefix
    )
    if magic != MAGIC:
        raise ValueError("Invalid archive signature")
    if version != VERSION:
        raise ValueError(f"Unsupported archive version: {version}")
    if chunk_size <= 0:
        raise ValueError("Chunk size must be positive")
    codec_name_bytes = src.read(name_length)
    if len(codec_name_bytes) != name_length:
        raise ValueError("Truncated codec name in header")
    codec_name = codec_name_bytes.decode("utf-8")
    codec = get_codec(codec_name)
    expected_size = original_size if has_size_flag else None
    return codec, expected_size

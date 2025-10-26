"""High-performance archive compression and decompression utilities.

This module provides streaming helpers that combine ``tarfile`` with
``lzma`` to produce highly-compressed archives. The goal is to offer a
modern alternative to traditional tools such as WinRAR with a focus on
speed, compression ratio and safe extraction.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import tarfile
import threading
from typing import Callable, Iterable, Iterator, List, Optional, Tuple
import lzma


ProgressCallback = Callable[[int, int], None]


class OperationCancelled(RuntimeError):
    """Raised when a long-running operation is cancelled by the user."""


@dataclass
class CompressionSettings:
    """Settings used by the compression helpers."""

    level: int = 9
    block_size: int = 64 * 1024 * 1024  # 64 MiB default block size

    def __post_init__(self) -> None:
        self.level = max(0, min(9, int(self.level)))
        self.block_size = max(1 * 1024 * 1024, int(self.block_size))


@dataclass
class DecompressionSettings:
    """Settings used by the decompression helpers."""

    block_size: int = 64 * 1024 * 1024

    def __post_init__(self) -> None:
        self.block_size = max(1 * 1024 * 1024, int(self.block_size))


_ARCHIVE_SUFFIX = ".pwr"


def default_archive_name(target: Path) -> Path:
    """Return a valid archive path for the requested *target*.

    Parameters
    ----------
    target:
        Desired archive name. The ``.pwr`` suffix is automatically appended
        if missing.
    """

    target = Path(target)
    if target.suffix != _ARCHIVE_SUFFIX:
        target = target.with_suffix(_ARCHIVE_SUFFIX)
    return target


# -- Internal helpers -----------------------------------------------------

def _iter_root_items(items: Iterable[Path]) -> List[Tuple[Path, Path]]:
    """Normalize the *items* supplied by the user.

    Returns a list of tuples ``(path, base)`` where ``base`` represents the
    parent directory used to compute archive-relative paths. The ordering is
    stable which keeps the resulting archive deterministic.
    """

    normalized: List[Tuple[Path, Path]] = []
    for item in items:
        path = Path(item).resolve()
        if not path.exists():
            raise FileNotFoundError(f"Path does not exist: {path}")
        if path.is_dir():
            normalized.append((path, path.parent))
        else:
            normalized.append((path, path.parent))
    return sorted(normalized, key=lambda pair: str(pair[0]))


def _iter_directories(path: Path) -> Iterator[Path]:
    yield path
    for subdir in sorted(p for p in path.rglob("*") if p.is_dir()):
        yield subdir


def _iter_files(path: Path) -> Iterator[Path]:
    for file in sorted(p for p in path.rglob("*") if p.is_file()):
        yield file


def _calc_total_size(pairs: Iterable[Tuple[Path, Path]]) -> int:
    total = 0
    for path, _ in pairs:
        if path.is_file():
            total += path.stat().st_size
        else:
            for file in _iter_files(path):
                total += file.stat().st_size
    return total


# -- Public API -----------------------------------------------------------

def compress(
    items: Iterable[Path],
    destination: Path,
    *,
    settings: Optional[CompressionSettings] = None,
    progress: Optional[ProgressCallback] = None,
    cancel_event: Optional[threading.Event] = None,
) -> Path:
    """Create an archive containing *items*.

    Parameters
    ----------
    items:
        Collection of file system entries to store in the archive. Both files
        and directories are supported.
    destination:
        Desired archive path. The ``.pwr`` suffix will be appended automatically.
    settings:
        Optional :class:`CompressionSettings` instance to customize compression
        level and block size.
    progress:
        Optional callable receiving ``(processed_bytes, total_bytes)``.
    cancel_event:
        Optional :class:`threading.Event` used to abort the operation.

    Returns
    -------
    Path to the generated archive.
    """

    dest = default_archive_name(Path(destination))
    settings = settings or CompressionSettings()
    pairs = _iter_root_items(items)
    if not pairs:
        raise ValueError("At least one item must be supplied")

    total_size = max(_calc_total_size(pairs), 1)
    processed = 0

    if progress:
        progress(0, total_size)

    filter_event = cancel_event

    with lzma.open(dest, "wb", preset=settings.level, format=lzma.FORMAT_XZ, check=lzma.CHECK_CRC64) as lzma_file:
        with tarfile.open(fileobj=lzma_file, mode="w|") as tar:
            for path, base in pairs:
                if filter_event and filter_event.is_set():
                    raise OperationCancelled("Compression cancelled")

                if path.is_dir():
                    for directory in _iter_directories(path):
                        arcname = str(directory.relative_to(base))
                        tarinfo = tar.gettarinfo(str(directory), arcname)
                        tar.addfile(tarinfo)
                        if filter_event and filter_event.is_set():
                            raise OperationCancelled("Compression cancelled")

                    for file in _iter_files(path):
                        if filter_event and filter_event.is_set():
                            raise OperationCancelled("Compression cancelled")

                        arcname = str(file.relative_to(base))
                        tarinfo = tar.gettarinfo(str(file), arcname)
                        with file.open("rb") as stream:
                            tar.addfile(tarinfo, stream)
                        processed += tarinfo.size
                        if progress:
                            progress(processed, total_size)
                else:
                    arcname = str(path.relative_to(base))
                    tarinfo = tar.gettarinfo(str(path), arcname)
                    with path.open("rb") as stream:
                        tar.addfile(tarinfo, stream)
                    processed += tarinfo.size
                    if progress:
                        progress(processed, total_size)

    if progress:
        progress(total_size, total_size)

    return dest


def _safe_extract_member(tar: tarfile.TarFile, member: tarfile.TarInfo, target_dir: Path) -> None:
    target_dir = target_dir.resolve()
    resolved_path = target_dir.joinpath(member.name).resolve()
    if not str(resolved_path).startswith(str(target_dir)):
        raise RuntimeError(f"Unsafe path detected in archive: {member.name}")
    tar.extract(member, path=target_dir)


def decompress(
    archive: Path,
    destination: Path,
    *,
    settings: Optional[DecompressionSettings] = None,
    progress: Optional[ProgressCallback] = None,
    cancel_event: Optional[threading.Event] = None,
) -> Path:
    """Extract *archive* into the provided *destination* directory."""

    archive = Path(archive)
    if not archive.exists():
        raise FileNotFoundError(f"Archive not found: {archive}")

    settings = settings or DecompressionSettings()
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)

    with tarfile.open(archive, "r:xz") as tar:
        members = tar.getmembers()
        total_size = max(sum(member.size for member in members if member.isfile()), 1)
        processed = 0

        if progress:
            progress(0, total_size)

        for member in members:
            if cancel_event and cancel_event.is_set():
                raise OperationCancelled("Extraction cancelled")
            _safe_extract_member(tar, member, destination)
            if member.isfile():
                processed += member.size
                if progress:
                    progress(processed, total_size)

    if progress:
        progress(total_size, total_size)

    return destination


__all__ = [
    "CompressionSettings",
    "DecompressionSettings",
    "OperationCancelled",
    "compress",
    "decompress",
    "default_archive_name",
]

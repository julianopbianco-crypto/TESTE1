from __future__ import annotations

import filecmp
import os
from pathlib import Path

import pytest

from powrar.compression import CompressionSettings, decompress, compress


@pytest.fixture()
def sample_tree(tmp_path: Path) -> Path:
    root = tmp_path / "data"
    root.mkdir()

    (root / "docs").mkdir()
    (root / "docs" / "manual.txt").write_text("PowRAR Manual\n", encoding="utf-8")
    (root / "docs" / "readme.md").write_text("# Guia\nPowRAR é incrível!\n", encoding="utf-8")

    (root / "media").mkdir()
    (root / "media" / "image.bin").write_bytes(os.urandom(64_000))

    (root / "empty").mkdir()

    (root / "root.txt").write_text("Arquivo na raiz\n", encoding="utf-8")
    return root


def _compare_trees(left: Path, right: Path) -> None:
    comp = filecmp.dircmp(left, right)
    assert not comp.left_only
    assert not comp.right_only
    assert not comp.funny_files

    _, mismatch, errors = filecmp.cmpfiles(left, right, comp.common_files, shallow=False)
    assert not mismatch
    assert not errors

    for common_dir in comp.common_dirs:
        _compare_trees(left / common_dir, right / common_dir)


def test_compress_and_decompress_roundtrip(tmp_path: Path, sample_tree: Path) -> None:
    destination = tmp_path / "backup.pwr"

    progress_updates: list[tuple[int, int]] = []

    archive = compress(
        [sample_tree],
        destination,
        settings=CompressionSettings(level=9),
        progress=lambda done, total: progress_updates.append((done, total)),
    )
    assert archive.exists()

    target_dir = tmp_path / "restored"
    decompress(archive, target_dir)

    _compare_trees(sample_tree, target_dir / sample_tree.name)
    assert progress_updates
    assert progress_updates[0][0] <= progress_updates[-1][0]


def test_compress_requires_items(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        compress([], tmp_path / "out.pwr")


def test_decompress_missing_archive(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        decompress(tmp_path / "missing.pwr", tmp_path / "target")

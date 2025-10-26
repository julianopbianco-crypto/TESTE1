from __future__ import annotations

from pathlib import Path

import pytest

from hypercompressor.cli import run_cli
from hypercompressor.core import CompressionSettings, Compressor
from hypercompressor.strategies import CODEC_BY_NAME


def create_sample_file(path: Path, size: int) -> bytes:
    data = bytearray()
    for i in range(size):
        data.append((i * 37) % 256)
    path.write_bytes(data)
    return bytes(data)


def test_roundtrip_preserves_data(tmp_path: Path) -> None:
    source = tmp_path / "input.bin"
    expected = create_sample_file(source, size=128_000)

    archive = tmp_path / "input.hcz"
    output = tmp_path / "output.bin"

    settings = CompressionSettings(codec=CODEC_BY_NAME["lzma"], chunk_size=8192, max_workers=2)
    compressor = Compressor(settings=settings)
    compressor.compress_file(source, archive)
    compressor.decompress_file(archive, output)

    assert output.read_bytes() == expected


def test_cli_compress_and_decompress(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source = tmp_path / "cli.txt"
    archive = tmp_path / "cli.hcz"
    restored = tmp_path / "cli_restored.txt"

    source.write_text("Hypercompressor CLI test\n" * 100)

    exit_code = run_cli([
        "--codec",
        "lzma",
        "--chunk-size",
        "4096",
        "compress",
        str(source),
        str(archive),
    ])
    assert exit_code == 0
    assert archive.exists()

    exit_code = run_cli([
        "--codec",
        "lzma",
        "decompress",
        str(archive),
        str(restored),
    ])
    assert exit_code == 0
    assert restored.read_text() == source.read_text()

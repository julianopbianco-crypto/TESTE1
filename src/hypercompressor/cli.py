"""Command line interface for Hypercompressor."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from .core import CompressionSettings, Compressor
from .strategies import CODEC_BY_NAME


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="hypercompress",
        description="Compactador modular de alta performance",
    )
    parser.add_argument(
        "--codec",
        choices=sorted(CODEC_BY_NAME.keys()),
        default="lzma",
        help="Codec a ser utilizado (default: %(default)s)",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=1024 * 1024,
        help="Tamanho do bloco em bytes para processar (default: %(default)s)",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=None,
        help="Número máximo de threads para compressão (default: auto)",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    compress_parser = subparsers.add_parser("compress", help="Compacta um arquivo")
    compress_parser.add_argument("source", type=Path)
    compress_parser.add_argument("target", type=Path)

    decompress_parser = subparsers.add_parser("decompress", help="Descompacta um arquivo")
    decompress_parser.add_argument("source", type=Path)
    decompress_parser.add_argument("target", type=Path)

    return parser


def run_cli(args: Sequence[str] | None = None) -> int:
    parser = build_parser()
    namespace = parser.parse_args(args=args)

    settings = CompressionSettings(
        codec=CODEC_BY_NAME[namespace.codec],
        chunk_size=namespace.chunk_size,
        max_workers=namespace.workers,
    )
    compressor = Compressor(settings=settings)

    if namespace.command == "compress":
        compressor.compress_file(namespace.source, namespace.target)
    elif namespace.command == "decompress":
        compressor.decompress_file(namespace.source, namespace.target)
    else:  # pragma: no cover - handled by argparse
        parser.error("Comando desconhecido")
    return 0


def main() -> None:
    raise SystemExit(run_cli())


if __name__ == "__main__":  # pragma: no cover
    main()

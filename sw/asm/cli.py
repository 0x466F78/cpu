import argparse
import os
import sys

from .assembler import Assembler
from .output import write_listing, write_memfile, write_memory_map


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python3 -m sw",
        description="RISC16 assembler — 16-bit single-cycle Harvard.",
    )
    parser.add_argument("source", help="berkas sumber .asm")
    parser.add_argument("-o", "--output", help="berkas .mem keluaran (default: <source>.mem)")
    parser.add_argument("-l", "--listing", help="berkas .lst listing")
    parser.add_argument("-m", "--memory-map", help="berkas peta memori .txt")
    parser.add_argument("-q", "--quiet", action="store_true")
    return parser


def main(argv=None) -> int:
    args = _build_parser().parse_args(argv)
    output_path = args.output or os.path.splitext(args.source)[0] + ".mem"

    try:
        with open(args.source, encoding="utf-8") as f:
            source = f.read()
    except FileNotFoundError:
        print(f"error: berkas tidak ditemukan: {args.source}", file=sys.stderr)
        return 1

    result = Assembler().assemble(source)

    for diagnostic in result.diagnostics.items:
        print(diagnostic.render(args.source), file=sys.stderr)
    if not result.ok:
        error_count = len(result.diagnostics.errors)
        print(f"\n{error_count} error, tidak ada keluaran.", file=sys.stderr)
        return 1

    write_memfile(output_path, result.words)
    if args.listing:
        write_listing(args.listing, result, source.split("\n"))
    if args.memory_map:
        write_memory_map(args.memory_map, result)

    if not args.quiet:
        print(f"OK: {args.source} → {output_path}  ({len(result.words)} kata)")
        if args.listing:
            print(f"    listing    : {args.listing}")
        if args.memory_map:
            print(f"    memory map : {args.memory_map}")
    return 0

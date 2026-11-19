from typing import List

from .assembler import AssemblyResult
from .isa import (IO_KBDDT, IO_KBDST, IO_TTY, RAM_END, RAM_SIZE, RAM_START,
                  ROM_END, ROM_SIZE)


def _hex_words(words: List[int]) -> str:
    return " ".join(f"{word:04X}" for word in words)


def write_memfile(path: str, words: List[int], per_line: int = 8) -> None:
    """Format Logisim-evolution: header 'v2.0 raw', lalu hex 4 digit per kata."""
    with open(path, "w", encoding="utf-8") as f:
        f.write("v2.0 raw\n")
        for i in range(0, len(words), per_line):
            f.write(_hex_words(words[i:i + per_line]) + "\n")


def write_listing(path: str, result: AssemblyResult, source_lines: List[str]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        f.write("; RISC16 Assembler — Listing\n")
        f.write("; line   addr     hex                 source\n")
        f.write("; ----   ------   ------------------  -----------------------------\n")

        for entry in result.layout:
            stmt = entry.statement
            index = stmt.line_no - 1
            source = source_lines[index].rstrip() if index < len(source_lines) else ""
            if stmt.body is None and not stmt.labels and not source.strip():
                f.write("\n")
                continue

            words = result.words[entry.addr:entry.addr + entry.size]
            f.write(f"  {stmt.line_no:>4}   0x{entry.addr:04X}   "
                    f"{_hex_words(words):<18}  {source}\n")


def write_memory_map(path: str, result: AssemblyResult) -> None:
    used = len(result.words)
    lines = [
        "RISC16 Memory Map",
        "=================",
        "",
        f"Program ROM ({ROM_SIZE // 1024}K words):",
        f"  0x0000 - 0x{max(used - 1, 0):04X}  digunakan  ({used} words)",
        f"  0x{used:04X} - 0x{ROM_END:04X}  kosong",
        "",
        f"Data RAM ({RAM_SIZE // 1024}K words):",
        f"  0x{RAM_START:04X} - 0x{RAM_END:04X}",
        "",
        "I/O (memory-mapped):",
        f"  0x{IO_TTY:04X}  TTY Output   (write)",
        f"  0x{IO_KBDST:04X}  KBD Status   (read)",
        f"  0x{IO_KBDDT:04X}  KBD Data     (read, auto-clear)",
        "",
        "Symbols:",
    ]

    symbols = result.symbols.all()
    if not symbols:
        lines.append("  (kosong)")
    for symbol in symbols:
        lines.append(f"  0x{symbol.value:04X}  {symbol.kind:<5}  {symbol.name}  "
                     f"(line {symbol.line_no})")

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

from dataclasses import dataclass
from enum import Enum
from typing import Dict, Optional, Tuple

# ---------- Peta memori ----------

ROM_START = 0x0000
ROM_SIZE = 0x1000
ROM_END = ROM_START + ROM_SIZE - 1

RAM_START = 0x2000
RAM_SIZE = 0x1000
RAM_END = RAM_START + RAM_SIZE - 1

IO_TTY = 0x4000
IO_KBDST = 0x4001
IO_KBDDT = 0x4002

# ---------- Register ----------

NUM_REGISTERS = 8


def parse_register(name: str) -> Optional[int]:
    """'r0'..'r7' (huruf besar atau kecil) menjadi 0..7, selain itu None."""
    if len(name) == 2 and name[0] in "rR" and name[1].isdigit():
        number = int(name[1])
        if number < NUM_REGISTERS:
            return number
    return None


def is_register_name(name: str) -> bool:
    return parse_register(name) is not None


# ---------- Instruksi ----------

class OperandKind(Enum):
    REG = "reg"         # rX
    MEM = "mem"         # (rX)
    IMM = "imm"         # konstanta 8-bit
    TARGET = "target"   # tujuan cabang: label atau offset angka


@dataclass(frozen=True)
class InstructionSpec:
    mnemonic: str
    opcode: Optional[int]    # None untuk pseudo-instruksi
    operands: Tuple[OperandKind, ...]


_REG, _MEM, _IMM, _TARGET = (OperandKind.REG, OperandKind.MEM,
                             OperandKind.IMM, OperandKind.TARGET)

_NATIVE = [
    ("add",  0x0, (_REG, _REG, _REG)),
    ("sub",  0x1, (_REG, _REG, _REG)),
    ("mul",  0x2, (_REG, _REG, _REG)),
    ("div",  0x3, (_REG, _REG, _REG)),
    ("jalr", 0x4, (_REG, _REG, _REG)),
    ("sw",   0x5, (_REG, _MEM)),
    ("lw",   0x6, (_REG, _MEM)),
    ("rem",  0x7, (_REG, _REG, _REG)),
    ("lhi",  0x8, (_REG, _IMM)),
    ("lli",  0x9, (_REG, _IMM)),
    ("andn", 0xA, (_REG, _REG, _REG)),
    ("xor",  0xB, (_REG, _REG, _REG)),
    ("bnz",  0xD, (_REG, _TARGET)),
    ("bz",   0xE, (_REG, _TARGET)),
    ("bltz", 0xF, (_REG, _TARGET)),
]

_PSEUDO = [
    ("li",  (_REG, _IMM)),
    ("nop", ()),
    ("mov", (_REG, _REG)),
    ("b",   (_TARGET,)),
]

INSTRUCTIONS: Dict[str, InstructionSpec] = {
    name: InstructionSpec(name, opcode, operands)
    for name, opcode, operands in _NATIVE
}

PSEUDO: Dict[str, InstructionSpec] = {
    name: InstructionSpec(name, None, operands)
    for name, operands in _PSEUDO
}


def lookup_spec(mnemonic: str) -> Optional[InstructionSpec]:
    name = mnemonic.lower()
    return INSTRUCTIONS.get(name) or PSEUDO.get(name)


def opcode_of(mnemonic: str) -> int:
    return INSTRUCTIONS[mnemonic].opcode


# ---------- Direktif ----------

STRING_DIRECTIVES = {"ascii", "asciz", "string"}

DIRECTIVES = {"org", "equ", "word", "space", "zero", "align"} | STRING_DIRECTIVES

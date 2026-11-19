from typing import List, Optional

from .ast_nodes import Directive, Instruction
from .diagnostics import DiagnosticBag
from .expressions import evaluate, is_bit_pattern, references_label
from .isa import STRING_DIRECTIVES, opcode_of
from .symbols import SymbolTable


def _r_format(opcode: int, dst: int, x: int, y: int) -> int:
    return (opcode << 12) | (dst << 8) | (x << 4) | y


def _i_format(opcode: int, dst: int, imm: int) -> int:
    return (opcode << 12) | (dst << 8) | (imm & 0xFF)


def string_data(directive: Directive) -> List[int]:
    """Kata untuk .ascii/.asciz/.string. Selain .ascii diakhiri nol."""
    words = [ord(char) & 0xFFFF for char in directive.args[0]]
    if directive.name != "ascii":
        words.append(0)
    return words


class Encoder:
    def __init__(self, symbols: SymbolTable, diag: DiagnosticBag):
        self.symbols = symbols
        self.diag = diag
        self._handlers = {
            "nop": self._nop,
            "mov": self._mov,
            "li": self._li,
            "b": self._jump,
            "sw": self._store,
            "lw": self._load,
            "lhi": self._immediate,
            "lli": self._immediate,
            "bnz": self._branch,
            "bz": self._branch,
            "bltz": self._branch,
        }

    # ---------- instruksi ----------

    def encode_instruction(self, instr: Instruction, pc: int) -> Optional[List[int]]:
        """Kembalikan daftar kata, atau None jika ada error."""
        handler = self._handlers.get(instr.mnemonic, self._alu)
        return handler(instr, pc)

    def _value(self, expr, pc: int) -> Optional[int]:
        return evaluate(expr, self.symbols, pc, self.diag)

    def _warn_if_r0(self, instr: Instruction, register: int) -> None:
        if register == 0:
            self.diag.warning(f"'{instr.mnemonic}' menulis ke r0 (konvensi nol)",
                              instr.span)

    def _alu(self, instr, pc):
        dst, x, y = instr.operands
        if instr.mnemonic != "jalr":
            self._warn_if_r0(instr, dst.num)
        return [_r_format(opcode_of(instr.mnemonic), dst.num, x.num, y.num)]

    def _nop(self, instr, pc):
        return [0x0000]

    def _mov(self, instr, pc):
        dst, src = instr.operands
        self._warn_if_r0(instr, dst.num)
        return [_r_format(opcode_of("add"), dst.num, src.num, 0)]

    def _store(self, instr, pc):
        # sw Y, (X)
        source, address = instr.operands
        return [_r_format(opcode_of("sw"), 0, address.num, source.num)]

    def _load(self, instr, pc):
        # lw Dst, (X)
        dst, address = instr.operands
        self._warn_if_r0(instr, dst.num)
        return [_r_format(opcode_of("lw"), dst.num, address.num, 0)]

    def _immediate(self, instr, pc):
        reg, imm = instr.operands
        value = self._value(imm.expr, pc)
        if value is None:
            return None

        if instr.mnemonic == "lli":
            valid = self._check_lli_range(value, reg.num, imm)
        else:
            valid = self._check_lhi_range(value, imm)
        if not valid:
            return None

        self._warn_if_r0(instr, reg.num)
        return [_i_format(opcode_of(instr.mnemonic), reg.num, value)]

    def _check_lli_range(self, value: int, reg: int, imm) -> bool:
        # Hardware melakukan sign-extend 8-bit, jadi rentang aslinya -128..127.
        # Hex/biner/karakter boleh sampai 0xFF karena jelas ditulis sebagai bit.
        if -128 <= value <= 127:
            return True
        if 128 <= value <= 255:
            if is_bit_pattern(imm.expr):
                return True
            self.diag.error(
                f"'lli' melakukan sign-extend 8-bit: {value} akan dimuat sebagai "
                f"{value - 256}. Pakai 'li r{reg}, {value}' untuk nilai {value}, "
                f"atau tulis '0x{value:02X}' jika memang ingin pola bit.",
                imm.span)
            return False
        self.diag.error(
            f"immediate {value} di luar jangkauan 'lli': -128..127 "
            f"(atau 0x00..0xFF sebagai pola bit). Pakai 'li' untuk 16-bit.",
            imm.span)
        return False

    def _check_lhi_range(self, value: int, imm) -> bool:
        if -128 <= value <= 255:
            return True
        self.diag.error(f"immediate {value} di luar jangkauan 'lhi': -128..255", imm.span)
        return False

    def _li(self, instr, pc):
        reg, imm = instr.operands
        value = self._value(imm.expr, pc)
        if value is None:
            return None
        if not -32768 <= value <= 65535:
            self.diag.error(f"nilai li {value} di luar jangkauan 16-bit", imm.span)
            return None
        value &= 0xFFFF
        self._warn_if_r0(instr, reg.num)
        return [_i_format(opcode_of("lli"), reg.num, value & 0xFF),
                _i_format(opcode_of("lhi"), reg.num, value >> 8)]

    def _branch_offset(self, target, pc: int) -> Optional[int]:
        """Label dihitung relatif terhadap pc, angka dipakai apa adanya."""
        value = self._value(target.expr, pc)
        if value is None:
            return None
        offset = value - pc if references_label(target.expr, self.symbols) else value
        if not -128 <= offset <= 127:
            self.diag.error(f"offset cabang {offset} di luar jangkauan [-128, 127]",
                            target.span)
            return None
        return offset

    def _branch(self, instr, pc):
        reg, target = instr.operands
        offset = self._branch_offset(target, pc)
        if offset is None:
            return None
        return [_i_format(opcode_of(instr.mnemonic), reg.num, offset)]

    def _jump(self, instr, pc):
        # b target  =  bz r0, target  (r0 selalu nol)
        offset = self._branch_offset(instr.operands[0], pc)
        if offset is None:
            return None
        return [_i_format(opcode_of("bz"), 0, offset)]

    # ---------- direktif ----------

    def encode_directive(self, directive: Directive, addr: int, size: int) -> List[int]:
        """Kata hasil direktif. Jika gagal, isi dengan nol sebanyak `size`."""
        if directive.name in ("org", "equ"):
            return []
        if directive.name == "word":
            return self._word_data(directive, addr, size)
        if directive.name in STRING_DIRECTIVES:
            return string_data(directive)
        return [0] * size    # .space, .zero, .align

    def _word_data(self, directive: Directive, addr: int, size: int) -> List[int]:
        words = []
        for expr in directive.args:
            value = self._value(expr, addr)
            if value is None:
                return [0] * size
            if not -32768 <= value <= 65535:
                self.diag.error(f"nilai .word {value} di luar 16-bit", expr.span)
                return [0] * size
            words.append(value & 0xFFFF)
        return words

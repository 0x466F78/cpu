import operator
from typing import Optional

from .ast_nodes import (BinaryExpr, Expr, NumberExpr, PcExpr, SliceExpr,
                        SymbolExpr, UnaryExpr)
from .diagnostics import DiagnosticBag
from .symbols import SymbolTable


def _divide(left: int, right: int) -> int:
    """Pembagian bulat yang dibulatkan ke nol, seperti di C."""
    quotient = abs(left) // abs(right)
    return quotient if (left < 0) == (right < 0) else -quotient


def _remainder(left: int, right: int) -> int:
    return left - _divide(left, right) * right


def _shift_left(value: int, amount: int) -> int:
    return value << amount if 0 <= amount < 32 else 0


def _shift_right(value: int, amount: int) -> int:
    return value >> amount if 0 <= amount < 32 else 0


_UNARY_OPS = {"+": operator.pos, "-": operator.neg, "~": operator.invert}

_BINARY_OPS = {
    "+": operator.add, "-": operator.sub, "*": operator.mul,
    "/": _divide, "%": _remainder,
    "<<": _shift_left, ">>": _shift_right,
    "&": operator.and_, "|": operator.or_, "^": operator.xor,
}


def evaluate(expr: Expr, symbols: SymbolTable, pc: int,
             diag: DiagnosticBag) -> Optional[int]:
    """Hitung nilai ekspresi. Mengembalikan None (dan melapor ke diag) jika gagal."""
    if isinstance(expr, NumberExpr):
        return expr.value

    if isinstance(expr, PcExpr):
        return pc

    if isinstance(expr, SymbolExpr):
        symbol = symbols.lookup(expr.name)
        if symbol is None:
            diag.error(f"simbol tak terdefinisi '{expr.name}'", expr.span)
            return None
        return symbol.value

    if isinstance(expr, UnaryExpr):
        value = evaluate(expr.operand, symbols, pc, diag)
        return None if value is None else _UNARY_OPS[expr.op](value)

    if isinstance(expr, SliceExpr):
        value = evaluate(expr.operand, symbols, pc, diag)
        if value is None:
            return None
        mask = (1 << (expr.hi - expr.lo + 1)) - 1
        return (value >> expr.lo) & mask

    if isinstance(expr, BinaryExpr):
        left = evaluate(expr.left, symbols, pc, diag)
        if left is None:
            return None
        right = evaluate(expr.right, symbols, pc, diag)
        if right is None:
            return None
        if expr.op in ("/", "%") and right == 0:
            what = "pembagian" if expr.op == "/" else "modulo"
            diag.error(f"{what} dengan nol", expr.span)
            return None
        return _BINARY_OPS[expr.op](left, right)

    return None


def references_label(expr: Expr, symbols: SymbolTable) -> bool:
    """True jika ekspresi memakai minimal satu simbol berjenis label."""
    if isinstance(expr, SymbolExpr):
        symbol = symbols.lookup(expr.name)
        return symbol is not None and symbol.kind == "label"
    if isinstance(expr, (UnaryExpr, SliceExpr)):
        return references_label(expr.operand, symbols)
    if isinstance(expr, BinaryExpr):
        return (references_label(expr.left, symbols)
                or references_label(expr.right, symbols))
    return False


def is_bit_pattern(expr: Expr) -> bool:
    """True untuk literal hex/bin/oct, karakter, atau bit slice.

    Nilai seperti ini dianggap sengaja ditulis sebagai pola bit, jadi
    `lli r1, 0xC8` diterima walau akan di-sign-extend menjadi -56.
    """
    if isinstance(expr, NumberExpr):
        return expr.is_bitpattern
    return isinstance(expr, SliceExpr)

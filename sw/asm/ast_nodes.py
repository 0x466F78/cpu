from dataclasses import dataclass
from typing import List, Optional, Union

from .diagnostics import SourceSpan


# ---------- Ekspresi ----------

@dataclass(frozen=True)
class NumberExpr:
    value: int
    span: SourceSpan
    is_bitpattern: bool = False   # literal 0x.., 0b.., 0o.. atau karakter


@dataclass(frozen=True)
class SymbolExpr:
    name: str
    span: SourceSpan


@dataclass(frozen=True)
class PcExpr:
    span: SourceSpan


@dataclass(frozen=True)
class UnaryExpr:
    op: str
    operand: "Expr"
    span: SourceSpan


@dataclass(frozen=True)
class BinaryExpr:
    op: str
    left: "Expr"
    right: "Expr"
    span: SourceSpan


@dataclass(frozen=True)
class SliceExpr:
    """Ambil bit hi sampai lo (inklusif): expr[hi:lo]."""
    operand: "Expr"
    hi: int
    lo: int
    span: SourceSpan


Expr = Union[NumberExpr, SymbolExpr, PcExpr, UnaryExpr, BinaryExpr, SliceExpr]


# ---------- Operand ----------

@dataclass(frozen=True)
class RegOperand:
    num: int
    span: SourceSpan


@dataclass(frozen=True)
class MemOperand:
    num: int    # nomor register di dalam "(rN)"
    span: SourceSpan


@dataclass(frozen=True)
class ExprOperand:
    expr: Expr
    span: SourceSpan


Operand = Union[RegOperand, MemOperand, ExprOperand]


# ---------- Statement ----------

@dataclass(frozen=True)
class Instruction:
    mnemonic: str
    operands: List[Operand]
    span: SourceSpan


@dataclass(frozen=True)
class Directive:
    name: str
    # .equ                 -> [(nama_simbol, Expr)]
    # .ascii/.asciz/.string -> [str]
    # lainnya               -> [Expr, Expr, ...]
    args: List
    span: SourceSpan


@dataclass
class Statement:
    line_no: int
    labels: List[str]
    body: Optional[Union[Instruction, Directive]]
    span: SourceSpan

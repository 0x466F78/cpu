from dataclasses import dataclass
from typing import List, Optional

from .ast_nodes import Directive, Instruction, Statement
from .diagnostics import Diagnostic, DiagnosticBag, SourceSpan
from .encoder import Encoder, string_data
from .expressions import evaluate
from .isa import ROM_END, ROM_SIZE, STRING_DIRECTIVES, is_register_name
from .lexer import Lexer
from .parser import Parser
from .symbols import Symbol, SymbolTable

LI_SIZE = 2    # li dipecah menjadi lli + lhi


@dataclass
class LayoutEntry:
    statement: Statement
    addr: int
    size: int


@dataclass
class AssemblyResult:
    words: List[int]
    statements: List[Statement]
    layout: List[LayoutEntry]
    symbols: SymbolTable
    diagnostics: DiagnosticBag

    @property
    def ok(self) -> bool:
        return not self.diagnostics.has_errors

    @property
    def warnings(self) -> List[Diagnostic]:
        return self.diagnostics.warnings


class Assembler:
    def assemble(self, source: str) -> AssemblyResult:
        """Rakit source. Jika ada error, hasilnya `ok == False` dan `words` kosong."""
        self._diag = DiagnosticBag()
        self._symbols = SymbolTable()
        self._encoder = Encoder(self._symbols, self._diag)

        tokens = Lexer(source, self._diag).tokenize()
        statements = Parser(tokens, self._diag).parse_program()

        layout: List[LayoutEntry] = []
        words: List[int] = []
        if not self._diag.has_errors:
            layout = self._layout(statements)
        if not self._diag.has_errors:
            words = self._emit(layout)
        if self._diag.has_errors:
            words = []

        return AssemblyResult(words, statements, layout, self._symbols, self._diag)

    # ---------- pass 1: alamat dan simbol ----------

    def _layout(self, statements: List[Statement]) -> List[LayoutEntry]:
        layout: List[LayoutEntry] = []
        addr = 0

        for stmt in statements:
            body = stmt.body
            is_directive = isinstance(body, Directive)

            if is_directive and body.name in ("org", "equ", "align") and stmt.labels:
                self._diag.error(
                    f"label tidak boleh menempel pada '.{body.name}'", body.span)

            if is_directive and body.name == "org":
                target = self._org_target(body, addr)
                if target is not None:
                    addr = target
                    layout.append(LayoutEntry(stmt, addr, 0))
                continue

            self._define_labels(stmt, addr)

            size = self._size_of(stmt, addr)
            if size is None:
                continue
            if addr + size > ROM_SIZE:
                self._diag.error(
                    f"program melebihi ROM (0x{addr + size:04X} > 0x{ROM_SIZE:04X})",
                    stmt.span)
                break

            layout.append(LayoutEntry(stmt, addr, size))
            addr += size

        return layout

    def _define_labels(self, stmt: Statement, addr: int) -> None:
        for name in stmt.labels:
            if not self._is_valid_symbol_name(name, stmt.span):
                continue
            if not self._symbols.define(Symbol(name, addr, stmt.line_no, "label")):
                self._diag.error(f"label duplikat '{name}'", stmt.span)

    def _is_valid_symbol_name(self, name: str, span: SourceSpan) -> bool:
        if is_register_name(name):
            self._diag.error(f"'{name}' adalah nama register yang dipesan", span)
            return False
        return True

    def _size_of(self, stmt: Statement, addr: int) -> Optional[int]:
        """Jumlah kata yang dipakai statement, atau None jika ada error."""
        body = stmt.body
        if body is None:
            return 0
        if isinstance(body, Instruction):
            return LI_SIZE if body.mnemonic == "li" else 1

        if body.name == "equ":
            self._define_equ(body, addr, stmt)
            return 0
        if body.name == "word":
            return len(body.args)
        if body.name in STRING_DIRECTIVES:
            return len(string_data(body))
        if body.name in ("space", "zero"):
            return self._space_size(body, addr)
        if body.name == "align":
            return self._align_size(body, addr)
        return 0

    def _org_target(self, directive: Directive, addr: int) -> Optional[int]:
        if len(directive.args) != 1:
            self._diag.error("'.org' butuh 1 argumen", directive.span)
            return None
        target = evaluate(directive.args[0], self._symbols, addr, self._diag)
        if target is None:
            return None
        if target < addr:
            self._diag.error(
                f"'.org' tidak boleh mundur (saat ini 0x{addr:04X}, target 0x{target:04X})",
                directive.span)
            return None
        if target > ROM_END:
            self._diag.error(
                f"'.org' target 0x{target:04X} di luar ROM (maks 0x{ROM_END:04X})",
                directive.span)
            return None
        return target

    def _define_equ(self, directive: Directive, addr: int, stmt: Statement) -> None:
        name, expr = directive.args[0]
        if not self._is_valid_symbol_name(name, directive.span):
            return
        value = evaluate(expr, self._symbols, addr, self._diag)
        if value is None:
            return
        if not self._symbols.define(Symbol(name, value, stmt.line_no, "equ")):
            self._diag.error(f"simbol duplikat '{name}'", directive.span)

    def _directive_arg(self, directive: Directive, addr: int) -> Optional[int]:
        if not directive.args:
            self._diag.error(f"'.{directive.name}' kekurangan argumen", directive.span)
            return None
        return evaluate(directive.args[0], self._symbols, addr, self._diag)

    def _space_size(self, directive: Directive, addr: int) -> Optional[int]:
        count = self._directive_arg(directive, addr)
        if count is not None and count < 0:
            self._diag.error(f"'.{directive.name}' size tidak boleh negatif",
                             directive.span)
            return None
        return count

    def _align_size(self, directive: Directive, addr: int) -> Optional[int]:
        power = self._directive_arg(directive, addr)
        if power is None:
            return None
        if not 0 <= power <= 15:
            self._diag.error("'.align' eksponen harus 0..15", directive.span)
            return None
        mask = (1 << power) - 1
        return ((addr + mask) & ~mask) - addr

    # ---------- pass 2: encode ----------

    def _emit(self, layout: List[LayoutEntry]) -> List[int]:
        words: List[int] = []

        for entry in layout:
            words += [0] * (entry.addr - len(words))    # celah dari .org
            body = entry.statement.body
            if body is None:
                continue

            if isinstance(body, Instruction):
                encoded = self._encoder.encode_instruction(body, entry.addr)
            else:
                encoded = self._encoder.encode_directive(body, entry.addr, entry.size)

            if encoded is None:
                encoded = [0] * entry.size
            elif len(encoded) != entry.size:
                self._diag.error(
                    f"internal: ukuran pass 2 ({len(encoded)}) berbeda dari pass 1 "
                    f"({entry.size}) di baris {entry.statement.line_no}",
                    entry.statement.span)
            words += encoded

        return words

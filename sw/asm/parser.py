from typing import List, Optional

from .ast_nodes import (BinaryExpr, Directive, Expr, ExprOperand, Instruction,
                        MemOperand, NumberExpr, Operand, PcExpr, RegOperand,
                        SliceExpr, Statement, SymbolExpr, UnaryExpr)
from .diagnostics import DiagnosticBag, SourceSpan
from .isa import (DIRECTIVES, STRING_DIRECTIVES, OperandKind, lookup_spec,
                  parse_register)
from .tokens import Token, TokenKind

# Operator biner dari prioritas terendah ke tertinggi.
_BINARY_LEVELS = [
    {TokenKind.PIPE: "|"},
    {TokenKind.CARET: "^"},
    {TokenKind.AMP: "&"},
    {TokenKind.LSHIFT: "<<", TokenKind.RSHIFT: ">>"},
    {TokenKind.PLUS: "+", TokenKind.MINUS: "-"},
    {TokenKind.STAR: "*", TokenKind.SLASH: "/", TokenKind.PERCENT: "%"},
]

_UNARY_KINDS = (TokenKind.PLUS, TokenKind.MINUS, TokenKind.TILDE)


def _span(token: Token) -> SourceSpan:
    return SourceSpan(token.line, token.col, len(token.text))


class Parser:
    def __init__(self, tokens: List[Token], diag: DiagnosticBag):
        self.tokens = tokens
        self.pos = 0
        self.diag = diag

    def parse_program(self) -> List[Statement]:
        statements: List[Statement] = []
        while not self._at(TokenKind.EOF):
            statement = self._parse_statement()
            if statement is not None:
                statements.append(statement)
            self._skip_newlines()
        return statements

    # ---------- bantuan token ----------

    def _current(self) -> Token:
        return self.tokens[self.pos]

    def _peek(self, offset: int = 1) -> Token:
        i = self.pos + offset
        return self.tokens[i] if i < len(self.tokens) else self.tokens[-1]

    def _at(self, kind: TokenKind) -> bool:
        return self._current().kind == kind

    def _at_line_end(self) -> bool:
        return self._at(TokenKind.NEWLINE) or self._at(TokenKind.EOF)

    def _advance(self, count: int = 1) -> Token:
        """Maju `count` token (berhenti di EOF). Mengembalikan token awal."""
        token = self._current()
        self.pos = min(self.pos + count, len(self.tokens) - 1)
        return token

    def _span_here(self) -> SourceSpan:
        return SourceSpan(self._current().line, self._current().col, 1)

    def _consume(self, kind: TokenKind) -> Optional[Token]:
        if self._at(kind):
            return self._advance()
        self.diag.error(f"diharapkan {kind.name.lower()}", self._span_here())
        return None

    def _expect(self, kind: TokenKind, message: str) -> Optional[Token]:
        if self._at(kind):
            return self._advance()
        self.diag.error(message, self._span_here())
        return None

    def _skip_newlines(self) -> None:
        while self._at(TokenKind.NEWLINE):
            self._advance()

    def _skip_to_eol(self) -> None:
        while not self._at_line_end():
            self._advance()

    def _skip_line(self) -> None:
        self._skip_to_eol()
        if self._at(TokenKind.NEWLINE):
            self._advance()

    def _fail(self, message: str, span: SourceSpan) -> None:
        """Lapor error, lewati sisa baris, dan kembalikan None."""
        self.diag.error(message, span)
        self._skip_to_eol()
        return None

    # ---------- statement ----------

    def _parse_statement(self) -> Optional[Statement]:
        start = self._current()
        labels: List[str] = []
        while self._at(TokenKind.IDENT) and self._peek().kind == TokenKind.COLON:
            labels.append(self._current().value)
            self._advance(2)

        span = SourceSpan(start.line, start.col)

        if self._at_line_end():
            if self._at(TokenKind.NEWLINE):
                self._advance()
            return Statement(start.line, labels, None, span)

        if self._at(TokenKind.IDENT):
            body = self._parse_instruction()
        elif self._at(TokenKind.DIRECTIVE):
            body = self._parse_directive()
        else:
            self.diag.error("diharapkan instruksi atau direktif", self._span_here())
            self._skip_line()
            return None

        if not self._at_line_end():
            self.diag.error("token tak terduga setelah statement", self._span_here())
        self._skip_line()

        if body is None:
            return None
        return Statement(start.line, labels, body, span)

    # ---------- instruksi ----------

    def _parse_instruction(self) -> Optional[Instruction]:
        name_token = self._advance()
        mnemonic = name_token.value.lower()
        spec = lookup_spec(mnemonic)
        if spec is None:
            return self._fail(f"mnemonic tidak dikenal '{name_token.value}'",
                              _span(name_token))

        operands: List[Operand] = []
        for index, kind in enumerate(spec.operands):
            if index > 0:
                if not self._at(TokenKind.COMMA):
                    return self._fail(f"diharapkan ',' sebelum operand ke-{index + 1}",
                                      self._span_here())
                self._advance()
            operand = self._parse_operand(kind)
            if operand is None:
                self._skip_to_eol()
                return None
            operands.append(operand)

        if self._at(TokenKind.COMMA):
            return self._fail(f"operand berlebih untuk '{mnemonic}'", self._span_here())
        return Instruction(mnemonic, operands, _span(name_token))

    def _parse_operand(self, kind: OperandKind) -> Optional[Operand]:
        if kind == OperandKind.REG:
            return self._parse_register_operand()
        if kind == OperandKind.MEM:
            return self._parse_memory_operand()
        expr = self._parse_expression()
        return None if expr is None else ExprOperand(expr, expr.span)

    def _parse_register_operand(self) -> Optional[RegOperand]:
        token = self._current()
        if token.kind != TokenKind.IDENT:
            self.diag.error("diharapkan register r0-r7", self._span_here())
            return None
        number = parse_register(token.value)
        if number is None:
            self.diag.error(f"'{token.value}' bukan register r0-r7", _span(token))
            return None
        self._advance()
        return RegOperand(number, _span(token))

    def _parse_memory_operand(self) -> Optional[MemOperand]:
        start = self._current()
        self._consume(TokenKind.LPAREN)
        token = self._current()
        number = parse_register(token.value) if token.kind == TokenKind.IDENT else None
        if number is None:
            self.diag.error("diharapkan register di dalam '(rX)'", _span(token))
            return None
        self._advance()
        self._consume(TokenKind.RPAREN)
        return MemOperand(number, SourceSpan(start.line, start.col))

    # ---------- direktif ----------

    def _parse_directive(self) -> Optional[Directive]:
        token = self._advance()
        name = token.value
        span = _span(token)
        if name not in DIRECTIVES:
            return self._fail(f"direktif tidak dikenal '.{name}'", span)

        if name == "equ":
            args = self._parse_equ_args()
        elif name in STRING_DIRECTIVES:
            args = self._parse_string_args(name)
        else:
            args = self._parse_expression_list()

        if args is None:
            self._skip_to_eol()
            return None
        return Directive(name, args, span)

    def _parse_equ_args(self) -> Optional[list]:
        if not self._at(TokenKind.IDENT):
            self.diag.error("'.equ' memerlukan nama simbol", self._span_here())
            return None
        name = self._advance().value
        self._consume(TokenKind.COMMA)
        expr = self._parse_expression()
        return None if expr is None else [(name, expr)]

    def _parse_string_args(self, directive: str) -> Optional[list]:
        if not self._at(TokenKind.STRING):
            self.diag.error(f"'.{directive}' memerlukan string literal", self._span_here())
            return None
        return [self._advance().value]

    def _parse_expression_list(self) -> Optional[list]:
        args: List[Expr] = []
        if self._at_line_end():
            return args
        while True:
            expr = self._parse_expression()
            if expr is None:
                return None
            args.append(expr)
            if not self._at(TokenKind.COMMA):
                return args
            self._advance()

    # ---------- ekspresi ----------

    def _parse_expression(self) -> Optional[Expr]:
        return self._parse_binary(0)

    def _parse_binary(self, level: int) -> Optional[Expr]:
        if level >= len(_BINARY_LEVELS):
            return self._parse_unary()

        left = self._parse_binary(level + 1)
        if left is None:
            return None

        operators = _BINARY_LEVELS[level]
        while self._current().kind in operators:
            op = operators[self._advance().kind]
            right = self._parse_binary(level + 1)
            if right is None:
                return None
            left = BinaryExpr(op, left, right, left.span.merge(right.span))
        return left

    def _parse_unary(self) -> Optional[Expr]:
        token = self._current()
        if token.kind not in _UNARY_KINDS:
            return self._parse_postfix()
        self._advance()
        operand = self._parse_unary()
        if operand is None:
            return None
        return UnaryExpr(token.text, operand, _span(token).merge(operand.span))

    def _parse_postfix(self) -> Optional[Expr]:
        expr = self._parse_primary()
        while expr is not None and self._at(TokenKind.LBRACKET):
            expr = self._parse_bit_slice(expr)
        return expr

    def _parse_bit_slice(self, operand: Expr) -> Optional[SliceExpr]:
        """Bagian `[hi:lo]` dari `expr[hi:lo]`."""
        bracket = self._advance()
        hi_token = self._expect(TokenKind.NUMBER, "bit slice: diharapkan indeks hi (angka)")
        if hi_token is None:
            return None
        if self._expect(TokenKind.COLON, "bit slice: diharapkan ':' setelah hi") is None:
            return None
        lo_token = self._expect(TokenKind.NUMBER, "bit slice: diharapkan indeks lo (angka)")
        if lo_token is None:
            return None
        if self._expect(TokenKind.RBRACKET, "bit slice: diharapkan ']'") is None:
            return None

        hi, lo = hi_token.value, lo_token.value
        where = SourceSpan(bracket.line, bracket.col)
        if hi < lo:
            self.diag.error(f"bit slice [{hi}:{lo}]: indeks hi harus >= lo", where)
            return None
        if hi > 31:
            self.diag.error(f"bit slice [{hi}:{lo}]: hi={hi} melebihi 31", where)
            return None
        return SliceExpr(operand, hi, lo, operand.span.merge(_span(hi_token)))

    def _parse_primary(self) -> Optional[Expr]:
        token = self._current()

        if token.kind == TokenKind.NUMBER:
            self._advance()
            return NumberExpr(token.value, _span(token), token.is_bitpattern)

        if token.kind == TokenKind.PC:
            self._advance()
            return PcExpr(_span(token))

        if token.kind == TokenKind.IDENT:
            if parse_register(token.value) is not None:
                self.diag.error(
                    f"register '{token.value}' tidak dapat dipakai di dalam ekspresi",
                    _span(token))
                return None
            self._advance()
            return SymbolExpr(token.value, _span(token))

        if token.kind == TokenKind.LPAREN:
            self._advance()
            inner = self._parse_expression()
            if inner is None:
                return None
            self._consume(TokenKind.RPAREN)
            return inner

        self.diag.error(f"ekspresi tidak valid: token {token.kind.name.lower()}",
                        self._span_here())
        return None

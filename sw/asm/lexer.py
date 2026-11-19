import string
from typing import List, Tuple

from .diagnostics import DiagnosticBag, SourceSpan
from .tokens import Token, TokenKind

_ESCAPES = {
    "n": "\n", "t": "\t", "r": "\r",
    "0": "\0", "\\": "\\", '"': '"', "'": "'",
}

_TWO_CHAR_TOKENS = {
    "<<": TokenKind.LSHIFT,
    ">>": TokenKind.RSHIFT,
}

_ONE_CHAR_TOKENS = {
    ",": TokenKind.COMMA,    ":": TokenKind.COLON,
    "(": TokenKind.LPAREN,   ")": TokenKind.RPAREN,
    "[": TokenKind.LBRACKET, "]": TokenKind.RBRACKET,
    "+": TokenKind.PLUS,     "-": TokenKind.MINUS,
    "*": TokenKind.STAR,     "/": TokenKind.SLASH,
    "%": TokenKind.PERCENT,  "&": TokenKind.AMP,
    "|": TokenKind.PIPE,     "^": TokenKind.CARET,
    "~": TokenKind.TILDE,
}


class Lexer:
    def __init__(self, source: str, diag: DiagnosticBag):
        self.src = source
        self.diag = diag
        self.pos = 0
        self.line = 1
        self.col = 1

    def tokenize(self) -> List[Token]:
        tokens: List[Token] = []
        while self.pos < len(self.src):
            c = self.src[self.pos]

            if c in " \t\r":
                self._advance()
            elif c == "\n":
                tokens.append(Token(TokenKind.NEWLINE, "\n", self.line, self.col, "\n"))
                self._advance_line()
            elif c in ";#":
                self._skip_comment()
            elif c.isdigit():
                tokens.append(self._lex_number())
            elif c.isalpha() or c == "_":
                tokens.append(self._lex_ident())
            elif c == ".":
                tokens.append(self._lex_dot())
            elif c == "$":
                tokens.append(Token(TokenKind.PC, "$", self.line, self.col, "$"))
                self._advance()
            elif c == '"':
                tokens.append(self._lex_string())
            elif c == "'":
                tokens.append(self._lex_char())
            elif self.src[self.pos:self.pos + 2] in _TWO_CHAR_TOKENS:
                tokens.append(self._lex_symbol(2, _TWO_CHAR_TOKENS))
            elif c in _ONE_CHAR_TOKENS:
                tokens.append(self._lex_symbol(1, _ONE_CHAR_TOKENS))
            else:
                self.diag.error(f"karakter tidak dikenal {c!r}", SourceSpan(self.line, self.col))
                self._advance()

        tokens.append(Token(TokenKind.EOF, None, self.line, self.col, ""))
        return tokens

    # ---------- posisi ----------

    def _peek(self, offset: int = 0) -> str:
        i = self.pos + offset
        return self.src[i] if i < len(self.src) else ""

    def _advance(self, count: int = 1) -> None:
        count = min(count, len(self.src) - self.pos)
        self.pos += count
        self.col += count

    def _advance_line(self) -> None:
        self.pos += 1
        self.line += 1
        self.col = 1

    def _skip_comment(self) -> None:
        while self._peek() not in ("", "\n"):
            self._advance()

    def _scan_word(self) -> str:
        """Ambil huruf, angka, dan '_' berurutan mulai dari posisi sekarang."""
        end = self.pos
        while end < len(self.src) and (self.src[end].isalnum() or self.src[end] == "_"):
            end += 1
        return self.src[self.pos:end]

    # ---------- token ----------

    def _lex_symbol(self, length: int, table: dict) -> Token:
        line, col = self.line, self.col
        text = self.src[self.pos:self.pos + length]
        self._advance(length)
        return Token(table[text], text, line, col, text)

    def _lex_number(self) -> Token:
        line, col = self.line, self.col
        text = self._scan_word()
        self._advance(len(text))

        is_bitpattern = text[:2].lower() in ("0x", "0b", "0o")
        try:
            value = int(text, 0) if is_bitpattern else int(text, 10)
        except ValueError:
            self.diag.error(f"literal angka tidak valid '{text}'",
                            SourceSpan(line, col, len(text)))
            value = 0
        return Token(TokenKind.NUMBER, value, line, col, text, is_bitpattern)

    def _lex_ident(self) -> Token:
        line, col = self.line, self.col
        text = self._scan_word()
        self._advance(len(text))
        return Token(TokenKind.IDENT, text, line, col, text)

    def _lex_dot(self) -> Token:
        """'.nama' adalah direktif, '.' sendirian berarti alamat saat ini."""
        line, col = self.line, self.col
        next_char = self._peek(1)
        if next_char.isalpha() or next_char == "_":
            self._advance()
            name = self._scan_word()
            self._advance(len(name))
            return Token(TokenKind.DIRECTIVE, name.lower(), line, col, "." + name)
        self._advance()
        return Token(TokenKind.PC, ".", line, col, ".")

    def _lex_string(self) -> Token:
        line, col = self.line, self.col
        self._advance()  # kutip pembuka
        chars = []
        while self._peek() not in ("", '"', "\n"):
            if self._peek() == "\\":
                char, ok = self._read_escape()
                if ok:
                    chars.append(char)
            else:
                chars.append(self._peek())
                self._advance()

        if self._peek() == '"':
            self._advance()
        else:
            self.diag.error("string tidak ditutup", SourceSpan(line, col))

        text = "".join(chars)
        return Token(TokenKind.STRING, text, line, col, text)

    def _lex_char(self) -> Token:
        line, col = self.line, self.col
        self._advance()  # kutip pembuka
        if self._peek() == "":
            self.diag.error("char literal tidak ditutup", SourceSpan(line, col))
            return Token(TokenKind.NUMBER, 0, line, col, "")

        if self._peek() == "\\":
            char, _ = self._read_escape()
        else:
            char = self._peek()
            self._advance()

        if self._peek() == "'":
            self._advance()
        else:
            self.diag.error("char literal tidak ditutup", SourceSpan(line, col))
        return Token(TokenKind.NUMBER, ord(char), line, col, repr(char),
                     is_bitpattern=True)

    # ---------- escape ----------

    def _read_escape(self) -> Tuple[str, bool]:
        """Baca '\\' dan kode sesudahnya. Mengembalikan (karakter, berhasil)."""
        self._advance()  # tanda '\'
        code = self._peek()
        if code == "":
            return "\0", False
        if code == "x":
            return self._read_hex_escape()
        self._advance()
        return _ESCAPES.get(code, code), True

    def _read_hex_escape(self) -> Tuple[str, bool]:
        self._advance()  # huruf 'x'
        digits = ""
        while len(digits) < 2 and self._peek() and self._peek() in string.hexdigits:
            digits += self._peek()
            self._advance()
        if digits:
            return chr(int(digits, 16)), True
        return "\\", False

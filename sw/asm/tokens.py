from dataclasses import dataclass
from enum import Enum, auto
from typing import Any


class TokenKind(Enum):
    NUMBER = auto()
    STRING = auto()
    IDENT = auto()
    DIRECTIVE = auto()   # nama direktif tanpa titik, mis. "org"
    PC = auto()          # "$" atau "."
    NEWLINE = auto()
    EOF = auto()

    COMMA = auto()
    COLON = auto()
    LPAREN = auto()
    RPAREN = auto()
    LBRACKET = auto()
    RBRACKET = auto()

    PLUS = auto()
    MINUS = auto()
    STAR = auto()
    SLASH = auto()
    PERCENT = auto()
    LSHIFT = auto()
    RSHIFT = auto()
    AMP = auto()
    PIPE = auto()
    CARET = auto()
    TILDE = auto()


@dataclass(frozen=True)
class Token:
    kind: TokenKind
    value: Any
    line: int
    col: int
    text: str
    is_bitpattern: bool = False   # True untuk 0x.., 0b.., 0o.. dan char literal

    def __repr__(self) -> str:
        return f"Token({self.kind.name}, {self.value!r}, {self.line}:{self.col})"

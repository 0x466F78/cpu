from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass(frozen=True)
class Symbol:
    name: str
    value: int
    line_no: int
    kind: str    # "label" atau "equ"


class SymbolTable:
    def __init__(self):
        self._symbols: Dict[str, Symbol] = {}

    def define(self, symbol: Symbol) -> bool:
        """Simpan simbol. Mengembalikan False jika namanya sudah ada."""
        if symbol.name in self._symbols:
            return False
        self._symbols[symbol.name] = symbol
        return True

    def lookup(self, name: str) -> Optional[Symbol]:
        return self._symbols.get(name)

    def all(self) -> List[Symbol]:
        return sorted(self._symbols.values(), key=lambda s: (s.value, s.name))

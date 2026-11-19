from dataclasses import dataclass, field
from typing import List


@dataclass(frozen=True)
class SourceSpan:
    """Posisi teks di sumber (baris dan kolom dimulai dari 1)."""
    line: int
    col: int = 1
    length: int = 1

    def merge(self, other: "SourceSpan") -> "SourceSpan":
        if self.line != other.line:
            return self
        end = max(self.col + self.length, other.col + other.length)
        return SourceSpan(self.line, self.col, end - self.col)


@dataclass(frozen=True)
class Diagnostic:
    severity: str    # "error" atau "warning"
    message: str
    span: SourceSpan

    def render(self, filename: str) -> str:
        return (f"{filename}:{self.span.line}:{self.span.col}: "
                f"{self.severity}: {self.message}")


@dataclass
class DiagnosticBag:
    """Menampung semua error dan warning dari satu kali perakitan."""
    items: List[Diagnostic] = field(default_factory=list)

    def error(self, message: str, span: SourceSpan) -> None:
        self.items.append(Diagnostic("error", message, span))

    def warning(self, message: str, span: SourceSpan) -> None:
        self.items.append(Diagnostic("warning", message, span))

    @property
    def has_errors(self) -> bool:
        return any(d.severity == "error" for d in self.items)

    @property
    def errors(self) -> List[Diagnostic]:
        return [d for d in self.items if d.severity == "error"]

    @property
    def warnings(self) -> List[Diagnostic]:
        return [d for d in self.items if d.severity == "warning"]

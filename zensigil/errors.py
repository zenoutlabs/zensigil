"""Diagnostics shared by the parser, checker, interpreter, and CLI."""
from dataclasses import dataclass


@dataclass
class SigilError(Exception):
    code: str
    message: str
    line: int = 1
    column: int = 1
    source_name: str = ""
    call_trace: tuple = ()

    def __str__(self):
        return f"{self.code} at {self.line}:{self.column}: {self.message}"

    def as_dict(self, source=""):
        lines = source.split("\n")
        result = {"code": self.code, "message": self.message, "line": self.line,
                "column": self.column,
                "source_line": lines[self.line - 1] if 0 < self.line <= len(lines) else ""}
        if self.source_name:
            result["source_name"] = self.source_name
            result["source_file"] = self.source_name
        if self.call_trace:
            result["call_trace"] = list(self.call_trace)
        return result


def fail(token, code, message):
    raise SigilError(code, message, token.line, token.column, getattr(token, "source_name", ""))

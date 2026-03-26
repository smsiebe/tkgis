"""Safe expression parser for attribute queries.

Translates a safe subset of SQL WHERE syntax into pandas boolean masks.
NO eval() is used — expressions are tokenized and converted to boolean
Series operations manually.
"""
from __future__ import annotations

import re
from typing import Any

import pandas as pd


class ExpressionError(Exception):
    """Raised when an expression cannot be parsed or is unsafe."""


# ---------------------------------------------------------------------------
# Token types
# ---------------------------------------------------------------------------

_TOKEN_PATTERNS = [
    ("STRING", r"'(?:[^'\\]|\\.)*'"),      # Single-quoted strings
    ("NUMBER", r"-?\d+(?:\.\d+)?"),         # Integers and floats
    ("IS_NOT_NULL", r"\bIS\s+NOT\s+NULL\b"),
    ("IS_NULL", r"\bIS\s+NULL\b"),
    ("NOT", r"\bNOT\b"),
    ("AND", r"\bAND\b"),
    ("OR", r"\bOR\b"),
    ("LIKE", r"\bLIKE\b"),
    ("IN", r"\bIN\b"),
    ("NULL", r"\bNULL\b"),
    ("CMP", r"<=|>=|!=|<>|<|>|="),
    ("LPAREN", r"\("),
    ("RPAREN", r"\)"),
    ("COMMA", r","),
    ("IDENT", r"[A-Za-z_][A-Za-z0-9_]*"),
    ("WS", r"\s+"),
]

_TOKEN_RE = re.compile(
    "|".join(f"(?P<{name}>{pat})" for name, pat in _TOKEN_PATTERNS),
    re.IGNORECASE,
)

# Dangerous patterns we reject outright
_DANGEROUS_RE = re.compile(
    r"(__|import|exec|eval|compile|globals|locals|getattr|setattr"
    r"|delattr|open|os\.|sys\.|subprocess|lambda|def |class )",
    re.IGNORECASE,
)


def _tokenize(expression: str) -> list[tuple[str, str]]:
    """Tokenize an expression string into (type, value) pairs."""
    tokens: list[tuple[str, str]] = []
    pos = 0
    for m in _TOKEN_RE.finditer(expression):
        if m.start() != pos:
            unexpected = expression[pos : m.start()].strip()
            if unexpected:
                raise ExpressionError(
                    f"Unexpected characters at position {pos}: {unexpected!r}"
                )
        pos = m.end()
        kind = m.lastgroup
        assert kind is not None
        if kind == "WS":
            continue
        tokens.append((kind, m.group()))
    if pos != len(expression):
        leftover = expression[pos:].strip()
        if leftover:
            raise ExpressionError(f"Unexpected trailing text: {leftover!r}")
    return tokens


def _parse_value(tok_val: str, tok_type: str) -> Any:
    """Convert a token value to a Python literal."""
    if tok_type == "STRING":
        # Strip surrounding quotes and unescape
        return tok_val[1:-1].replace("\\'", "'")
    if tok_type == "NUMBER":
        if "." in tok_val:
            return float(tok_val)
        return int(tok_val)
    if tok_type == "NULL":
        return None
    raise ExpressionError(f"Cannot parse value from token: {tok_type}={tok_val!r}")


class ExpressionParser:
    """Parse a safe SQL WHERE subset into a pandas boolean mask.

    Supported operators::

        =  !=  <  >  <=  >=
        LIKE  IN  AND  OR  NOT
        IS NULL  IS NOT NULL

    Safety: no ``eval()`` or ``exec()`` is ever called. Expressions are
    tokenized and converted to pandas boolean Series operations manually.
    """

    ALLOWED_OPS = {
        "=", "!=", "<", ">", "<=", ">=",
        "LIKE", "IN", "AND", "OR", "NOT",
        "IS NULL", "IS NOT NULL",
    }

    def parse(self, expression: str, df: pd.DataFrame) -> pd.Series:
        """Return a boolean mask Series for *expression* applied to *df*.

        Parameters
        ----------
        expression : str
            SQL-like WHERE clause (e.g. ``"value > 5 AND name = 'Chicago'"``).
        df : pd.DataFrame
            The dataframe to apply the expression against.

        Returns
        -------
        pd.Series
            Boolean mask with the same index as *df*.

        Raises
        ------
        ExpressionError
            If the expression is malformed or contains unsafe content.
        """
        if not expression or not expression.strip():
            raise ExpressionError("Empty expression")

        # Reject dangerous input before tokenizing
        if _DANGEROUS_RE.search(expression):
            raise ExpressionError(
                f"Expression contains disallowed content: {expression!r}"
            )

        tokens = _tokenize(expression)
        if not tokens:
            raise ExpressionError("Empty expression after tokenization")

        parser = _Parser(tokens, df)
        mask = parser.parse_or()

        if parser.pos < len(parser.tokens):
            remaining = " ".join(t[1] for t in parser.tokens[parser.pos :])
            raise ExpressionError(f"Unexpected tokens after expression: {remaining}")

        return mask


# ---------------------------------------------------------------------------
# Recursive descent parser — builds pd.Series boolean masks
# ---------------------------------------------------------------------------

class _Parser:
    """Recursive descent parser for WHERE-clause expressions."""

    def __init__(self, tokens: list[tuple[str, str]], df: pd.DataFrame) -> None:
        self.tokens = tokens
        self.df = df
        self.pos = 0

    def _peek(self) -> tuple[str, str] | None:
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return None

    def _advance(self) -> tuple[str, str]:
        tok = self.tokens[self.pos]
        self.pos += 1
        return tok

    def _expect(self, tok_type: str) -> tuple[str, str]:
        tok = self._peek()
        if tok is None or tok[0] != tok_type:
            expected = tok_type
            got = tok[1] if tok else "end of expression"
            raise ExpressionError(f"Expected {expected}, got {got!r}")
        return self._advance()

    # Grammar:
    #   or_expr  -> and_expr (OR and_expr)*
    #   and_expr -> not_expr (AND not_expr)*
    #   not_expr -> NOT not_expr | primary
    #   primary  -> IDENT comparison
    #            -> LPAREN or_expr RPAREN

    def parse_or(self) -> pd.Series:
        left = self.parse_and()
        while self._peek() and self._peek()[0] == "OR":  # type: ignore[index]
            self._advance()
            right = self.parse_and()
            left = left | right
        return left

    def parse_and(self) -> pd.Series:
        left = self.parse_not()
        while self._peek() and self._peek()[0] == "AND":  # type: ignore[index]
            self._advance()
            right = self.parse_not()
            left = left & right
        return left

    def parse_not(self) -> pd.Series:
        if self._peek() and self._peek()[0] == "NOT":  # type: ignore[index]
            self._advance()
            operand = self.parse_not()
            return ~operand
        return self.parse_primary()

    def parse_primary(self) -> pd.Series:
        tok = self._peek()
        if tok is None:
            raise ExpressionError("Unexpected end of expression")

        # Parenthesized sub-expression
        if tok[0] == "LPAREN":
            self._advance()
            result = self.parse_or()
            self._expect("RPAREN")
            return result

        # Must be IDENT (column name) followed by operator
        if tok[0] != "IDENT":
            raise ExpressionError(
                f"Expected column name, got {tok[1]!r}"
            )

        col_tok = self._advance()
        col_name = col_tok[1]

        if col_name not in self.df.columns:
            raise ExpressionError(f"Unknown column: {col_name!r}")

        col = self.df[col_name]

        # Next token determines the operation
        op_tok = self._peek()
        if op_tok is None:
            raise ExpressionError(
                f"Expected operator after column {col_name!r}"
            )

        # IS NULL / IS NOT NULL
        if op_tok[0] == "IS_NULL":
            self._advance()
            return col.isna()

        if op_tok[0] == "IS_NOT_NULL":
            self._advance()
            return col.notna()

        # LIKE
        if op_tok[0] == "LIKE":
            self._advance()
            val_tok = self._expect("STRING")
            pattern = _parse_value(val_tok[1], val_tok[0])
            return self._like_to_mask(col, pattern)

        # IN (val1, val2, ...)
        if op_tok[0] == "IN":
            self._advance()
            self._expect("LPAREN")
            values = self._parse_value_list()
            self._expect("RPAREN")
            return col.isin(values)

        # Comparison operators: = != < > <= >=
        if op_tok[0] == "CMP":
            self._advance()
            op = op_tok[1]
            val_tok = self._peek()
            if val_tok is None:
                raise ExpressionError(f"Expected value after {op!r}")

            if val_tok[0] == "NULL":
                self._advance()
                if op in ("=", "=="):
                    return col.isna()
                elif op in ("!=", "<>"):
                    return col.notna()
                else:
                    raise ExpressionError(
                        f"Cannot use {op!r} with NULL; use IS NULL / IS NOT NULL"
                    )

            if val_tok[0] not in ("STRING", "NUMBER", "IDENT"):
                raise ExpressionError(
                    f"Expected value after {op!r}, got {val_tok[1]!r}"
                )

            self._advance()
            if val_tok[0] == "IDENT":
                # Column-to-column comparison
                other_col = val_tok[1]
                if other_col not in self.df.columns:
                    raise ExpressionError(f"Unknown column: {other_col!r}")
                value = self.df[other_col]
            else:
                value = _parse_value(val_tok[1], val_tok[0])

            return self._compare(col, op, value)

        raise ExpressionError(
            f"Unexpected operator {op_tok[1]!r} after column {col_name!r}"
        )

    def _parse_value_list(self) -> list[Any]:
        """Parse a comma-separated list of literal values."""
        values: list[Any] = []
        tok = self._peek()
        if tok is not None and tok[0] == "RPAREN":
            return values  # empty list

        while True:
            tok = self._peek()
            if tok is None:
                raise ExpressionError("Unexpected end of IN list")
            if tok[0] not in ("STRING", "NUMBER", "NULL"):
                raise ExpressionError(
                    f"Expected value in IN list, got {tok[1]!r}"
                )
            self._advance()
            values.append(_parse_value(tok[1], tok[0]))
            nxt = self._peek()
            if nxt is None or nxt[0] != "COMMA":
                break
            self._advance()  # consume comma
        return values

    @staticmethod
    def _compare(col: pd.Series, op: str, value: Any) -> pd.Series:
        """Apply a comparison operator."""
        if op == "=" or op == "==":
            return col == value
        elif op == "!=" or op == "<>":
            return col != value
        elif op == "<":
            return col < value
        elif op == ">":
            return col > value
        elif op == "<=":
            return col <= value
        elif op == ">=":
            return col >= value
        else:
            raise ExpressionError(f"Unknown comparison operator: {op!r}")

    @staticmethod
    def _like_to_mask(col: pd.Series, pattern: str) -> pd.Series:
        """Convert a SQL LIKE pattern to a pandas string match.

        ``%`` matches any sequence of characters; ``_`` matches a single
        character.  The pattern is anchored to the full string.
        """
        # Escape regex special characters except our LIKE wildcards
        regex = ""
        i = 0
        while i < len(pattern):
            ch = pattern[i]
            if ch == "%":
                regex += ".*"
            elif ch == "_":
                regex += "."
            else:
                regex += re.escape(ch)
            i += 1
        regex = "^" + regex + "$"
        return col.astype(str).str.match(regex, na=False)

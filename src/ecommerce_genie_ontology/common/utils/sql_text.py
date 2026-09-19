from __future__ import annotations


def sql_string(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"

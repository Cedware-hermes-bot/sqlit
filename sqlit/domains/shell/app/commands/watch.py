"""Recurring query watch command handlers."""

from __future__ import annotations

import re
from typing import Any

from .router import register_command_handler

_WATCH_INTERVAL_RE = re.compile(r"^(?P<value>\d+(?:\.\d+)?)(?P<unit>ms|s|m)?$", re.IGNORECASE)


def _handle_watch_command(app: Any, cmd: str, args: list[str]) -> bool:
    if cmd != "watch":
        return False

    value = args[0].lower() if args else ""
    if not value:
        interval = float(getattr(app, "_watch_query_interval_s", 0.0) or 0.0)
        if interval > 0:
            app.notify(f"Query watch active ({app._format_watch_interval()})")
        else:
            app.notify("Query watch disabled")
        return True

    if value in {"off", "stop", "disable", "disabled", "0"}:
        app._disable_query_watch()
        return True

    interval_s = _parse_watch_interval(value)
    if interval_s is None or interval_s <= 0:
        app.notify("Usage: :watch <interval>|off", severity="warning")
        return True

    app._set_query_watch(interval_s)
    return True


def _parse_watch_interval(raw: str) -> float | None:
    match = _WATCH_INTERVAL_RE.match(raw.strip())
    if match is None:
        return None

    value = float(match.group("value"))
    unit = (match.group("unit") or "s").lower()
    if unit == "ms":
        return value / 1000.0
    if unit == "m":
        return value * 60.0
    return value


register_command_handler(_handle_watch_command)

"""Recognised failures and the plain-language explanation for each."""

import json
import re
from pathlib import Path


_CATALOGUE_PATH = Path(__file__).with_name("known_issues.json")


class KnownIssue:
    """One recognised failure: how to spot it, and what to tell the user."""

    def __init__(self, entry: dict):
        self.id = entry.get("id", "")
        self.summary = entry.get("summary", "")
        self.detail = entry.get("detail", "")
        self.action = entry.get("action", "")
        self._regex = bool(entry.get("regex", False))
        self._any = list(entry.get("match_any") or [])
        self._all = list(entry.get("match_all") or [])

    def _hit(self, pattern: str, text: str) -> bool:
        if self._regex:
            return re.search(pattern, text, re.IGNORECASE) is not None
        return pattern.lower() in text

    def matches(self, text: str) -> bool:
        lowered = text.lower()
        if self._all and not all(self._hit(p, lowered) for p in self._all):
            return False
        if self._any:
            return any(self._hit(p, lowered) for p in self._any)
        return bool(self._all)

    def advice(self) -> str:
        """The explanation and what to do about it, as one line."""
        return " ".join(part for part in (self.detail, self.action) if part)

    def __repr__(self):
        return f"KnownIssue({self.id!r})"


_cache: list[KnownIssue] | None = None


def load_known_issues(force_reload: bool = False) -> list[KnownIssue]:
    """The catalogue, read once and kept. A bad catalogue is treated as empty."""
    global _cache
    if _cache is not None and not force_reload:
        return _cache

    try:
        raw = json.loads(_CATALOGUE_PATH.read_text(encoding="utf-8"))
        _cache = [KnownIssue(entry) for entry in raw.get("issues", [])]
    except Exception:
        _cache = []
    return _cache


def explain(text) -> KnownIssue | None:
    """The catalogue entry describing this error, if one recognises it."""
    if not text:
        return None
    text = str(text)
    for issue in load_known_issues():
        if issue.matches(text):
            return issue
    return None


def describe_failure(text, include_original: bool = True) -> str:
    """An error phrased for a user. Unrecognised errors are returned untouched."""
    if not text:
        return ""

    text = str(text)
    issue = explain(text)
    if issue is None:
        return text

    lead = issue.summary or text
    advice = issue.advice()

    if include_original and text.lower() not in lead.lower():
        return f"{lead}. {advice} [{text}]" if advice else f"{lead}. [{text}]"
    return f"{lead}. {advice}" if advice else lead


DIAGNOSTIC_LEVELS = ("info", "warning", "error")


def _backend_title(device_type: str) -> str:
    return f"The {device_type.upper()} backend could not be loaded"


def server_diagnostics(server_info) -> list[dict]:
    """Server-level faults worth showing, newest server payload in, list out."""
    info = server_info or {}
    backends = info.get("backends") or {}
    if not isinstance(backends, dict):
        return []

    server = info.get("hostname") or info.get("ip") or "server"
    issues = []

    for device_type, entry in sorted(backends.items()):
        if not isinstance(entry, dict) or entry.get("available", True):
            continue
        reason = str(entry.get("error") or "no reason was reported")
        known = explain(reason)
        issues.append(
            {
                "id": f"{server}:backend:{device_type}:{known.id if known else reason}",
                "device_type": device_type,
                "level": "error",
                "title": known.summary if known else _backend_title(device_type),
                "message": (
                    known.advice()
                    if known and known.advice()
                    else f"{device_type.upper()} hardware cannot be used on "
                    f"{server} until this is fixed."
                ),
                "detail": reason,
            }
        )

    return issues


__all__ = [
    "DIAGNOSTIC_LEVELS",
    "KnownIssue",
    "describe_failure",
    "explain",
    "load_known_issues",
    "server_diagnostics",
]

"""Recognised failures and the plain-language explanation for each.

The Monitor and the Configurator both surface errors that originate on the
server, and each used to word them however its own code happened to. The
catalogue in ``known_issues.json`` is the single place those explanations live:
both GUIs render errors through :func:`explain`, so the same cause reads the
same way wherever it appears, and teaching BioView about a new failure means
adding an entry to the JSON rather than editing either GUI.
"""
import json
import re
from pathlib import Path
from typing import List, Optional


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


_cache: Optional[List[KnownIssue]] = None


def load_known_issues(force_reload: bool = False) -> List[KnownIssue]:
    """The catalogue, read once and kept.

    A malformed or missing catalogue must never take the application down: it
    is there to make errors clearer, so failing to read it just means errors
    are reported exactly as the server phrased them.
    """
    global _cache
    if _cache is not None and not force_reload:
        return _cache

    try:
        raw = json.loads(_CATALOGUE_PATH.read_text(encoding="utf-8"))
        _cache = [KnownIssue(entry) for entry in raw.get("issues", [])]
    except Exception:
        _cache = []
    return _cache


def explain(text) -> Optional[KnownIssue]:
    """The catalogue entry describing this error, if one recognises it.

    Entries are checked in file order, so put the specific ones first: a driver
    blocked by Memory Integrity is also an MPDRVERR, and the specific cause is
    the more useful thing to say.
    """
    if not text:
        return None
    text = str(text)
    for issue in load_known_issues():
        if issue.matches(text):
            return issue
    return None


def describe_failure(text, include_original: bool = True) -> str:
    """An error phrased for a user, with guidance when the cause is recognised.

    Unrecognised errors are returned untouched -- better the server's own words
    than a vague stand-in that hides them.
    """
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


__all__ = ["KnownIssue", "load_known_issues", "explain", "describe_failure"]

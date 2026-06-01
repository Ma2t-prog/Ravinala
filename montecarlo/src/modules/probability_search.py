"""
Full-text search and filtering for the Probability Bible.
"""
from __future__ import annotations
import re
from typing import Any


def _text_of(entry: dict) -> str:
    """Concatenate all searchable text fields of an entry."""
    parts = [
        entry.get("title", ""),
        entry.get("statement", ""),
        entry.get("intuition", ""),
        entry.get("example", "") or "",
        entry.get("finance_application", "") or "",
        " ".join(entry.get("keywords", [])),
        entry.get("proof", "") or "",
    ]
    return " ".join(str(p) for p in parts).lower()


def search_entries(
    bible: dict,
    query: str = "",
    levels: list[str] | None = None,
    types: list[str] | None = None,
    chapter_id: str | None = None,
) -> list[dict]:
    """
    Search and filter entries across the entire Probability Bible.

    Parameters
    ----------
    bible : dict
        The PROBABILITY_BIBLE dict.
    query : str
        Free-text search string. Empty = no text filter.
    levels : list[str] | None
        Filter by level tags (L1, L2, L3, M1, M2, PhD, RESEARCH).
        None = no filter.
    types : list[str] | None
        Filter by entry type (DEFINITION, THEOREM, etc.).
        None = no filter.
    chapter_id : str | None
        Restrict to a specific chapter. None = all chapters.

    Returns
    -------
    list[dict]
        Matched entries, each augmented with keys:
        ``chapter_id``, ``chapter_title``, ``section_id``, ``section_title``.
    """
    tokens = [t.lower() for t in re.split(r"\s+", query.strip()) if t] if query.strip() else []

    results: list[dict] = []
    for chapter in bible.get("chapters", []):
        if chapter_id and chapter["id"] != chapter_id:
            continue
        for section in chapter.get("sections", []):
            for entry in section.get("entries", []):
                # Level filter
                if levels and entry.get("level") not in levels:
                    continue
                # Type filter
                if types and entry.get("type") not in types:
                    continue
                # Text filter
                if tokens:
                    body = _text_of(entry)
                    if not all(t in body for t in tokens):
                        continue
                # Build augmented result
                result = dict(entry)
                result["chapter_id"] = chapter["id"]
                result["chapter_title"] = chapter["title"]
                result["section_id"] = section["id"]
                result["section_title"] = section["title"]
                results.append(result)

    return results


def highlight(text: str, query: str) -> str:
    """
    Return text with query tokens wrapped in <mark> tags.
    Safe for use inside st.markdown(unsafe_allow_html=True).
    """
    if not query.strip():
        return text
    tokens = re.split(r"\s+", query.strip())
    for token in tokens:
        if token:
            pattern = re.compile(re.escape(token), re.IGNORECASE)
            text = pattern.sub(
                lambda m: f'<mark style="background:rgba(0,217,166,0.25);color:#00D9A6;'
                          f'border-radius:3px;padding:0 2px">{m.group()}</mark>',
                text,
            )
    return text


def count_by_chapter(bible: dict) -> dict[str, int]:
    """Return {chapter_id: entry_count} for all chapters."""
    return {
        ch["id"]: sum(len(sec.get("entries", [])) for sec in ch.get("sections", []))
        for ch in bible.get("chapters", [])
    }


def count_total(bible: dict) -> int:
    return sum(count_by_chapter(bible).values())


def get_entry_by_id(bible: dict, entry_id: str) -> dict | None:
    """Look up a single entry by its dot-notation ID (e.g. '4.2.5')."""
    parts = entry_id.split(".")
    if len(parts) < 3:
        return None
    ch_id, sec_id = parts[0], ".".join(parts[:2])
    for chapter in bible.get("chapters", []):
        if chapter["id"] != ch_id:
            continue
        for section in chapter.get("sections", []):
            if section["id"] != sec_id:
                continue
            for entry in section.get("entries", []):
                if entry["id"] == entry_id:
                    return entry
    return None

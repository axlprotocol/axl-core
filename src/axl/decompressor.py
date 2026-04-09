"""AXL Decompressor v0.8.0

Focused fixes for the v3 round-trip failures:
- parse single `^key:value` ARG2 values positionally instead of swallowing them as META
- parse trailing bracketed META separately without confusing it with ARG1/ARG2
- group claims by full subject/base subject rather than by tag alone
- render dotted hierarchical subjects (`company.revenue`) as sections + bullets
"""

from __future__ import annotations

import re
from collections import defaultdict
from typing import Optional


TAG_NAMES = {
    "$": "Financial",
    "@": "Entity",
    "#": "Metric",
    "!": "Event",
    "~": "State",
    "^": "Value",
}

VALID_TEMPS = {"NOW", "1H", "4H", "1D", "1W", "1M", "HIST"}


def _humanize_token(text: str) -> str:
    return text.replace("_", " ").strip()


def _subject_parts(tag_value: str) -> tuple[str, Optional[str]]:
    if "." not in tag_value:
        return _humanize_token(tag_value), None
    base, aspect = tag_value.split(".", 1)
    return _humanize_token(base), _humanize_token(aspect)


def _clean_arg(arg: Optional[str]) -> str:
    if not arg:
        return ""

    arg = re.sub(r"^<-@", "according to ", arg)
    arg = re.sub(r"^<-", "because ", arg)
    arg = re.sub(r"^RE:", "references ", arg)

    parts = [p.strip() for p in arg.split("+") if p.strip()]
    expanded: list[str] = []
    for part in parts:
        clean_part = re.sub(r"^[\^~\$@#!]", "", part)
        if ":" in clean_part:
            key, val = clean_part.split(":", 1)
            key = _humanize_token(key)
            val = _humanize_token(val)
            if "=" in val:
                role, actual = val.split("=", 1)
                expanded.append(f"{_humanize_token(role)} {actual}")
            else:
                expanded.append(f"{key}: {val}")
        else:
            expanded.append(_humanize_token(clean_part))
    return ", ".join(expanded).strip()


def _extract_meta(line: str) -> tuple[str, dict[str, str]]:
    meta: dict[str, str] = {}

    def repl(match: re.Match[str]) -> str:
        meta[match.group(1)] = match.group(2)
        return ""

    stripped = re.sub(r"\s*\[\^(\w+):([^\]]+)\]", repl, line).strip()
    return stripped, meta


def parse_packet(line: str) -> Optional[dict]:
    """Parse a single AXL v3 packet line.

    Important v0.8.0 fix: parsing is now positional first. A field like
    `^pct:30%` is preserved as ARG2 if it appears in ARG2 position.
    """
    if not line or not isinstance(line, str):
        return None

    line = line.strip()
    if not line:
        return None

    try:
        line_no_meta, meta = _extract_meta(line)
        parts = [p.strip() for p in line_no_meta.split("|")]
        if len(parts) < 3:
            return None

        raw_id = parts[0]
        if raw_id.startswith("ID:"):
            raw_id = raw_id[3:]
        agent_id = raw_id

        op_cc = parts[1]
        dot = op_cc.find(".")
        if dot < 0:
            return None
        op = op_cc[:dot].upper()
        if op not in ("OBS", "INF", "CON", "MRG", "SEK", "YLD", "PRD"):
            return None
        try:
            cc = int(op_cc[dot + 1 :])
        except ValueError:
            cc = 50

        subj = parts[2] if len(parts) > 2 else ""
        tag = "^"
        tag_value = subj
        if subj and subj[0] in TAG_NAMES:
            tag = subj[0]
            tag_value = subj[1:].lstrip(".")
        tag_value = tag_value.strip()

        remaining = parts[3:]
        temp = "NOW"
        if remaining and remaining[-1] in VALID_TEMPS:
            temp = remaining.pop()

        arg1 = remaining[0] if len(remaining) >= 1 else None
        arg2 = remaining[1] if len(remaining) >= 2 else None
        if len(remaining) > 2:
            tail = [p for p in remaining[1:] if p]
            arg2 = "|".join(tail) if tail else arg2

        base_subject, aspect = _subject_parts(tag_value)

        return {
            "id": agent_id,
            "op": op,
            "cc": cc,
            "tag": tag,
            "tag_value": _humanize_token(tag_value),
            "base_subject": base_subject,
            "aspect": aspect,
            "arg1": _clean_arg(arg1),
            "arg2": _clean_arg(arg2),
            "temp": temp,
            "meta": meta,
            "raw": line,
        }
    except Exception:
        return None


def strip_kernel(text: str) -> str:
    if not text or not isinstance(text, str):
        return ""

    marker = "---PACKETS---"
    idx = text.find(marker)
    if idx >= 0:
        return text[idx + len(marker) :].strip()

    lines = text.split("\n")
    for i, line in enumerate(lines):
        line = line.strip()
        if not line:
            continue
        if "|" in line and re.search(r"\b(?:OBS|INF|CON|MRG|SEK|YLD|PRD)\.\d{2}\b", line):
            return "\n".join(lines[i:]).strip()

    return text.strip()


def _claim_text(parsed: dict) -> str:
    label = parsed["aspect"] or parsed["base_subject"] or "unknown"
    arg1 = parsed["arg1"]
    arg2 = parsed["arg2"]
    cc = parsed["cc"]
    temp = parsed["temp"]
    op = parsed["op"]

    if op == "OBS":
        core = arg2 or arg1 or "noted"
        return f"{label}: {core} ({cc}% confidence)"
    if op == "INF":
        if arg1 and arg2:
            return f"{label}: {arg2}; based on {arg1} ({cc}% confidence)"
        if arg1:
            return f"{label}: based on {arg1} ({cc}% confidence)"
        return f"{label}: inferred {arg2 or ''} ({cc}% confidence)".strip()
    if op == "CON":
        if arg1 and arg2:
            return f"{label}: contradicts {arg1}; {arg2} ({cc}% confidence)"
        return f"{label}: contradiction noted ({cc}% confidence)"
    if op == "MRG":
        detail = arg2 or arg1 or "synthesis"
        return f"{label}: synthesis of {detail} ({cc}% confidence)"
    if op == "SEK":
        detail = arg2 or arg1 or "information requested"
        return f"{label}: {detail}"
    if op == "YLD":
        detail = arg2 or "belief updated"
        if arg1:
            return f"{label}: {detail}; because {arg1} ({cc}% confidence)"
        return f"{label}: {detail} ({cc}% confidence)"
    if op == "PRD":
        detail = arg2 or arg1 or "prediction"
        if temp != "NOW":
            return f"{label}: {detail}; within {temp} ({cc}% confidence)"
        return f"{label}: {detail} ({cc}% confidence)"
    return f"{label}: {arg2 or arg1 or 'noted'} ({cc}% confidence)"


def v3_to_english(packets_text: str) -> list[dict]:
    text = strip_kernel(packets_text)
    if not text:
        return []

    claims = []
    for line in text.split("\n"):
        line = line.strip()
        if not line:
            continue
        parsed = parse_packet(line)
        if not parsed:
            continue
        claim_text = _claim_text(parsed)
        claim_text = re.sub(r"\s+", " ", claim_text).strip()
        claims.append(
            {
                "op": parsed["op"],
                "cc": parsed["cc"],
                "tag": parsed["tag"],
                "tag_value": parsed["tag_value"],
                "base_subject": parsed["base_subject"],
                "aspect": parsed["aspect"],
                "claim_text": claim_text,
                "temp": parsed["temp"],
                "raw": parsed["raw"],
            }
        )
    return claims


def format_decompressed(claims: list[dict]) -> str:
    """Group by semantic subject, not by tag alone."""
    if not claims:
        return "No valid packets found."

    groups: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for claim in claims:
        key = (claim.get("tag", "^"), claim.get("base_subject") or claim.get("tag_value") or "unknown")
        groups[key].append(claim)

    for key in groups:
        groups[key].sort(key=lambda x: x.get("cc", 0), reverse=True)

    tag_order = ["@", "$", "#", "!", "~", "^"]

    def section_sort_key(item: tuple[tuple[str, str], list[dict]]):
        (tag, base_subject), section_claims = item
        tag_rank = tag_order.index(tag) if tag in tag_order else len(tag_order)
        best_cc = max((c.get("cc", 0) for c in section_claims), default=0)
        return (tag_rank, -best_cc, base_subject.lower())

    sections = []
    for (tag, base_subject), section_claims in sorted(groups.items(), key=section_sort_key):
        header = base_subject or TAG_NAMES.get(tag, "Other")
        lines = [f"  - {claim['claim_text']}" for claim in section_claims]
        sections.append(f"[{header}]\n" + "\n".join(lines))

    return "\n\n".join(sections)


def decompress(text: str) -> str:
    claims = v3_to_english(text)
    return format_decompressed(claims)

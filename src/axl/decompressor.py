"""AXL Decompressor v2.0

Rule-based prose reconstruction engine. No LLM dependency.
Produces readable English from AXL v3 packets using:
- 200+ abbreviation reversals
- Financial value formatting with context awareness
- State-as-adjective integration
- Operation-specific sentence templates (15 patterns)
- Topic-based section grouping (not raw subject grouping)
- Confidence-based language (high=fact, low=estimated)
- Subject cleaning (strip articles, expand known aliases)
- Evidence humanization
- Empty packet suppression
"""

from __future__ import annotations

import re
from collections import defaultdict
from typing import Optional

# -- Constants ---------------------------------------------------------------

TAG_NAMES = {
    "$": "Financial",
    "@": "Entity",
    "#": "Metric",
    "!": "Event",
    "~": "State",
    "^": "Value",
}

VALID_TEMPS = {"NOW", "1H", "4H", "1D", "1W", "1M", "HIST"}

# Temporal to prose
TEMP_PROSE = {
    "NOW": "",
    "1H": "within the next hour",
    "4H": "within four hours",
    "1D": "within the next day",
    "1W": "within the next week",
    "1M": "within the next month",
    "HIST": "historically",
}

# -- Abbreviation reversal (200+ entries) ------------------------------------

_ABBREV_REVERSE = {
    # Core financial
    "rev": "revenue", "amt": "amount", "val": "valuation",
    "grw": "growth", "pct": "percent", "cost": "costs",
    "costs": "costs", "margin": "margin", "profit": "profit",
    "cash": "cash", "loss": "loss", "rate": "rate",
    "inv": "investment", "fin": "financial", "funding": "funding",
    "capital": "capital", "debt": "debt", "equity": "equity",
    "runway": "runway", "burn": "burn rate", "opex": "operating expenses",
    "capex": "capital expenditures", "ebitda": "EBITDA",
    "arpu": "average revenue per user", "ltv": "lifetime value",
    "cac": "customer acquisition cost", "mrr": "monthly recurring revenue",
    "arr": "annual recurring revenue", "nrc": "non-recurring costs",
    "cogs": "cost of goods sold",
    # Operations
    "fac": "facilities", "faciliti": "facilities",
    "location": "locations", "orders": "orders",
    "volume": "volume", "stations": "stations",
    "brands": "brands", "ops": "operations",
    "customer": "customers", "cust": "customers",
    "emp": "employees", "staff": "staff",
    "turn": "turnover", "churn": "churn",
    "occupanc": "occupancy", "capacity": "capacity",
    # Technology
    "tech": "technology", "dev": "development",
    "develope": "developers", "frontend": "frontend",
    "analyst": "analyst", "platform": "platform",
    "licensin": "licensing", "applicat": "applications",
    "predicti": "prediction", "mape": "MAPE",
    "stars": "star rating", "quality": "quality score",
    # Business
"mgmt": "management",
    "exp": "expansion", "acq": "acquisition",
    "comp": "competition", "commissi": "commission",
    "comm": "commission", "share": "market share",
    "penetr": "penetration", "pen": "penetration",
    "sat": "satisfaction", "ret": "retention",
    "sub": "subscription", "prtn": "partnership",
    "proj": "projection", "projecti": "projection",
    "rec": "recommendation", "scenario": "scenario",
    "multiple": "multiple", "premium": "premium",
    "return": "return", "stake": "stake",
    "rights": "rights", "shares": "shares",
    "threshol": "threshold", "deadline": "deadline",
    "proceeds": "proceeds", "terms": "terms",
    "pre": "pre-money", "sheet": "term sheet",
    # People/roles
    "experien": "experience", "individu": "individuals",
    "confirma": "confirmations", "completi": "completion",
    "provisio": "provisions", "executiv": "executives",
    "assessme": "assessments", "statemen": "statements",
    "meetings": "meetings", "financia": "financial",
    # Places/context
    "columbia": "British Columbia", "vancouve": "Vancouver",
    "pacific": "Pacific", "langford": "Langford",
    "january": "January", "q1": "Q1", "q4": "Q4",
    "apr": "April", "mar": "March",
    # Food/industry
    "ingredie": "ingredients", "freshnes": "freshness",
    "dissatis": "dissatisfaction", "reviews": "reviews",
    "estimate": "estimated", "items": "items",
    "waste": "waste", "food": "food",
    "delivery": "delivery", "ghost": "ghost kitchen",
    "househol": "household", "average": "average",
    "tenant": "tenant", "rental": "rental",
    # Misc
    "data": "data", "count": "count",
    "date": "date", "end": "end",
    "total": "total", "combinat": "combined",
    "process": "process", "period": "period",
    "breakdow": "breakdown", "improvem": "improvements",
    "carryove": "carryover", "deprecia": "depreciation",
    "contribu": "contribution", "calendar": "calendar year",
    "compound": "compound", "principa": "principal",
    "profitab": "profitability", "openings": "new openings",
    "income": "income", "assembly": "per location",
    "machine": "per unit", "kernel": "per unit",
    "node": "per unit", "circuit": "per unit",
    "protocol": "per unit", "pi": "per unit",
    "way": "per unit",
}

# State words that become adjectives
_STATE_ADJECTIVES = {
    "pre": "pre-money", "post": "post-money",
    "gross": "gross", "net": "net",
    "proprietary": "proprietary", "current": "current",
    "historical": "historical", "fiscal": "fiscal year",
    "monthly": "monthly", "quarterly": "quarterly",
    "annual": "annual", "daily": "daily",
    "significant": "significant", "substantial": "substantial",
    "commercial": "commercial", "modular": "modular",
    "premium": "premium", "artisan": "artisan",
    "dominant": "dominant", "comprehensive": "comprehensive",
    "preliminary": "preliminary", "comparable": "comparable",
    "outstanding": "outstanding", "provisional": "provisional",
    "senior": "senior", "junior": "junior",
    "total": "total", "average": "average",
    "national": "national", "canadian": "Canadian",
    "global": "global", "local": "local",
    "new": "new", "additional": "additional",
    "key": "key", "primary": "primary",
    "formal": "formal", "internal": "internal",
    "deep": "advanced", "algorithmic": "algorithmic",
    "organic": "organic", "distressed": "distressed",
    "forward": "forward-looking",
}

# Known 2-3 char subject aliases that are meaningless without expansion
_GARBAGE_SUBJECTS = {
    "co", "cl", "clo", "su", "mv", "tu", "tus",
    "gkb", "do", "fa", "to", "on", "un", "tr",
    "br", "cr", "nd", "ja", "ma", "lo", "ct",
    "mem", "que", "cog", "ckc", "ca", "cc",
    "pc", "la", "it", "op", "ip", "vmp", "vk",
    "va", "am", "tuo", "tri", "cre", "uni", "nor",
    "kh",
}

# Topic classification keywords
_TOPIC_FINANCIAL = {
    "revenue", "cost", "margin", "profit", "cash", "burn",
    "valuation", "funding", "investment", "financing",
    "gross", "opex", "income", "loss", "ebitda", "capital",
    "seed", "series", "round",
}
_TOPIC_TEAM = {
    "team", "ceo", "cto", "coo", "cfo", "founder",
    "director", "officer", "management", "executive",
    "bios", "portfolio", "experience",
}
_TOPIC_MARKET = {
    "market", "share", "competition", "competitor",
    "platform", "delivery", "penetration", "occupancy",
    "ghost", "kitchen",
}
_TOPIC_RISK = {
    "risk", "concern", "dispute", "challenge", "inflation",
    "dependency", "turnover", "complaint", "downsizing",
}
_TOPIC_OPS = {
    "facility", "facilities", "location", "station",
    "order", "brand", "kitchen", "cooks", "worker",
    "buildout", "lease", "tenant",
}

_YEAR_RE = re.compile(r"^(19|20)\d{2}$")
_MONEY_RE = re.compile(r"^\d[\d.]*[MBKmbk]$")
_MULT_RE = re.compile(r"^\d[\d.]*x$")
_PCT_RE = re.compile(r"[%]")

# Financial key terms that warrant a $ prefix on K/M/B values
_FINANCIAL_KEYS = {
    "rev", "revenue", "cost", "costs", "price", "salary", "budget", "fee",
    "fund", "funding", "profit", "loss", "margin", "valuation", "cash",
    "burn", "amt", "amount", "funding", "investment", "capital", "opex",
    "proceeds", "capex", "ebitda", "mrr", "arr", "cac", "ltv", "arpu",
    "cogs", "nrc", "debt", "equity", "credit", "income",
}

# v3.1 bundle pattern: label[value] or label[value,qualifier]
_BUNDLE_RE = re.compile(r"([^[;]+)\[([^\]]*)\]")


# -- Parsing (kept from v0.9.0) ---------------------------------------------

def _humanize_token(text: str) -> str:
    return text.replace("_", " ").strip()


def _subject_parts(tag_value: str) -> tuple[str, Optional[str]]:
    if "." not in tag_value:
        return _humanize_token(tag_value), None
    base, aspect = tag_value.split(".", 1)
    return _humanize_token(base), _humanize_token(aspect)


def _extract_meta(line: str) -> tuple[str, dict[str, str]]:
    meta: dict[str, str] = {}

    def repl(match: re.Match[str]) -> str:
        meta[match.group(1)] = match.group(2)
        return ""

    stripped = re.sub(r"\s*\[\^(\w+):([^\]]+)\]", repl, line).strip()
    return stripped, meta


def parse_packet(line: str) -> Optional[dict]:
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

        op_cc = parts[1]
        dot = op_cc.find(".")
        if dot < 0:
            return None
        op = op_cc[:dot].upper()
        if op not in ("OBS", "INF", "CON", "MRG", "SEK", "YLD", "PRD"):
            return None
        try:
            cc = int(op_cc[dot + 1:])
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
            "id": raw_id,
            "op": op,
            "cc": cc,
            "tag": tag,
            "tag_value": _humanize_token(tag_value),
            "base_subject": base_subject,
            "aspect": aspect,
            "arg1": arg1,
            "arg2": arg2,
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
        return text[idx + len(marker):].strip()
    lines = text.split("\n")
    for i, line_text in enumerate(lines):
        line_text = line_text.strip()
        if not line_text:
            continue
        if "|" in line_text and re.search(
            r"\b(?:OBS|INF|CON|MRG|SEK|YLD|PRD)\.\d{2}\b",
            line_text,
        ):
            return "\n".join(lines[i:]).strip()
    return text.strip()


# -- Ontology expansion ------------------------------------------------------

def _extract_ontology(packets: list[dict]) -> dict[str, str]:
    aliases: dict[str, str] = {}
    for pkt in packets:
        subj = pkt.get("tag_value", "")
        if not subj.startswith("m.O."):
            continue
        arg2_raw = pkt.get("arg2", "") or ""
        for part in arg2_raw.split("+"):
            part = part.strip()
            if part.startswith("^df:"):
                part = part[4:]
            if "=" in part:
                alias, full = part.split("=", 1)
                alias = alias.strip()
                full = full.strip()
                if alias and full:
                    aliases[alias.lower()] = full
    return aliases


def _expand_alias(value: str, aliases: dict[str, str]) -> str:
    if not aliases:
        return value
    clean = value.replace("_", " ")
    if clean.lower() in aliases:
        return aliases[clean.lower()]
    if "." in clean:
        prefix, rest = clean.split(".", 1)
        expanded = aliases.get(prefix.lower())
        if expanded:
            return f"{expanded} {rest}"
    return clean


# -- Subject cleaning --------------------------------------------------------

# Generic references that should resolve to primary entity
_GENERIC_REFS = {
    "the company", "the firm", "the organization",
    "the business", "the enterprise", "the startup",
    "the corporation", "the group", "the entity",
}


def _primary_entity(aliases: dict[str, str]) -> str:
    """Get the first/primary entity from the ontology."""
    if not aliases:
        return ""
    # First value in aliases dict (insertion order)
    for full_name in aliases.values():
        return full_name
    return ""


def _clean_subject(
    base: str, aspect: Optional[str], aliases: dict[str, str],
) -> str:
    """Produce a readable subject phrase."""
    # Expand aliases
    base = _expand_alias(base, aliases)

    # Resolve generic references to primary entity
    base_lower = base.lower().strip()
    if base_lower in _GENERIC_REFS:
        primary = _primary_entity(aliases)
        if primary:
            base = primary

    # Strip leading articles from aspect
    if aspect:
        aspect_clean = re.sub(
            r"^(The|the|A|a|An|an|The s|the s)\s*", "", aspect,
        ).strip()
        if not aspect_clean or aspect_clean.lower() in (
            "the", "a", "an", "s",
        ):
            aspect = None
        else:
            aspect = aspect_clean

    # If base is a garbage 2-3 char alias with no expansion
    if base_lower in _GARBAGE_SUBJECTS and len(base) <= 4:
        primary = _primary_entity(aliases)
        if primary:
            base = primary
        else:
            return (
                base.upper()
                if not aspect
                else f"{base.upper()} {aspect}"
            )

    # Build subject phrase
    if aspect:
        return f"{base} - {aspect}"

    # Capitalize if needed
    if base and base[0].islower() and not base.startswith("the"):
        base = base[0].upper() + base[1:]

    return base


# -- Value formatting --------------------------------------------------------

def _parse_bundles(arg2: str) -> Optional[list[dict]]:
    """Parse label[value,qualifier] bundles from v3.1 syntax."""
    if not arg2 or "[" not in arg2:
        return None

    bundles = []
    for item in arg2.split(";"):
        item = item.strip()
        if not item:
            continue
        m = _BUNDLE_RE.match(item)
        if m:
            label = m.group(1).strip()
            inner = m.group(2).strip()
            parts = [p.strip() for p in inner.split(",")]
            value = parts[0]
            qualifier = parts[1] if len(parts) > 1 else None
            bundles.append({"label": label, "value": value, "qualifier": qualifier})
        else:
            bundles.append({"label": item, "value": item, "qualifier": None})

    return bundles if bundles else None


def _format_bundle_list(
    bundles: list[dict], ent_anchors: Optional[dict] = None
) -> str:
    """Convert parsed v3.1 bundles into readable prose."""
    phrases = []
    for b in bundles:
        label_raw = b["label"].replace("_", " ").strip()
        # Expand @ent.XX labels to full names
        ent_m = re.match(r"@ent\.(\w+)", label_raw)
        if ent_m:
            alias = ent_m.group(1)
            label_raw = (ent_anchors or {}).get(alias, alias)
        label_l = label_raw.lower()
        label_exp = _ABBREV_REVERSE.get(label_l, label_raw)
        value = b["value"]
        qualifier = b["qualifier"]

        # Expand transition values (21.3%->15.8%)
        if "->" in value:
            parts = value.split("->", 1)
            value = f"{parts[0]} to {parts[1]}"

        if qualifier:
            phrases.append(f"{label_exp} {value} ({qualifier})")
        else:
            phrases.append(f"{label_exp} {value}")

    return ", ".join(phrases)


def _format_single_value(key: str, val: str) -> str:
    """Format a single key:value pair into readable text."""
    key_l = key.lower().strip()
    v = val.strip()

    # Expand abbreviated key
    if key_l in _ABBREV_REVERSE:
        key = _ABBREV_REVERSE[key_l]
    key_l = key.lower()

    # Year detection - never add $
    if _YEAR_RE.match(v):
        return f"in {v}"

    # Quarter-year (Q1 2025)
    if re.match(r"Q[1-4][\s_]20\d{2}", v):
        return f"in {v.replace('_', ' ')}"

    # Percentage - never add $
    if _PCT_RE.search(v):
        if key_l in ("growth", "grw"):
            return f"{v} growth"
        if key_l in ("margin",):
            return f"{v} margin"
        if key_l in ("share", "market share"):
            return f"{v} market share"
        return v

    # Multiplier (6.0x)
    if _MULT_RE.match(v):
        return f"{v} multiple"

    # Money values (M/B/K suffix) - only add $ for financial keys
    if _MONEY_RE.match(v):
        if key_l == "date":
            return v
        orig_key_l = key.lower().strip() if key else ""
        # Use original key (before abbrev expansion) to check financial context
        raw_key_l = orig_key_l.split()[0] if orig_key_l else ""
        if raw_key_l in _FINANCIAL_KEYS or key_l in _FINANCIAL_KEYS:
            return f"${v}"
        return v  # non-financial K/M (facilities, locations, orders)

    # Bare numbers in financial context
    if re.match(r"^\d[\d,.]*$", v) and key_l in (
        "revenue", "valuation", "amount", "costs", "profit",
        "cash", "funding", "investment", "financing",
        "capital", "proceeds", "term sheet",
    ):
        return f"${v}"

    # Date key
    if key_l == "date":
        return f"in {v.replace('_', ' ')}"

    # State key - skip (handled separately)
    if key_l == "state":
        return ""

    # Count
    if key_l == "count":
        return v

    # Default: value with key as context
    if key_l in ("need", "need info"):
        return v.replace("_", " ")

    # If value is a word/phrase, just return it
    if not v[0].isdigit():
        return f"{v.replace('_', ' ')} {key}"

    return f"{v} {key}"


def _extract_state(arg2: Optional[str]) -> str:
    """Extract state adjective from raw ARG2."""
    if not arg2:
        return ""
    match = re.search(r"~state:(\w+)", arg2)
    if not match:
        return ""
    state_raw = match.group(1).replace("_", " ")
    return _STATE_ADJECTIVES.get(state_raw.lower(), state_raw)


def _format_values(
    arg2: Optional[str], ent_anchors: Optional[dict] = None
) -> str:
    """Format all values from raw ARG2 into readable prose."""
    if not arg2:
        return ""

    # v3.1: handle causal chain with => operator in arg2
    # e.g. "food_inflation[+8.2%] => menu_price[+4.5%] => margin[21.3%->15.8%]"
    if "=>" in arg2:
        chain_parts = [p.strip() for p in arg2.split("=>")]
        chain_texts = []
        for cp in chain_parts:
            bundles = _parse_bundles(cp)
            if bundles:
                chain_texts.append(_format_bundle_list(bundles, ent_anchors))
            else:
                chain_texts.append(cp.replace("_", " "))
        return ", which caused ".join(chain_texts)

    # v3.1: detect label[value] bundle format (semicolons as separators)
    bundles = _parse_bundles(arg2)
    if bundles is not None:
        return _format_bundle_list(bundles, ent_anchors)

    # Classic v3: ^label:value+ format
    parts = [p.strip() for p in arg2.split("+") if p.strip()]
    formatted = []

    for part in parts:
        # Preserve $ prefix - track if it was present before stripping sigils
        has_dollar = part.lstrip("^~@#!").startswith("$")
        clean = re.sub(r"^[\^~\$@#!]", "", part)

        # Skip state entries (handled separately)
        if clean.startswith("state:"):
            continue

        if ":" in clean:
            key, val = clean.split(":", 1)
            key = key.replace("_", " ").strip()
            val = val.replace("_", " ").strip()
            if not val:
                continue
            rendered = _format_single_value(key, val)
            if rendered and rendered not in formatted:
                formatted.append(rendered)
        else:
            text = clean.replace("_", " ")
            # Re-add $ if it was stripped and value looks monetary
            if has_dollar and text and not text.startswith("$"):
                text = f"${text}"
            if text and text not in formatted:
                formatted.append(text)

    return ", ".join(formatted)


# -- Evidence formatting -----------------------------------------------------

def _format_evidence(arg1: Optional[str]) -> str:
    """Format ARG1 evidence into readable text."""
    if not arg1:
        return ""

    text = arg1.strip()

    # v3.1: causal operator => (starting)
    if text.startswith("=>"):
        text = text[2:].strip()
        text = text.replace("_", " ")
        return f"causing {text}"

    # v3.1: inline => causal chain in evidence (e.g. ask[$34M,8.9x] => above_comps)
    if "=>" in text and "[" in text:
        # Treat as a values-style causal chain
        return _format_values(text)

    # v3.1: numeric transition ->
    if text.startswith("->"):
        text = text[2:].strip()
        parts = text.split("->", 1)
        if len(parts) == 2:
            return f"from {parts[0].strip()} to {parts[1].strip()}"
        return text.replace("_", " ")

    # Strip classic prefixes
    text = re.sub(r"^<-@?", "", text)
    text = re.sub(r"^RE:", "references ", text)

    # v3.1: expand subject references like $CK.rev.FY25 or @ent.XX
    text = re.sub(r"@ent\.(\w+)", r"\1", text)
    # Expand dot-path financial references: $CK.rev.FY25 -> CK revenue FY25
    def _expand_ref(m: re.Match) -> str:
        path = m.group(2)  # e.g. CK.rev.FY25
        parts = path.split(".")
        expanded_parts = []
        for p in parts:
            pl = p.lower()
            expanded_parts.append(_ABBREV_REVERSE.get(pl, p))
        return " ".join(expanded_parts)

    text = re.sub(r"([$@#!~^])(\w+(?:\.\w+)*)", _expand_ref, text)

    # Replace underscores
    text = text.replace("_", " ").strip()

    # Expand abbreviations in evidence
    words = text.split()
    expanded = []
    for w in words:
        wl = w.lower()
        if wl in _ABBREV_REVERSE:
            expanded.append(_ABBREV_REVERSE[wl])
        else:
            expanded.append(w)

    return " ".join(expanded)


# -- Confidence language -----------------------------------------------------

def _confidence_prefix(cc: int) -> str:
    """Return a language qualifier based on confidence level."""
    if cc >= 90:
        return ""  # stated as fact
    if cc >= 80:
        return ""  # still fairly confident
    if cc >= 70:
        return "It is estimated that "
    if cc >= 60:
        return "It is possible that "
    return "With low confidence, "


def _confidence_suffix(cc: int) -> str:
    """Confidence as parenthetical, only for non-obvious cases."""
    if cc >= 85:
        return ""
    return f" ({cc}%)"


# -- Sentence reconstruction ------------------------------------------------

def _build_sentence(
    parsed: dict, aliases: dict[str, str], ent_anchors: Optional[dict] = None
) -> str:
    """Build a readable English sentence from a parsed packet."""
    subject = _clean_subject(
        parsed.get("base_subject", ""),
        parsed.get("aspect"),
        aliases,
    )
    op = parsed["op"]
    cc = parsed["cc"]
    arg1 = parsed.get("arg1")
    arg2 = parsed.get("arg2")
    temp = parsed.get("temp", "NOW")

    # v3.1: for @ent.XX declaration packets (tag_value starts with 'ent.'),
    # ARG1 is the full entity name (not evidence). Clear it from evidence.
    raw_tag_val = parsed.get("tag_value", "")
    if raw_tag_val.startswith("ent.") and arg1 and not arg1.startswith(
        ("<-", "=>", "->", "RE:")
    ):
        arg1 = None  # suppress declaration ARG1 from evidence display

    # v3.1: when ARG1 contains bundle data (has '[') and ARG2 is evidence ('<-'/'=>')
    # swap the semantic roles: treat ARG1 as values, ARG2 as evidence
    if (arg1 and "[" in arg1 and
            arg2 and (arg2.startswith("<-") or arg2.startswith("=>") or arg2.startswith("->"))):
        values_raw, evidence_raw = arg1, arg2
    else:
        values_raw, evidence_raw = arg2, arg1

    state = _extract_state(values_raw)
    values = _format_values(values_raw, ent_anchors)
    evidence = _format_evidence(evidence_raw)
    prefix = _confidence_prefix(cc)
    suffix = _confidence_suffix(cc)
    temporal = TEMP_PROSE.get(temp, "")

    # Skip completely empty packets
    if not values and not state and not evidence and op == "OBS":
        return ""

    # Build based on operation
    if op == "OBS":
        if values and state:
            return (
                f"{prefix}{subject} reported {values} "
                f"({state}).{suffix}"
            )
        if values:
            return f"{prefix}{subject} reported {values}.{suffix}"
        if state:
            return (
                f"{prefix}{subject} is described as "
                f"{state}.{suffix}"
            )
        return ""

    if op == "INF":
        if evidence and values:
            return (
                f"{prefix}Based on {evidence}, {subject.lower()} "
                f"shows {values}.{suffix}"
            )
        if evidence and state:
            return (
                f"{prefix}Based on {evidence}, {subject.lower()} "
                f"is {state}.{suffix}"
            )
        if evidence:
            return (
                f"{prefix}Analysis of {subject.lower()}: "
                f"{evidence}.{suffix}"
            )
        if values:
            return (
                f"{prefix}{subject} indicates {values}.{suffix}"
            )
        return ""

    if op == "CON":
        details = values or state or "unspecified"
        if evidence:
            return (
                f"{prefix}{subject} faces challenges regarding "
                f"{evidence}: {details}.{suffix}"
            )
        return (
            f"{prefix}{subject} raises concerns: "
            f"{details}.{suffix}"
        )

    if op == "MRG":
        if values:
            if evidence:
                return (
                    f"{prefix}Overall, {subject.lower()} combines "
                    f"{values} (based on {evidence}).{suffix}"
                )
            return (
                f"{prefix}Overall, {subject.lower()} shows "
                f"{values}.{suffix}"
            )
        if state:
            return (
                f"{prefix}Overall, {subject.lower()} is "
                f"{state}.{suffix}"
            )
        return ""

    if op == "SEK":
        detail = values or "additional details"
        return (
            f"Further information is needed regarding "
            f"{subject.lower()}: {detail}."
        )

    if op == "YLD":
        detail = values or state or "position updated"
        if evidence:
            return (
                f"{prefix}{subject} changed position to "
                f"{detail}, based on {evidence}.{suffix}"
            )
        return f"{prefix}{subject} updated: {detail}.{suffix}"

    if op == "PRD":
        tf = f" {temporal}" if temporal else ""
        if values:
            return (
                f"{prefix}{subject} is projected to reach "
                f"{values}{tf}.{suffix}"
            )
        if state:
            return (
                f"{prefix}{subject} outlook is "
                f"{state}{tf}.{suffix}"
            )
        return ""

    return ""


# -- Topic classification ---------------------------------------------------

def _classify_topic(
    subject: str, values: str, op: str, state: str,
) -> str:
    """Assign a claim to a topic section."""
    text = f"{subject} {values} {state}".lower()

    if op == "PRD":
        return "Projections and Valuation"
    if op == "CON":
        return "Risk Factors and Concerns"
    if op == "SEK":
        return "Outstanding Questions"

    for kw in _TOPIC_FINANCIAL:
        if kw in text:
            return "Financial Performance"
    for kw in _TOPIC_TEAM:
        if kw in text:
            return "Management and Team"
    for kw in _TOPIC_RISK:
        if kw in text:
            return "Risk Factors and Concerns"
    for kw in _TOPIC_MARKET:
        if kw in text:
            return "Market and Competition"
    for kw in _TOPIC_OPS:
        if kw in text:
            return "Operations and Facilities"

    return "General Observations"


# -- Main pipeline -----------------------------------------------------------

def _extract_ent_anchors(packets: list[dict]) -> dict[str, str]:
    """Build a registry of @ent.XX aliases from v3.1 declaration packets.

    A declaration packet has subject tag_value starting with 'ent.' and
    arg1 containing the full entity name.
    """
    anchors: dict[str, str] = {}
    for pkt in packets:
        tag_val = pkt.get("tag_value", "")
        if not tag_val.startswith("ent."):
            continue
        alias = tag_val[4:]  # strip 'ent.'
        # Remove any sub-path (ent.CK.sales -> alias = CK)
        alias = alias.split(".")[0]
        arg1 = pkt.get("arg1") or ""
        # arg1 should be the full entity name on first mention
        if arg1 and not arg1.startswith(("<-", "=>", "->", "RE:")):
            anchors[alias] = arg1.strip()
    return anchors


def _resolve_ent_subject(tag_value: str, ent_anchors: dict[str, str]) -> str:
    """Expand @ent.XX subject to full name if known."""
    if not tag_value.startswith("ent."):
        return tag_value
    rest = tag_value[4:]  # e.g. "CK" or "CK.sales" or "WTW"
    parts = rest.split(".", 1)
    alias = parts[0]
    sub = parts[1] if len(parts) > 1 else None
    full = ent_anchors.get(alias, alias)
    if sub:
        return f"{full} - {sub.replace('_', ' ')}"
    return full


def v3_to_english(packets_text: str) -> list[dict]:
    text = strip_kernel(packets_text)
    if not text:
        return []

    all_parsed = []
    for line in text.split("\n"):
        line = line.strip()
        if not line:
            continue
        parsed = parse_packet(line)
        if parsed:
            all_parsed.append(parsed)

    aliases = _extract_ontology(all_parsed)
    ent_anchors = _extract_ent_anchors(all_parsed)

    claims = []
    for parsed in all_parsed:
        subj = parsed.get("tag_value", "")
        if subj.startswith("m.O.") or subj.startswith("m.B."):
            continue

        # v3.1: resolve @ent.XX subjects
        if subj.startswith("ent."):
            full_name = _resolve_ent_subject(subj, ent_anchors)
            # Patch parsed so _build_sentence sees the expanded name
            parsed = dict(parsed)
            dot = full_name.find(" - ")
            if dot >= 0:
                parsed["base_subject"] = full_name[:dot]
                parsed["aspect"] = full_name[dot + 3:]
            else:
                parsed["base_subject"] = full_name
                parsed["aspect"] = None
            # Skip pure declaration packets (arg2 is the entity description)
            # but still emit them as observations

        sentence = _build_sentence(parsed, aliases, ent_anchors)
        if not sentence:
            continue

        state = _extract_state(parsed.get("arg2"))
        values = _format_values(parsed.get("arg2"), ent_anchors)
        subject = _clean_subject(
            parsed.get("base_subject", ""),
            parsed.get("aspect"),
            aliases,
        )
        topic = _classify_topic(
            subject, values, parsed["op"], state,
        )

        claims.append({
            "op": parsed["op"],
            "cc": parsed["cc"],
            "tag": parsed["tag"],
            "tag_value": parsed["tag_value"],
            "base_subject": subject,
            "aspect": parsed.get("aspect"),
            "claim_text": sentence,
            "temp": parsed["temp"],
            "topic": topic,
            "raw": parsed["raw"],
        })
    return claims


def format_decompressed(claims: list[dict]) -> str:
    if not claims:
        return "No valid packets found."

    # Group by topic
    topics: dict[str, list[dict]] = defaultdict(list)
    for claim in claims:
        topics[claim.get("topic", "General")].append(claim)

    # Sort within each topic by confidence
    for key in topics:
        topics[key].sort(
            key=lambda x: x.get("cc", 0), reverse=True,
        )

    # Topic ordering
    topic_order = [
        "General Observations",
        "Financial Performance",
        "Operations and Facilities",
        "Market and Competition",
        "Management and Team",
        "Projections and Valuation",
        "Risk Factors and Concerns",
        "Outstanding Questions",
    ]

    sections = []
    for topic in topic_order:
        if topic not in topics:
            continue
        section_claims = topics[topic]
        if not section_claims:
            continue

        # Build paragraph: join sentences into flowing text
        sentences = []
        for claim in section_claims:
            text = claim["claim_text"].strip()
            if text:
                # Ensure sentence ends with period
                if text and text[-1] not in ".!?":
                    text += "."
                sentences.append(text)

        if sentences:
            # Join into paragraph(s) - max 4 sentences per paragraph
            paragraphs = []
            for i in range(0, len(sentences), 4):
                chunk = sentences[i:i + 4]
                paragraphs.append(" ".join(chunk))
            sections.append(
                f"{topic}\n\n" + "\n\n".join(paragraphs)
            )

    # Any remaining topics not in the order
    for topic, section_claims in topics.items():
        if topic in topic_order:
            continue
        sentences = [
            c["claim_text"].strip()
            for c in section_claims
            if c["claim_text"].strip()
        ]
        if sentences:
            sections.append(
                f"{topic}\n\n" + " ".join(sentences)
            )

    return "\n\n".join(sections)


def decompress(text: str) -> str:
    claims = v3_to_english(text)
    return format_decompressed(claims)

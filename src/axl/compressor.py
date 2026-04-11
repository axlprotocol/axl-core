"""AXL Compressor v0.9.0

Dense semantic compression with entity aliasing.

Architecture:
  Pass 1 - Scan full document, build entity registry with short aliases
  Pass 2 - Extract facts per sentence using quality-fixed pipeline
  Pass 3 - Pack same-subject values into single ARG2, compress evidence
  Pass 4 - Emit compact packets + ontology manifest + bundle manifest

Quality fixes preserved from v0.8.x:
- DATE/year guard before number compaction
- word-scale number normalization ("5 million dollars" -> "5M")
- pronoun and numeric subject suppression
- semantic subject ranking (teams/orgs outrank numbers)
- safer evidence fallback (no generic prepositions as causal)
- no invalid synthetic MRG packets

Density improvements (new in v0.9.0):
- Entity registry with 2-3 char aliases (CloudKitchen -> CK)
- Short agent ID ("C" not "COMPRESS")
- Compressed evidence (verb:object, max 30 chars)
- Same-subject value packing (all values in one ARG2)
- Role-labeled values (^rev:8.5M not ^amt:8.5M)
- Mini kernel (741 chars vs 5,853 full)
- Ontology manifest with entity->alias mappings
"""

from __future__ import annotations

import re
from collections import defaultdict
from typing import Iterable, Optional

import spacy

from axl.emitter import emit_v3
from axl.models import Operation, TagType, V3Packet

# -- Abbreviation dictionary -------------------------------------------------

_ABBREV = {
    "revenue": "rev", "technology": "tech", "operations": "ops",
    "engineering": "eng", "marketing": "mkt", "management": "mgmt",
    "development": "dev", "performance": "perf", "production": "prod",
    "infrastructure": "infra", "acquisition": "acq", "valuation": "val",
    "investment": "inv", "economics": "econ", "analysis": "anl",
    "commission": "comm", "competition": "comp", "expansion": "exp",
    "financial": "fin", "growth": "grw", "partnership": "prtn",
    "platform": "plat", "projection": "proj", "recommendation": "rec",
    "subscription": "sub", "turnover": "turn", "facility": "fac",
    "customer": "cust", "employee": "emp", "percentage": "pct",
    "approximately": "approx", "metropolitan": "metro",
    "penetration": "pen", "satisfaction": "sat", "retention": "ret",
    "intelligence": "intel", "prediction": "pred",
}


def _abbr(word: str, max_len: int = 10) -> str:
    """Abbreviate a word using the dictionary, or truncate."""
    w = word.lower().strip()
    if w in _ABBREV:
        return _ABBREV[w]
    if len(w) <= max_len:
        return w
    return w[:max_len]


# -- Entity Registry --------------------------------------------------------


class EntityRegistry:
    """Assigns short 2-3 char aliases to named entities."""

    def __init__(self):
        self._to_alias: dict[str, str] = {}
        self._to_full: dict[str, str] = {}
        self._used: set[str] = set()

    def get(self, full_name: str) -> Optional[str]:
        return self._to_alias.get(full_name.lower().strip())

    def register(self, full_name: str) -> str:
        key = full_name.lower().strip()
        if key in self._to_alias:
            return self._to_alias[key]
        alias = self._make_alias(full_name)
        self._to_alias[key] = alias
        self._to_full[alias] = full_name
        self._used.add(alias.lower())
        return alias

    def _make_alias(self, name: str) -> str:
        words = name.split()
        # Single word: first 2-3 uppercase chars
        if len(words) == 1:
            for n in (2, 3, 4):
                c = name[:n].upper()
                if c.lower() not in self._used:
                    return c
            return name[:5].upper()
        # Multi-word: initials
        initials = "".join(
            w[0] for w in words if w and w[0].isalpha()
        ).upper()
        if len(initials) >= 2 and initials.lower() not in self._used:
            return initials[:3]
        # Fallback: first word abbreviated
        for n in (3, 4, 5):
            c = words[0][:n].upper()
            if c.lower() not in self._used:
                return c
        return words[0][:4].upper()

    def has_aliases(self) -> bool:
        return len(self._to_alias) > 0

    def ontology_string(self) -> str:
        """Produce ontology definition string for manifest."""
        parts = []
        for alias, full in sorted(self._to_full.items()):
            parts.append(f"{alias}={full}")
        return "+".join(parts)


def _build_entity_registry(doc) -> EntityRegistry:
    """Scan entire document and register all named entities."""
    reg = EntityRegistry()
    for ent in doc.ents:
        if ent.label_ in (
            "PERSON", "ORG", "GPE", "PRODUCT",
            "WORK_OF_ART", "FAC", "NORP",
        ):
            name = ent.text.strip()
            if len(name) > 2:
                reg.register(name)
    return reg


# -- spaCy singleton ---------------------------------------------------------

_nlp = None


def _get_nlp():
    global _nlp
    if _nlp is None:
        _nlp = spacy.load("en_core_web_sm")
    return _nlp


# -- text normalization helpers ---------------------------------------------


def _truncate_word(s: str, max_len: int) -> str:
    """Truncate at an underscore boundary where possible."""
    if len(s) <= max_len:
        return s
    truncated = s[:max_len]
    last_sep = truncated.rfind("_")
    if last_sep > max_len // 2:
        return truncated[:last_sep]
    return truncated


def _clean_token_value(text: str, max_len: int = 40, keep: str = ".%:+-") -> str:
    """Normalize text to an AXL-safe token-ish value."""
    pattern = rf"[^\w{re.escape(keep)}]+"
    text = re.sub(pattern, "_", text.strip())
    text = re.sub(r"_+", "_", text).strip("_")
    return _truncate_word(text, max_len)


def _strip_trailing_zero(num: float) -> str:
    s = f"{num:.1f}"
    if s.endswith(".0"):
        return s[:-2]
    return s


def _human_scale(num: float) -> str:
    if num >= 1_000_000_000:
        return f"{_strip_trailing_zero(num / 1_000_000_000)}B"
    if num >= 1_000_000:
        return f"{_strip_trailing_zero(num / 1_000_000)}M"
    if num >= 1_000:
        return f"{_strip_trailing_zero(num / 1_000)}K"
    return _strip_trailing_zero(num)


def _looks_like_year(raw: str) -> bool:
    raw = raw.strip()
    return bool(re.fullmatch(r"(?:18|19|20|21)\d{2}", raw))


_SCALE_SUFFIX = {
    "thousand": "K",
    "k": "K",
    "million": "M",
    "m": "M",
    "billion": "B",
    "b": "B",
    "trillion": "T",
    "t": "T",
}


def _normalize_scaled_phrase(text: str) -> Optional[str]:
    m = re.search(
        r"([-+]?\d[\d,]*(?:\.\d+)?)\s*(thousand|million|billion|trillion|k|m|b|t)\b",
        text,
        re.IGNORECASE,
    )
    if not m:
        return None
    num = float(m.group(1).replace(",", ""))
    suffix = _SCALE_SUFFIX[m.group(2).lower()]
    return f"{_strip_trailing_zero(num)}{suffix}"


def normalize_entity_value(raw: str, ent_label: str) -> Optional[str]:
    """Normalize an extracted entity without destroying dates or scale words."""
    text = raw.strip()
    if not text:
        return None

    # DATE/TIME: never compact years. Preserve quarter/year structures.
    if ent_label in ("DATE", "TIME"):
        q = re.search(r"\b(Q[1-4])\s+(20\d{2})\b", text, re.IGNORECASE)
        if q:
            return f"{q.group(1).upper()}_{q.group(2)}"
        year = re.search(r"\b((?:18|19|20|21)\d{2})\b", text)
        if year:
            return year.group(1)
        return _clean_token_value(text, max_len=24, keep=".-")

    # Percents: preserve the percent sign if present.
    if ent_label == "PERCENT":
        m = re.search(r"([-+]?\d[\d,]*(?:\.\d+)?)\s*%", text)
        if m:
            return f"{m.group(1).replace(',', '')}%"
        scaled = _normalize_scaled_phrase(text)
        if scaled:
            return scaled
        return _clean_token_value(text.replace(",", ""), max_len=18, keep=".%+-")

    # Monetary phrases: support word scales and currency words/symbols.
    if ent_label == "MONEY":
        scaled = _normalize_scaled_phrase(text)
        if scaled:
            return scaled
        numeric = re.search(r"([-+]?\d[\d,]*(?:\.\d+)?)", text)
        if numeric:
            value = float(numeric.group(1).replace(",", ""))
            return _human_scale(value)
        return _clean_token_value(text, max_len=20)

    # Generic cardinals/quantities: avoid compacting likely years.
    scaled = _normalize_scaled_phrase(text)
    if scaled:
        return scaled

    numeric_only = re.sub(r"[^\d.+-]", "", text)
    if numeric_only:
        if _looks_like_year(numeric_only):
            return numeric_only
        try:
            value = float(numeric_only)
            return _human_scale(value)
        except ValueError:
            pass

    return _clean_token_value(text, max_len=20, keep=".%+-")


# -- Tag classification ------------------------------------------------------

_FINANCIAL_PATTERNS = re.compile(
    r"\$|USD|USDC|BTC|ETH|SOL|price|cost|revenue|budget|fee|fund|rate|"
    r"profit|loss|margin|earnings|valuation|salary|payment|invoice|debt|"
    r"credit|debit|stock|equity|bond|yield|dividend|interest|inflation",
    re.IGNORECASE,
)
_ENTITY_PATTERNS = re.compile(
    r"patient|doctor|agent|team|company|org|user|client|server|system|"
    r"person|department|hospital|university|platform|service|api|database|"
    r"marketing|engineering|sales|finance|operations|hr|legal",
    re.IGNORECASE,
)
_METRIC_PATTERNS = re.compile(
    r"%|percent|ratio|score|rate|count|total|average|mean|median|"
    r"index|level|volume|size|length|height|weight|temperature|"
    r"latency|throughput|bandwidth|accuracy|precision|recall|f1|target|"
    r"feature|campaign|employee|order|users?",
    re.IGNORECASE,
)
_EVENT_PATTERNS = re.compile(
    r"launch|release|deploy|publish|announce|discover|detect|trigger|"
    r"alert|incident|outage|breach|update|merge|commit|approve|reject|"
    r"start|stop|begin|end|occur|happen|complete|fail|succeed",
    re.IGNORECASE,
)
_STATE_PATTERNS = re.compile(
    r"bullish|bearish|stable|volatile|active|inactive|pending|resolved|"
    r"healthy|critical|warning|normal|abnormal|positive|negative|neutral|"
    r"increasing|decreasing|improving|degrading|growing|shrinking|probable|"
    r"possible|likely|unlikely|confirmed|suspected|uncertain",
    re.IGNORECASE,
)


NER_TO_VALUE_PREFIX = {
    "MONEY": "amt",
    "PERCENT": "pct",
    "CARDINAL": "count",
    "QUANTITY": "qty",
    "DATE": "date",
    "TIME": "date",
}


def classify_tag(text: str, ent_label: str = "") -> tuple[TagType, str]:
    """Classify text into an AXL tag type.

    Important change from v0.7.0: PERCENT is treated as a metric, not as a
    financial subject by default.
    """
    if ent_label == "MONEY":
        return TagType.FINANCIAL, text
    if ent_label == "PERCENT":
        return TagType.METRIC, text
    if ent_label in ("PERSON", "ORG", "GPE", "NORP", "FAC", "PRODUCT"):
        return TagType.ENTITY, text
    if ent_label in ("QUANTITY", "CARDINAL", "ORDINAL"):
        return TagType.METRIC, text
    if ent_label in ("EVENT",):
        return TagType.EVENT, text
    if ent_label in ("DATE", "TIME"):
        return TagType.VALUE, text

    if _FINANCIAL_PATTERNS.search(text):
        return TagType.FINANCIAL, text
    if _ENTITY_PATTERNS.search(text):
        return TagType.ENTITY, text
    if _METRIC_PATTERNS.search(text):
        return TagType.METRIC, text
    if _EVENT_PATTERNS.search(text):
        return TagType.EVENT, text
    if _STATE_PATTERNS.search(text):
        return TagType.STATE, text
    return TagType.VALUE, text


# -- Operation classification ------------------------------------------------

_INF_PATTERNS = re.compile(
    r"\b(therefore|thus|hence|consequently|implies?|suggests?|indicates?|"
    r"conclud|infer|mean|because|result|caus|lead|determin|analys|assess|"
    r"evaluat|estimat|calculat|deriv|based on|according to)\b",
    re.IGNORECASE,
)
_CON_PATTERNS = re.compile(
    r"\b(however|but|although|despite|disagree|contradict|challenge|"
    r"dispute|incorrect|wrong|false|reject|deny|counter|unlike|"
    r"on the other hand|in contrast|nevertheless|alternatively)\b",
    re.IGNORECASE,
)
_MRG_PATTERNS = re.compile(
    r"\b(overall|together|combined|synthesiz|integrat|both|all|"
    r"in summary|in conclusion|to summarize|taken together|"
    r"consensus|agree|align|converge|reconcil)\b",
    re.IGNORECASE,
)
_SEK_PATTERNS = re.compile(
    r"\b(need|require|request|ask|seek|want|looking for|searching|"
    r"where|how|what|when|who|which|please provide|can you|"
    r"unknown|unclear|missing|investigate|determine)\b",
    re.IGNORECASE,
)
_YLD_PATTERNS = re.compile(
    r"\b(changed? my mind|revised?|updated?|previously|was wrong|"
    r"now (believe|think)|correction|retract|amend|pivot|shift|"
    r"no longer|instead|originally|formerly)\b",
    re.IGNORECASE,
)
_PRD_PATTERNS = re.compile(
    r"\b(predict|forecast|expect|anticipat|project|will|would|"
    r"likely to|probably|estimated to|by (next|end|Q[1-4]|20\d\d)|"
    r"in the (next|coming)|future|outlook|prognosis|trajectory)\b",
    re.IGNORECASE,
)


def classify_operation(text: str) -> Operation:
    scores = {
        Operation.INF: len(_INF_PATTERNS.findall(text)),
        Operation.CON: len(_CON_PATTERNS.findall(text)) * 1.5,
        Operation.MRG: len(_MRG_PATTERNS.findall(text)),
        Operation.SEK: len(_SEK_PATTERNS.findall(text)),
        Operation.YLD: len(_YLD_PATTERNS.findall(text)) * 2,
        Operation.PRD: len(_PRD_PATTERNS.findall(text)),
    }
    best = max(scores, key=scores.get)
    if scores[best] > 0:
        return best
    return Operation.OBS


# -- Confidence --------------------------------------------------------------


def score_confidence(
    text: str,
    operation: Operation = Operation.OBS,
    has_numbers: bool = False,
    has_entities: bool = False,
) -> int:
    base = 75
    if operation == Operation.OBS:
        base = 90 if has_numbers else (85 if has_entities else 80)
    elif operation == Operation.INF:
        base = 80 if has_numbers else 70
    elif operation == Operation.CON:
        base = 80
    elif operation == Operation.MRG:
        base = 78
    elif operation == Operation.SEK:
        return 90
    elif operation == Operation.YLD:
        base = 82
    elif operation == Operation.PRD:
        base = 70

    hedging = {
        "approximately": -5,
        "estimated": -5,
        "roughly": -8,
        "about": -3,
        "around": -3,
        "nearly": -3,
        "possibly": -15,
        "perhaps": -15,
        "might": -12,
        "may": -10,
        "could": -8,
        "uncertain": -15,
        "unclear": -12,
        "likely": +3,
        "probably": +2,
        "expected": +3,
        "confirmed": +5,
        "verified": +5,
        "proven": +5,
        "definitely": +8,
        "certainly": +8,
        "clearly": +5,
        "reported": +0,
        "stated": +0,
        "claimed": -3,
        "will": +5,
        "shall": +5,
    }

    text_lower = text.lower()
    adjustment = 0
    for word, offset in hedging.items():
        if word in text_lower:
            adjustment += offset

    return max(10, min(99, base + adjustment))


# -- Temporal ----------------------------------------------------------------

_TEMPORAL_MAP = {
    r"\bnow\b|\bcurrently\b|\btoday\b|\bpresent\b|\bright now\b": "NOW",
    r"\b(next|coming)\s+hour\b|\b1\s*h\b|\bhourly\b": "1H",
    r"\b(next|coming)\s+4\s*hours?\b|\b4\s*h\b": "4H",
    r"\b(tomorrow|next day|1\s*d|daily)\b": "1D",
    r"\b(next|this|coming)\s+week\b|\b1\s*w\b|\bweekly\b": "1W",
    r"\b(next|this|coming)\s+month\b|\b1\s*m\b|\bmonthly\b": "1M",
    r"\b(historical|past|previous|last|ago|formerly)\b": "HIST",
}


def extract_temporal(text: str) -> str:
    for pattern, temporal in _TEMPORAL_MAP.items():
        if re.search(pattern, text, re.IGNORECASE):
            return temporal
    return "NOW"


# -- Evidence ----------------------------------------------------------------

_CAUSAL_MARKERS = {"because", "since", "as"}
_ATTRIBUTION_MARKERS = {"according", "reported", "per"}
_PREP_CAUSAL_HEADS = {"due", "based", "driven", "caused"}


def extract_evidence(text: str, doc=None) -> Optional[str]:
    """Extract evidence/cause from text.

    Important fix from v0.7.0:
    dependency fallback now ignores generic root-level prepositions such as
    "by 2025" and "by 30%" so temporal/location phrases do not become fake
    causal evidence.
    """
    patterns = [
        (r"\b(?:because|since|as)\b\s+(.+?)(?:\.|,|$)", "<-"),
        (r"\b(?:based on|due to|driven by|caused by)\b\s+(.+?)(?:\.|,|$)", "<-"),
        (r"\b(?:according to|reported by|per)\b\s+(.+?)(?:\.|,|$)", "<-@"),
        (r"\b(?:disagrees? with|contradicts?|challenges?)\b\s+(.+?)(?:\.|,|$)", "RE:"),
    ]

    for pattern, prefix in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            evidence = match.group(1).strip()[:80]
            evidence = _compress_evidence_text(evidence)
            if evidence:
                return f"{prefix}{evidence}"

    if not doc:
        return None

    for token in doc:
        if token.dep_ == "advcl":
            marks = {
                child.lemma_.lower()
                for child in token.children
                if child.dep_ == "mark"
            }
            if marks & _CAUSAL_MARKERS:
                subtree = " ".join(t.text for t in token.subtree)
                compressed = _compress_evidence_text(subtree)
                if compressed and len(compressed) > 3:
                    return f"<-{compressed}"

        if (token.dep_ == "prep"
                and token.lemma_.lower() in _PREP_CAUSAL_HEADS):
            subtree = " ".join(t.text for t in token.subtree)
            compressed = _compress_evidence_text(subtree)
            if compressed and len(compressed) > 3:
                return f"<-{compressed}"

    return None


def _compress_evidence_text(text: str) -> str:
    """Compress a causal clause to abbreviated form, max 30 chars."""
    text = re.sub(r"[^\w\s.+-]", "", text).strip()
    words = text.split()
    if not words:
        return ""
    # Abbreviate each word, skip stopwords
    stops = {
        "the", "a", "an", "of", "in", "to", "for", "and",
        "or", "is", "was", "were", "are", "by", "with",
        "from", "into", "that", "this", "its", "their",
    }
    parts = []
    for w in words:
        if w.lower() in stops:
            continue
        parts.append(_abbr(w, 8))
    result = "_".join(parts)
    return _truncate_word(result, 28)


# -- Subject extraction ------------------------------------------------------

_PRONOUNS = {
    "i",
    "you",
    "we",
    "they",
    "he",
    "she",
    "it",
    "this",
    "that",
    "these",
    "those",
    "someone",
    "somebody",
    "something",
    "anything",
    "everything",
}

_WEAK_SUBJECTS = {
    "thing",
    "stuff",
    "situation",
    "issue",
    "matter",
    "problem",
    "case",
    "item",
    "something",
    "anything",
    "everything",
}

_REQUEST_LEMMAS = {
    "need",
    "want",
    "seek",
    "request",
    "require",
    "ask",
    "know",
    "understand",
    "learn",
    "investigate",
    "determine",
}

_ROLE_STOPWORDS = {
    "dollar",
    "dollars",
    "usd",
    "percent",
    "percentage",
    "year",
    "month",
    "quarter",
    "date",
    "time",
    "team",
    "company",
    "system",
    "organization",
    "org",
}


def _is_pronoun_like(text: str) -> bool:
    stripped = text.strip().lower()
    return stripped in _PRONOUNS or bool(
        re.fullmatch(r"(?:i|you|we|they|he|she|it|this|that)", stripped)
    )


def _is_weak_subject(text: str) -> bool:
    stripped = text.strip().lower()
    return stripped in _WEAK_SUBJECTS


def _score_entity_candidate(ent) -> int:
    score = 0
    if ent.label_ in ("ORG", "PERSON", "GPE", "NORP", "FAC", "PRODUCT"):
        score += 110
    elif ent.label_ in ("DATE", "TIME"):
        score -= 30
    elif ent.label_ in ("MONEY", "PERCENT", "CARDINAL", "QUANTITY", "ORDINAL"):
        score -= 40

    if ent.root.dep_ in ("nsubj", "nsubjpass", "attr"):
        score += 25
    if _ENTITY_PATTERNS.search(ent.text):
        score += 20
    if _is_pronoun_like(ent.text):
        score -= 200
    if _is_weak_subject(ent.text):
        score -= 25
    return score


def _score_chunk_candidate(chunk) -> int:
    score = 0
    if chunk.root.dep_ in ("nsubj", "nsubjpass", "attr"):
        score += 95
    elif chunk.root.dep_ in ("dobj", "pobj", "appos"):
        score += 40
    if any(tok.pos_ == "PROPN" for tok in chunk):
        score += 20
    if _ENTITY_PATTERNS.search(chunk.text):
        score += 25
    if any(tok.like_num for tok in chunk):
        score -= 35
    if _is_pronoun_like(chunk.text):
        score -= 200
    if _is_weak_subject(chunk.text):
        score -= 20
    return score


def _extract_seek_subject(doc) -> Optional[str]:
    """Prefer the object/complement of the request, not the pronoun requester."""
    for token in doc:
        if token.lemma_.lower() not in _REQUEST_LEMMAS:
            continue

        for child in token.children:
            if child.dep_ in ("dobj", "attr", "oprd", "pobj") and child.pos_ in ("NOUN", "PROPN"):
                span = doc[child.left_edge.i : child.right_edge.i + 1]
                if not _is_pronoun_like(span.text):
                    return span.text
            if child.dep_ in ("xcomp", "ccomp"):
                for gc in child.children:
                    if gc.dep_ in ("dobj", "attr", "pobj") and gc.pos_ in ("NOUN", "PROPN"):
                        span = doc[gc.left_edge.i : gc.right_edge.i + 1]
                        if not _is_pronoun_like(span.text):
                            return span.text
            if child.dep_ == "prep" and child.lemma_.lower() in {"about", "for", "on", "regarding"}:
                for gc in child.children:
                    if gc.dep_ == "pobj":
                        span = doc[gc.left_edge.i : gc.right_edge.i + 1]
                        if not _is_pronoun_like(span.text):
                            return span.text

    for chunk in doc.noun_chunks:
        if chunk.root.dep_ in ("dobj", "pobj", "attr") and not _is_pronoun_like(chunk.text):
            return chunk.text
    return None


def extract_subject(
    doc,
    sent_text: str,
    operation: Operation = Operation.OBS,
    context_subject: Optional[tuple[TagType, str]] = None,
) -> tuple[TagType, str]:
    """Extract the best semantic subject.

    Changes from v0.7.0:
    - noun chunks are allowed to outrank numeric NER
    - pronouns are rejected as subjects
    - SEK requests prefer the requested object/complement
    - weak/numeric candidates fall back to prior context if available
    """
    if operation == Operation.SEK:
        seek_subject = _extract_seek_subject(doc)
        if seek_subject:
            tag, _ = classify_tag(seek_subject)
            clean = _clean_token_value(seek_subject, max_len=40, keep=".-")
            if clean:
                return tag, clean

    best_score = -10_000
    best: Optional[tuple[TagType, str]] = None

    # Grammatical noun chunks first.
    for chunk in doc.noun_chunks:
        score = _score_chunk_candidate(chunk)
        if score <= best_score:
            continue
        tag, _ = classify_tag(chunk.text)
        clean = _clean_token_value(chunk.text, max_len=40, keep=".-")
        if clean:
            best_score = score
            best = (tag, clean)

    # Then named entities.
    for ent in doc.ents:
        score = _score_entity_candidate(ent)
        if score <= best_score:
            continue
        tag, _ = classify_tag(ent.text, ent.label_)
        clean = _clean_token_value(ent.text, max_len=40, keep=".-")
        if clean:
            best_score = score
            best = (tag, clean)

    # Fallback tokens.
    if not best:
        for tok in doc:
            if (tok.pos_ in ("PROPN", "NOUN")
                    and not tok.like_num
                    and not _is_pronoun_like(tok.text)):
                tag, _ = classify_tag(tok.text)
                clean = _clean_token_value(tok.text, max_len=30, keep=".-")
                if clean:
                    best = (tag, clean)
                    best_score = 10
                    break

    if best and best_score >= 15:
        return best

    # Weak current subject? Carry forward prior entity context if available.
    if context_subject:
        return context_subject

    if best:
        return best
    return TagType.VALUE, "claim"


# -- Atomic value extraction -------------------------------------------------


def infer_role_label(ent, doc) -> Optional[str]:
    """Infer the semantic slot tied to a numeric entity.

    Examples:
    - 30% growth -> growth
    - 5 million in revenue -> revenue
    - 200 new employees -> employees
    """
    candidates: list[tuple[int, str]] = []

    # Nearby nouns, preferring those to the right of the entity.
    start = max(0, ent.start - 2)
    end = min(len(doc), ent.end + 5)
    for tok in doc[start:end]:
        if tok.i >= ent.start and tok.i < ent.end:
            continue
        if tok.pos_ not in ("NOUN", "PROPN"):
            continue
        lemma = tok.lemma_.lower()
        if lemma in _ROLE_STOPWORDS or tok.like_num:
            continue
        distance = abs(tok.i - ent.root.i)
        score = 20 - distance
        if tok.i >= ent.end:
            score += 5
        if tok.dep_ in ("pobj", "dobj", "attr", "appos", "nsubj"):
            score += 5
        candidates.append((score, tok.text))

    head = ent.root.head
    if (head.pos_ in ("NOUN", "PROPN")
            and head.lemma_.lower() not in _ROLE_STOPWORDS
            and not head.like_num):
        candidates.append((28, head.text))

    if not candidates:
        return None

    role = max(candidates, key=lambda item: item[0])[1]
    return _clean_token_value(role, max_len=20, keep=".-").lower()


def collect_role_qualifiers(doc) -> dict[str, list[str]]:
    """Attach adjectives to their semantic role instead of taking only the first ADJ."""
    out: dict[str, list[str]] = defaultdict(list)
    for tok in doc:
        if tok.pos_ != "ADJ" or tok.dep_ not in ("amod", "acomp", "attr"):
            continue
        if tok.lemma_.lower() in {"the", "a", "an", "this", "that", "same", "other"}:
            continue
        head = tok.head
        if head.pos_ not in ("NOUN", "PROPN"):
            continue
        role = _clean_token_value(head.lemma_ or head.text, max_len=20).lower()
        if role:
            qual = _clean_token_value(tok.lemma_.lower(), max_len=16)
            out[role].append(f"~state:{qual}")
    return out


def _join_subject_role(base_subject: str, role: Optional[str]) -> str:
    if not role:
        return base_subject
    parts = {p.lower() for p in base_subject.split(".")}
    if role.lower() in parts:
        return base_subject
    return _truncate_word(f"{base_subject}.{role}", 48)


def _dedupe_preserve_order(items: Iterable[str]) -> list[str]:
    seen = set()
    out = []
    for item in items:
        if item and item not in seen:
            seen.add(item)
            out.append(item)
    return out


def extract_packed_arg2(doc, registry: Optional[EntityRegistry] = None) -> str:
    """Pack ALL values from a sentence into a single dense ARG2.

    v0.9.0 strategy: one packet per sentence, all values packed.
    Uses role labels (^rev:8.5M) instead of type labels (^amt:8.5M)
    when a semantic role is available.
    """
    qualifiers = collect_role_qualifiers(doc)
    parts: list[str] = []
    seen: set[str] = set()

    for ent in doc.ents:
        if ent.label_ not in NER_TO_VALUE_PREFIX:
            continue
        normalized = normalize_entity_value(ent.text, ent.label_)
        if not normalized:
            continue

        prefix = NER_TO_VALUE_PREFIX[ent.label_]
        role = infer_role_label(ent, doc)

        # Use role as label if available, else type prefix
        if role:
            label = _abbr(role, 8)
        else:
            label = prefix

        atom = f"^{label}:{normalized}"
        if atom not in seen:
            seen.add(atom)
            parts.append(atom)

    # Add first qualifier if budget allows
    for role, quals in qualifiers.items():
        if quals and len("+".join(parts)) < 80:
            q = quals[0]
            if q not in seen:
                parts.append(q)
            break

    if not parts:
        return ""
    return "+".join(parts[:6])


def _seek_request_arg(sent_text: str) -> str:
    text = sent_text.lower()
    if "more" in text:
        return "^need:more_info"
    if any(w in text for w in ("why", "how", "when", "where", "what", "which", "who")):
        return "^need:answer"
    return "^need:info"


def _seek_target_arg(sent_text: str) -> str:
    text = sent_text.lower()
    if any(p in text for p in ("can you", "please", "could you", "would you", "provide")):
        return "RE:operator"
    return "RE:unknown"


# -- Main pipeline -----------------------------------------------------------


def _alias_subject(
    tag: TagType, value: str, registry: EntityRegistry,
) -> str:
    """Compress a subject using entity aliases.

    Only registered entities get aliased. Non-entity subjects
    keep their original text (cleaned and truncated) so the
    decompressor can produce readable section headers.
    """
    full_text = value.replace("_", " ")

    # Exact match: registered entity -> short alias
    alias = registry.get(full_text)
    if alias:
        return alias

    # Partial match: subject contains a registered entity
    words = full_text.split()
    for w in words:
        a = registry.get(w)
        if a:
            remaining = [
                x for x in words if x.lower() != w.lower()
            ]
            if remaining:
                role = "_".join(remaining)[:12]
                return f"{a}.{role}"
            return a

    # No entity match: keep original, just truncate
    return _truncate_word(value, 30)


def _merge_same_subject_packets(
    packets: list[V3Packet],
) -> list[V3Packet]:
    """Merge adjacent packets with same subject+operation+temporal."""
    if len(packets) <= 1:
        return packets

    merged: list[V3Packet] = []
    for pkt in packets:
        if not merged:
            merged.append(pkt)
            continue

        prev = merged[-1]
        same_subj = (
            prev.subject_tag == pkt.subject_tag
            and prev.subject_value == pkt.subject_value
        )
        same_op = prev.operation == pkt.operation
        same_temp = prev.temporal == pkt.temporal
        prev_arg2_len = len(prev.arg2 or "")

        if same_subj and same_op and same_temp and prev_arg2_len < 90:
            # Merge ARG2
            if pkt.arg2:
                if prev.arg2:
                    combined = f"{prev.arg2}+{pkt.arg2}"
                    if len(combined) <= 100:
                        merged[-1] = V3Packet(
                            id=prev.id,
                            operation=prev.operation,
                            confidence=max(prev.confidence, pkt.confidence),
                            subject_tag=prev.subject_tag,
                            subject_value=prev.subject_value,
                            arg1=prev.arg1 or pkt.arg1,
                            arg2=combined,
                            temporal=prev.temporal,
                        )
                        continue
                else:
                    merged[-1] = V3Packet(
                        id=prev.id,
                        operation=prev.operation,
                        confidence=max(prev.confidence, pkt.confidence),
                        subject_tag=prev.subject_tag,
                        subject_value=prev.subject_value,
                        arg1=prev.arg1 or pkt.arg1,
                        arg2=pkt.arg2,
                        temporal=prev.temporal,
                    )
                    continue

        merged.append(pkt)

    return merged


def english_to_v3(
    text: str, agent_id: str = "C",
) -> list[V3Packet]:
    """Two-pass compression: registry scan then packed emission."""
    nlp = _get_nlp()
    doc = nlp(text)

    # PASS 1: Build entity registry from full document
    registry = _build_entity_registry(doc)

    # PASS 2: Extract and emit packed packets
    packets: list[V3Packet] = []
    ctx_subj: Optional[tuple[TagType, str]] = None

    for sent in doc.sents:
        sent_text = sent.text.strip()
        if len(sent_text) < 5:
            continue

        sent_doc = nlp(sent_text)
        operation = classify_operation(sent_text)

        has_nums = bool(
            sent_doc.ents
            and any(
                e.label_ in (
                    "MONEY", "QUANTITY", "CARDINAL",
                    "PERCENT", "DATE",
                )
                for e in sent_doc.ents
            )
        )
        has_ents = bool(
            sent_doc.ents
            and any(
                e.label_ in ("PERSON", "ORG", "GPE")
                for e in sent_doc.ents
            )
        )
        confidence = score_confidence(
            sent_text, operation, has_nums, has_ents,
        )

        tag_type, raw_subject = extract_subject(
            sent_doc, sent_text, operation, ctx_subj,
        )
        if tag_type == TagType.ENTITY:
            ctx_subj = (tag_type, raw_subject)

        # Compress subject using entity aliases
        subject_value = _alias_subject(tag_type, raw_subject, registry)

        temporal = extract_temporal(sent_text)
        evidence = extract_evidence(sent_text, sent_doc)

        if operation == Operation.SEK:
            packets.append(V3Packet(
                id=agent_id,
                operation=operation,
                confidence=confidence,
                subject_tag=tag_type,
                subject_value=subject_value,
                arg1=_seek_target_arg(sent_text),
                arg2=_seek_request_arg(sent_text),
                temporal=temporal,
            ))
            continue

        # Pack ALL values from sentence into one ARG2
        arg2 = extract_packed_arg2(sent_doc, registry)

        packets.append(V3Packet(
            id=agent_id,
            operation=operation,
            confidence=confidence,
            subject_tag=tag_type,
            subject_value=subject_value,
            arg1=evidence,
            arg2=arg2 or None,
            temporal=temporal,
        ))

    # PASS 3: Merge adjacent same-subject packets
    packets = _merge_same_subject_packets(packets)

    # PASS 4: Add manifests
    # Ontology manifest with entity registry
    if registry.has_aliases():
        onto_str = registry.ontology_string()
        if len(onto_str) <= 800:
            onto = V3Packet(
                id="axl-core",
                operation=Operation.OBS,
                confidence=99,
                subject_tag=TagType.ENTITY,
                subject_value="m.O.doc",
                arg1=None,
                arg2=f"^df:{onto_str}",
                temporal="NOW",
            )
            packets.insert(0, onto)

    # Bundle manifest
    if packets:
        has_entities = any(
            p.subject_tag == TagType.ENTITY for p in packets
        )
        has_numbers = any(
            p.arg2 and "^" in (p.arg2 or "") for p in packets
        )
        has_causality = any(
            p.arg1
            and ("<-" in (p.arg1 or "") or "RE:" in (p.arg1 or ""))
            for p in packets
        )
        has_temporal = any(
            p.temporal != "NOW"
            or (p.arg2 and "^date:" in p.arg2)
            for p in packets
        )

        fidelity = sum([
            20 if has_entities else 0,
            20 if has_numbers else 0,
            20 if has_causality else 0,
            20,  # confidence always present
            20 if has_temporal else 0,
        ])

        mode = "qa" if (
            has_entities and has_numbers and has_temporal
        ) else "gist"
        keep = _dedupe_preserve_order([
            "confidence",
            *(["entities"] if has_entities else []),
            *(["numbers"] if has_numbers else []),
            *(["causality"] if has_causality else []),
            *(["temporal"] if has_temporal else []),
        ])

        manifest = V3Packet(
            id="axl-core",
            operation=Operation.OBS,
            confidence=99,
            subject_tag=TagType.ENTITY,
            subject_value="m.B.compress",
            arg1=(
                f'^mode:{mode}'
                f'+^keep:{"+".join(keep)}'
                '+^src:input'
            ),
            arg2=(
                '^loss:rhetoric+formatting+redundancy'
                '+hedging+style'
                f'+^f:{fidelity}+^fm:axl/v0.9'
            ),
            temporal="NOW",
        )
        packets.append(manifest)

    return packets


# -- Rosetta kernel cache ----------------------------------------------------

_KERNEL_CACHE: dict[str, Optional[str]] = {"full": None}

_MINI_KERNEL = (
    "DIRECTIVE: Reply in AXL v3 unless asked to decompress.\n"
    "PKT:=ID|OP.CC|SUBJ|ARG1|ARG2|TEMP [META]\n"
    "OP:=OBS|INF|CON|MRG|SEK|YLD|PRD ; CC:=00-99\n"
    "SUBJ:=TAG.value ; TAG:$ @ # ! ~ ^\n"
    "ARG1:=RE:id|<-evidence ; ARG2:=evidence|direction\n"
    "TEMP:=NOW|1H|4H|1D|1W|1M|HIST\n"
    "Bundles:^mode ^keep ^f ^fm ^src else gist.\n"
    "Decompress: claim per pkt, group by subject.\n"
    "Spec: https://axlprotocol.org/v3"
)


def _load_kernel(full: bool = False) -> str:
    if not full:
        return _MINI_KERNEL
    if _KERNEL_CACHE["full"]:
        return _KERNEL_CACHE["full"]
    import os

    local_paths = [
        "/var/www/axlprotocol/v3",
        os.path.join(
            os.path.dirname(__file__), "..", "..", "rosetta", "v3.md",
        ),
    ]
    for path in local_paths:
        try:
            with open(path) as f:
                _KERNEL_CACHE["full"] = f.read()
                return _KERNEL_CACHE["full"]
        except (FileNotFoundError, PermissionError):
            continue
    try:
        import urllib.request
        with urllib.request.urlopen(
            "https://axlprotocol.org/v3", timeout=5,
        ) as resp:
            _KERNEL_CACHE["full"] = resp.read().decode("utf-8")
            return _KERNEL_CACHE["full"]
    except Exception:
        return ""


def compress(
    text: str,
    agent_id: str = "C",
    include_kernel: bool = True,
    kernel_mode: str = "mini",
) -> str:
    """Compress English to self-bootstrapping AXL v3 output."""
    packets = english_to_v3(text, agent_id)
    packet_lines = "\n".join(emit_v3(p) for p in packets)

    if include_kernel:
        use_full = kernel_mode == "full"
        kernel = _load_kernel(full=use_full)
        if kernel:
            if use_full:
                directive = (
                    "DIRECTIVE: Parse the grammar below. "
                    "Reply in AXL v3 only.\n\n"
                )
                return (
                    directive + kernel
                    + "\n\n---PACKETS---\n" + packet_lines
                )
            return kernel + "\n\n---PACKETS---\n" + packet_lines
    return packet_lines

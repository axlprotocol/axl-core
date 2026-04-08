"""AXL Compressor: Deterministic English-to-AXL v3 pipeline.

No LLM dependency. Uses spaCy NER + Rosetta grammar rules.

Pipeline:
1. Sentence splitting
2. Entity extraction (NER -> tag types)
3. Operation classification (OBS/INF/CON/MRG/SEK/YLD/PRD)
4. Confidence scoring
5. Temporal extraction
6. Evidence linking
7. Packet assembly
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

import spacy

from axl.models import Operation, TagType, V3Packet
from axl.emitter import emit_v3

# Load spaCy model (lazy, singleton)
_nlp = None

def _get_nlp():
    global _nlp
    if _nlp is None:
        _nlp = spacy.load("en_core_web_sm")
    return _nlp


# ── Tag classification ────────────────────────────────

# Patterns for tag type detection
_FINANCIAL_PATTERNS = re.compile(
    r'\$|USD|USDC|BTC|ETH|SOL|price|cost|revenue|budget|fee|fund|rate|'
    r'profit|loss|margin|earnings|valuation|salary|payment|invoice|debt|'
    r'credit|debit|stock|equity|bond|yield|dividend|interest|inflation',
    re.IGNORECASE
)
_ENTITY_PATTERNS = re.compile(
    r'patient|doctor|agent|team|company|org|user|client|server|system|'
    r'person|department|hospital|university|platform|service|API|database',
    re.IGNORECASE
)
_METRIC_PATTERNS = re.compile(
    r'%|percent|ratio|score|rate|count|total|average|mean|median|'
    r'index|level|volume|size|length|height|weight|temperature|'
    r'latency|throughput|bandwidth|accuracy|precision|recall|f1',
    re.IGNORECASE
)
_EVENT_PATTERNS = re.compile(
    r'launch|release|deploy|publish|announce|discover|detect|trigger|'
    r'alert|incident|outage|breach|update|merge|commit|approve|reject|'
    r'start|stop|begin|end|occur|happen|complete|fail|succeed',
    re.IGNORECASE
)
_STATE_PATTERNS = re.compile(
    r'bullish|bearish|stable|volatile|active|inactive|pending|resolved|'
    r'healthy|critical|warning|normal|abnormal|positive|negative|neutral|'
    r'increasing|decreasing|improving|degrading|growing|shrinking|probable|'
    r'possible|likely|unlikely|confirmed|suspected|uncertain',
    re.IGNORECASE
)


def classify_tag(text: str, ent_label: str = "") -> tuple[TagType, str]:
    """Classify text into a tag type and extract the value."""
    # NER label hints
    if ent_label in ("MONEY", "PERCENT"):
        return TagType.FINANCIAL, text
    if ent_label in ("PERSON", "ORG", "GPE", "NORP", "FAC"):
        return TagType.ENTITY, text
    if ent_label in ("QUANTITY", "CARDINAL", "ORDINAL"):
        return TagType.METRIC, text
    if ent_label in ("EVENT",):
        return TagType.EVENT, text
    if ent_label in ("DATE", "TIME"):
        return TagType.VALUE, text

    # Pattern matching
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

    # Default: value
    return TagType.VALUE, text


# ── Operation classification ──────────────────────────

_INF_PATTERNS = re.compile(
    r'\b(therefore|thus|hence|consequently|implies?|suggests?|indicates?|'
    r'conclud|infer|mean|because|result|caus|lead|determin|analys|assess|'
    r'evaluat|estimat|calculat|deriv|based on|according to)\b',
    re.IGNORECASE
)
_CON_PATTERNS = re.compile(
    r'\b(however|but|although|despite|disagree|contradict|challenge|'
    r'dispute|incorrect|wrong|false|reject|deny|counter|unlike|'
    r'on the other hand|in contrast|nevertheless|alternatively)\b',
    re.IGNORECASE
)
_MRG_PATTERNS = re.compile(
    r'\b(overall|together|combined|synthesiz|integrat|both|all|'
    r'in summary|in conclusion|to summarize|taken together|'
    r'consensus|agree|align|converge|reconcil)\b',
    re.IGNORECASE
)
_SEK_PATTERNS = re.compile(
    r'\b(need|require|request|ask|seek|want|looking for|searching|'
    r'where|how|what|when|who|which|please provide|can you|'
    r'unknown|unclear|missing|investigate|determine)\b',
    re.IGNORECASE
)
_YLD_PATTERNS = re.compile(
    r'\b(changed? my mind|revised?|updated?|previously|was wrong|'
    r'now (believe|think)|correction|retract|amend|pivot|shift|'
    r'no longer|instead|originally|formerly)\b',
    re.IGNORECASE
)
_PRD_PATTERNS = re.compile(
    r'\b(predict|forecast|expect|anticipat|project|will|would|'
    r'likely to|probably|estimated to|by (next|end|Q[1-4]|20\d\d)|'
    r'in the (next|coming)|future|outlook|prognosis|trajectory)\b',
    re.IGNORECASE
)


def classify_operation(text: str) -> Operation:
    """Classify a sentence into an AXL operation."""
    # Score each operation
    scores = {
        Operation.INF: len(_INF_PATTERNS.findall(text)),
        Operation.CON: len(_CON_PATTERNS.findall(text)) * 1.5,  # boost contradictions
        Operation.MRG: len(_MRG_PATTERNS.findall(text)),
        Operation.SEK: len(_SEK_PATTERNS.findall(text)),
        Operation.YLD: len(_YLD_PATTERNS.findall(text)) * 2,  # boost yield (rare)
        Operation.PRD: len(_PRD_PATTERNS.findall(text)),
    }

    best = max(scores, key=scores.get)
    if scores[best] > 0:
        return best
    return Operation.OBS  # Default: observation


# ── Confidence scoring ────────────────────────────────

_HIGH_CONFIDENCE = re.compile(
    r'\b(definitely|certainly|confirmed|proven|verified|always|'
    r'clearly|obviously|undoubtedly|measured|recorded|is|are|was|were)\b',
    re.IGNORECASE
)
_MED_CONFIDENCE = re.compile(
    r'\b(likely|probably|suggests|appears|seems|indicates|generally|'
    r'typically|often|usually|tends|expected)\b',
    re.IGNORECASE
)
_LOW_CONFIDENCE = re.compile(
    r'\b(possibly|perhaps|might|may|could|uncertain|unclear|'
    r'speculative|estimated|approximate|roughly|debatable|questionable)\b',
    re.IGNORECASE
)


def score_confidence(text: str) -> int:
    """Score confidence 0-99 based on hedging language."""
    high = len(_HIGH_CONFIDENCE.findall(text))
    med = len(_MED_CONFIDENCE.findall(text))
    low = len(_LOW_CONFIDENCE.findall(text))

    if low > 0 and high == 0:
        return max(25, min(55, 40 + high * 5 - low * 10))
    if med > 0 and high == 0:
        return max(55, min(80, 70 + high * 3 - med * 5))
    if high > 0:
        return max(80, min(99, 90 + high * 3 - low * 5 - med * 2))
    return 75  # Default: moderate confidence


# ── Temporal extraction ───────────────────────────────

_TEMPORAL_MAP = {
    r'\bnow\b|\bcurrently\b|\btoday\b|\bpresent\b|\bright now\b': "NOW",
    r'\b(next|coming)\s+hour\b|\b1\s*h\b|\bhourly\b': "1H",
    r'\b(next|coming)\s+4\s*hours?\b|\b4\s*h\b': "4H",
    r'\b(tomorrow|next day|1\s*d|daily)\b': "1D",
    r'\b(next|this|coming)\s+week\b|\b1\s*w\b|\bweekly\b': "1W",
    r'\b(next|this|coming)\s+month\b|\b1\s*m\b|\bmonthly\b': "1M",
    r'\b(historical|past|previous|last|ago|formerly)\b': "HIST",
}


def extract_temporal(text: str) -> str:
    """Extract temporal scope from text."""
    for pattern, temporal in _TEMPORAL_MAP.items():
        if re.search(pattern, text, re.IGNORECASE):
            return temporal
    return "NOW"  # Default


# ── Evidence extraction ───────────────────────────────

_EVIDENCE_PATTERNS = re.compile(
    r'\b(?:because|based on|due to|from|according to|given|considering|'
    r'as shown by|evidenced by|supported by|driven by|caused by)\b\s+(.+?)(?:\.|,|$)',
    re.IGNORECASE
)


def extract_evidence(text: str) -> Optional[str]:
    """Extract evidence/cause from text."""
    match = _EVIDENCE_PATTERNS.search(text)
    if match:
        evidence = match.group(1).strip()[:60]  # Cap length
        # Clean and format as AXL evidence
        evidence = re.sub(r'[^\w\s.+-]', '', evidence).strip()
        evidence = evidence.replace(' ', '_')[:40]
        return f"<-{evidence}"
    return None


# ── Subject extraction ────────────────────────────────

def extract_subject(doc, sent_text: str) -> tuple[TagType, str]:
    """Extract the primary subject from a sentence using NER and noun chunks."""
    # Priority 1: NER entities (most semantically meaningful)
    best_ent = None
    for ent in doc.ents:
        # Prefer PERSON, ORG, MONEY, PRODUCT over generic labels
        if ent.label_ in ("PERSON", "ORG", "GPE", "PRODUCT", "WORK_OF_ART"):
            best_ent = ent
            break
        if ent.label_ in ("MONEY", "QUANTITY", "PERCENT") and not best_ent:
            best_ent = ent
        if not best_ent:
            best_ent = ent

    if best_ent:
        tag, val = classify_tag(best_ent.text, best_ent.label_)
        clean = re.sub(r'[^\w.%-]', '_', val).strip('_')[:30]
        if clean:
            return tag, clean

    # Priority 2: Subject noun chunk (the grammatical subject)
    for chunk in doc.noun_chunks:
        if chunk.root.dep_ in ("nsubj", "nsubjpass", "attr"):
            tag, val = classify_tag(chunk.root.text)
            clean = re.sub(r'[^\w.%-]', '_', chunk.text).strip('_')[:30]
            return tag, clean

    # Priority 3: First noun chunk
    chunks = list(doc.noun_chunks)
    if chunks:
        tag, val = classify_tag(chunks[0].text)
        clean = re.sub(r'[^\w.%-]', '_', chunks[0].text).strip('_')[:30]
        return tag, clean

    # Priority 4: First PROPN or NOUN token
    for tok in doc:
        if tok.pos_ == "PROPN":
            tag, val = classify_tag(tok.text)
            return tag, tok.text[:30]
    for tok in doc:
        if tok.pos_ == "NOUN":
            tag, val = classify_tag(tok.text)
            return tag, tok.text[:30]

    return TagType.VALUE, "claim"


# ── Main pipeline ─────────────────────────────────────

def english_to_v3(
    text: str,
    agent_id: str = "COMPRESS",
) -> list[V3Packet]:
    """Convert English prose to AXL v3 packets.

    Deterministic NLP pipeline. No LLM dependency.

    Args:
        text: English prose to compress
        agent_id: Agent ID for generated packets

    Returns:
        List of V3Packet objects
    """
    nlp = _get_nlp()
    doc = nlp(text)
    packets = []

    for sent in doc.sents:
        sent_text = sent.text.strip()
        if len(sent_text) < 5:  # Skip trivial fragments
            continue

        sent_doc = nlp(sent_text)

        # 1. Classify operation
        operation = classify_operation(sent_text)

        # 2. Score confidence
        confidence = score_confidence(sent_text)

        # 3. Extract subject
        tag_type, subject_value = extract_subject(sent_doc, sent_text)

        # 4. Extract temporal
        temporal = extract_temporal(sent_text)

        # 5. Extract evidence (ARG1)
        evidence = extract_evidence(sent_text)

        # 6. Extract additional values (ARG2)
        # Collect numbers and key values from the sentence
        values = []
        for ent in sent_doc.ents:
            if ent.label_ in ("MONEY", "QUANTITY", "CARDINAL", "PERCENT"):
                clean = re.sub(r'[^\w.%-]', '', ent.text)[:20]
                values.append(f"^{clean}")
        arg2 = "+".join(values[:3]) if values else None

        # 7. Assemble packet
        packet = V3Packet(
            id=agent_id,
            operation=operation,
            confidence=confidence,
            subject_tag=tag_type,
            subject_value=subject_value,
            arg1=evidence,
            arg2=arg2,
            temporal=temporal,
        )

        packets.append(packet)

    # If multiple packets and none is MRG, add a synthesis packet
    if len(packets) > 2:
        subjects = set()
        for p in packets:
            subjects.add(p.subject_value)
        if len(subjects) > 1 and not any(p.operation == Operation.MRG for p in packets):
            mrg = V3Packet(
                id=agent_id,
                operation=Operation.MRG,
                confidence=min(80, max(p.confidence for p in packets)),
                subject_tag=packets[0].subject_tag,
                subject_value=packets[0].subject_value,
                arg1=f"RE:{'+'.join(list(subjects)[:3])}",
                temporal="NOW",
            )
            packets.append(mrg)

    return packets


# ── Rosetta kernel cache ───────────────────────────────

_KERNEL_CACHE = {"text": None}

def _load_kernel() -> str:
    """Load and cache the Rosetta v3 kernel."""
    if _KERNEL_CACHE["text"]:
        return _KERNEL_CACHE["text"]
    # Try local file first
    import os
    local_paths = [
        "/var/www/axlprotocol/v3",
        os.path.join(os.path.dirname(__file__), "..", "..", "rosetta", "v3.md"),
    ]
    for path in local_paths:
        try:
            with open(path) as f:
                _KERNEL_CACHE["text"] = f.read()
                return _KERNEL_CACHE["text"]
        except (FileNotFoundError, PermissionError):
            continue
    # Fallback: fetch from URL
    try:
        import urllib.request
        with urllib.request.urlopen("https://axlprotocol.org/v3", timeout=5) as resp:
            _KERNEL_CACHE["text"] = resp.read().decode("utf-8")
            return _KERNEL_CACHE["text"]
    except Exception:
        return ""


def compress(text: str, agent_id: str = "COMPRESS", include_kernel: bool = True) -> str:
    """Compress English text to self-bootstrapping AXL v3 output.

    The output starts with the Rosetta v3 kernel, then the packets.
    Any LLM that receives this output can parse it immediately.

    Args:
        text: English prose
        agent_id: Agent ID
        include_kernel: If True, prepend the Rosetta v3 kernel

    Returns:
        Self-bootstrapping AXL output (kernel + packets)
    """
    packets = english_to_v3(text, agent_id)
    packet_lines = "\n".join(emit_v3(p) for p in packets)

    if include_kernel:
        kernel = _load_kernel()
        if kernel:
            return kernel + "\n\n---PACKETS---\n" + packet_lines
    return packet_lines

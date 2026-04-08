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


def _truncate_word(s: str, max_len: int) -> str:
    """Truncate string at word boundary (underscore-delimited)."""
    if len(s) <= max_len:
        return s
    truncated = s[:max_len]
    last_space = truncated.rfind('_')
    if last_space > max_len // 2:
        return truncated[:last_space]
    return truncated

from axl.models import Operation, TagType, V3Packet
from axl.emitter import emit_v3

# Load spaCy model (lazy, singleton)
_nlp = None

def _get_nlp():
    global _nlp
    if _nlp is None:
        _nlp = spacy.load("en_core_web_sm")
    return _nlp


# -- Tag classification ----------------------------------------

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


# -- Operation classification ----------------------------------

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


# -- Confidence scoring ----------------------------------------

def score_confidence(text: str, operation: Operation = Operation.OBS, has_numbers: bool = False, has_entities: bool = False) -> int:
    """Score confidence 0-99 based on content and hedging language."""
    base = 75  # default

    # Operation-based base
    if operation == Operation.OBS:
        base = 90 if has_numbers else (85 if has_entities else 80)
    elif operation == Operation.INF:
        base = 80 if has_numbers else 70
    elif operation == Operation.CON:
        base = 80
    elif operation == Operation.MRG:
        base = 78
    elif operation == Operation.SEK:
        return 90  # High confidence we need info
    elif operation == Operation.YLD:
        base = 82
    elif operation == Operation.PRD:
        base = 70

    # Hedging adjustments
    hedging = {
        'approximately': -5, 'estimated': -5, 'roughly': -8,
        'about': -3, 'around': -3, 'nearly': -3,
        'possibly': -15, 'perhaps': -15, 'might': -12, 'may': -10,
        'could': -8, 'uncertain': -15, 'unclear': -12,
        'likely': +3, 'probably': +2, 'expected': +3,
        'confirmed': +5, 'verified': +5, 'proven': +5,
        'definitely': +8, 'certainly': +8, 'clearly': +5,
        'reported': +0, 'stated': +0, 'claimed': -3,
        'will': +5, 'shall': +5,
    }

    text_lower = text.lower()
    adjustment = 0
    for word, offset in hedging.items():
        if word in text_lower:
            adjustment += offset

    return max(10, min(99, base + adjustment))


# -- Temporal extraction ---------------------------------------

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


# -- Evidence extraction ---------------------------------------

def extract_evidence(text: str, doc=None) -> Optional[str]:
    """Extract evidence/cause from text using patterns and spaCy deps."""
    # Pattern-based extraction
    patterns = [
        (r'\b(?:because|since|as)\b\s+(.+?)(?:\.|,|$)', '<-'),
        (r'\b(?:based on|due to|driven by|caused by)\b\s+(.+?)(?:\.|,|$)', '<-'),
        (r'\b(?:according to|reported by|per)\b\s+(.+?)(?:\.|,|$)', '<-@'),
        (r'\b(?:disagrees? with|contradicts?|challenges?)\b\s+(.+?)(?:\.|,|$)', 'RE:'),
    ]

    for pattern, prefix in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            evidence = match.group(1).strip()[:120]
            evidence = re.sub(r'[^\w\s.+-]', '', evidence).strip()
            evidence = _truncate_word(evidence.replace(' ', '_'), 100)
            if evidence:
                return f"{prefix}{evidence}"

    # spaCy dependency-based: find advcl or mark dependencies
    if doc:
        for token in doc:
            if token.dep_ in ('advcl', 'prep') and token.head.dep_ == 'ROOT':
                subtree = ' '.join([t.text for t in token.subtree])[:100]
                clean = _truncate_word(re.sub(r'[^\w\s]', '', subtree).strip().replace(' ', '_'), 80)
                if clean and len(clean) > 3:
                    return f"<-{clean}"

    return None


# -- Subject extraction ----------------------------------------

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
        clean = re.sub(r'[^\w.%-]', '_', val).replace('__', '_').strip('_')
        clean = _truncate_word(clean, 30)
        if clean:
            return tag, clean

    # Priority 2: Subject noun chunk (the grammatical subject)
    for chunk in doc.noun_chunks:
        if chunk.root.dep_ in ("nsubj", "nsubjpass", "attr"):
            tag, val = classify_tag(chunk.root.text)
            clean = re.sub(r'[^\w.%-]', '_', chunk.text).replace('__', '_').strip('_')
            clean = _truncate_word(clean, 30)
            return tag, clean

    # Priority 3: First noun chunk
    chunks = list(doc.noun_chunks)
    if chunks:
        tag, val = classify_tag(chunks[0].text)
        clean = re.sub(r'[^\w.%-]', '_', chunks[0].text).replace('__', '_').strip('_')
        clean = _truncate_word(clean, 30)
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


# -- Main pipeline ---------------------------------------------

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

        # 2. Score confidence (FIX 4: pass operation and content flags)
        has_nums = bool(sent_doc.ents and any(e.label_ in ('MONEY', 'QUANTITY', 'CARDINAL', 'PERCENT') for e in sent_doc.ents))
        has_ents = bool(sent_doc.ents and any(e.label_ in ('PERSON', 'ORG', 'GPE') for e in sent_doc.ents))
        confidence = score_confidence(sent_text, operation, has_nums, has_ents)

        # 3. Extract subject
        tag_type, subject_value = extract_subject(sent_doc, sent_text)

        # 4. Extract temporal
        temporal = extract_temporal(sent_text)

        # 5. Extract evidence (ARG1) - FIX 1: pass sent_doc for dep parsing
        evidence = extract_evidence(sent_text, sent_doc)

        # 6. Extract additional values (ARG2) - FIX 2: IMPROVED
        _ner_prefix_map = {
            "MONEY": "amt",
            "PERCENT": "pct",
            "CARDINAL": "count",
            "QUANTITY": "qty",
            "DATE": "date",
        }
        values = []
        for ent in sent_doc.ents:
            if ent.label_ in ("MONEY", "QUANTITY", "CARDINAL", "PERCENT", "DATE"):
                clean = ent.text.strip()
                # Normalize numbers
                clean = re.sub(r'\$\s*', '', clean)
                clean = re.sub(r',', '', clean)
                # Compact large numbers
                try:
                    num = float(re.sub(r'[^\d.]', '', clean))
                    if num >= 1_000_000_000:
                        clean = f'{num/1_000_000_000:.1f}B'
                    elif num >= 1_000_000:
                        clean = f'{num/1_000_000:.1f}M'
                    elif num >= 1_000:
                        clean = f'{num/1_000:.1f}K'
                except (ValueError, TypeError):
                    pass
                clean = re.sub(r'[^\w.%+-]', '', clean)[:20]
                if clean:
                    prefix = _ner_prefix_map.get(ent.label_, "")
                    values.append(f"^{prefix}:{clean}" if prefix else f"^{clean}")

        # Also extract qualitative states
        for token in sent_doc:
            if token.pos_ == 'ADJ' and token.dep_ in ('acomp', 'attr', 'amod'):
                if token.text.lower() not in ('the', 'a', 'an', 'this', 'that'):
                    if token.head.pos_ in ('NOUN', 'PROPN'):
                        values.append(f"~{token.head.text.lower()}:{token.text.lower()}")
                    else:
                        values.append(f"~{token.text.lower()}")
                    break  # Only first qualifier

        arg2 = "+".join(values[:4]) if values else None

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

    # FIX 3: Generate bundle manifest (loss contract)
    if packets:
        has_entities = any(p.subject_tag == TagType.ENTITY for p in packets)
        has_numbers = any(p.arg2 and '^' in (p.arg2 or '') for p in packets)
        has_causality = any(p.arg1 and ('<-' in (p.arg1 or '') or 'RE:' in (p.arg1 or '')) for p in packets)
        has_confidence = True  # Always have CC
        has_temporal = any(p.temporal != 'NOW' for p in packets)

        fidelity = 0
        if has_entities: fidelity += 20
        if has_numbers: fidelity += 20
        if has_causality: fidelity += 20
        if has_confidence: fidelity += 20
        if has_temporal: fidelity += 20

        mode = 'qa' if (has_entities and has_numbers and has_causality) else 'gist'

        keep_parts = ['entities', 'confidence']
        if has_numbers: keep_parts.append('numbers')
        if has_causality: keep_parts.append('causality')
        if has_temporal: keep_parts.append('temporal')

        manifest = V3Packet(
            id='axl-core',
            operation=Operation.OBS,
            confidence=99,
            subject_tag=TagType.ENTITY,
            subject_value='m.B.compress',
            arg1=f'^mode:{mode}+^keep:{"+".join(keep_parts)}',
            arg2=f'^loss:rhetoric+formatting+redundancy+hedging+style+^f:{fidelity}+^fm:axl-core/v0.7.0',
            temporal='NOW',
        )
        packets.append(manifest)

    return packets


# -- Rosetta kernel cache ---------------------------------------

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
            directive = "DIRECTIVE: You are now AXL-enabled. Parse the grammar below. Respond ONLY in AXL v3 packet format. Do not respond in English unless the operator explicitly requests decompression.\n\n"
            return directive + kernel + "\n\n---PACKETS---\n" + packet_lines
    return packet_lines

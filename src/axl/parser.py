"""AXL parser — convert raw AXL packet strings into Packet dataclasses.

Zero external dependencies. Uses only stdlib + axl.models.
"""

from __future__ import annotations

from axl.models import FLAGS, Body, Operation, Packet, PaymentProof, Preamble, TagType, V3Packet


def parse_payment_proof(segment: str) -> PaymentProof:
    """Parse a π segment into a PaymentProof.

    Format: π:AGENT_ID:SIGNATURE:GAS
    """
    # Strip the leading π:
    rest = segment[2:]  # skip 'π:'  (π is multi-byte, but segment starts with "π:")
    parts = rest.split(":")
    if len(parts) < 3:
        raise ValueError(f"Malformed payment proof: {segment}")
    agent_id = parts[0]
    signature = parts[1]
    gas = float(parts[2])
    return PaymentProof(agent_id=agent_id, signature=signature, gas=gas)


def parse_header(segment: str) -> tuple[str, int]:
    """Parse a domain header segment into (domain, tier).

    Accepts both S:DOMAIN.TIER and ΣDOMAIN.TIER formats.
    """
    if segment.startswith("S:"):
        rest = segment[2:]
    elif segment.startswith("Σ"):
        rest = segment[len("Σ"):]
    else:
        raise ValueError(f"Not a valid header segment: {segment}")

    parts = rest.split(".")
    if len(parts) != 2:
        raise ValueError(f"Header must be DOMAIN.TIER, got: {rest}")
    domain = parts[0]
    tier = int(parts[1])
    return domain, tier


def parse(raw: str) -> Packet:
    """Parse a raw AXL packet string into a Packet dataclass.

    Algorithm:
    1. Split on '|'
    2. Walk segments left to right, consuming preamble fields first,
       then the domain header, then body fields, then trailing flags.
    """
    segments = raw.split("|")

    rosetta_url: str | None = None
    payment: PaymentProof | None = None
    timestamp: int | None = None
    domain: str = ""
    tier: int = 1
    body_fields: list[str] = []
    flags: list[str] = []

    header_found = False
    body_start_idx: int | None = None

    # First pass: find preamble and header
    idx = 0
    while idx < len(segments):
        seg = segments[idx].strip()

        if not header_found:
            # Preamble detection
            if seg.startswith("@") and not _is_header(seg):
                # Could be rosetta URL (preamble) or a body field starting with @
                # Rosetta URLs appear before the header
                rosetta_url = seg[1:]  # strip leading @
                idx += 1
                continue

            if seg.startswith("π:"):
                payment = parse_payment_proof(seg)
                idx += 1
                continue

            if seg.startswith("T:"):
                timestamp = int(seg[2:])
                idx += 1
                continue

            if _is_header(seg):
                domain, tier = parse_header(seg)
                header_found = True
                body_start_idx = idx + 1
                idx += 1
                continue

            # If we reach here before header, treat as unknown preamble;
            # skip to avoid infinite loop
            idx += 1
            continue

        idx += 1

    # Second pass: split remaining segments into body vs flags (from the tail)
    if body_start_idx is not None:
        remaining = segments[body_start_idx:]

        # Collect trailing flags from right to left
        flag_list: list[str] = []
        while remaining and remaining[-1].strip() in FLAGS:
            flag_list.append(remaining.pop().strip())
        flag_list.reverse()

        body_fields = [s.strip() for s in remaining]
        flags = flag_list

    preamble = Preamble(
        rosetta_url=rosetta_url,
        payment=payment,
        timestamp=timestamp,
    )
    body = Body(domain=domain, tier=tier, fields=body_fields)

    return Packet(preamble=preamble, body=body, flags=flags)


def _is_header(seg: str) -> bool:
    """Check if a segment looks like a domain header."""
    if seg.startswith("S:") and "." in seg[2:]:
        return True
    if seg.startswith("Σ") and "." in seg[len("Σ"):]:
        return True
    return False


# ─── v3 parser ─────────────────────────────────────────────

_V3_OPS = frozenset(op.value for op in Operation)
_TAG_MAP = {t.value: t for t in TagType}


def detect_version(line: str) -> str:
    """Detect whether a packet is v1 or v3 format.

    v3: second field matches OP.CC pattern (e.g. OBS.99, INF.85).
    v1: contains S:DOMAIN.TIER or ΣDOMAIN.TIER.
    """
    parts = line.split("|")
    if len(parts) >= 2:
        second = parts[1].strip()
        dot = second.find(".")
        if dot > 0 and second[:dot] in _V3_OPS:
            return "v3"
    return "v1"


def parse_v3(line: str) -> V3Packet:
    """Parse a v3 AXL packet string into a V3Packet.

    Format: ID|OP.CC|SUBJ|ARG1|ARG2|TEMP [META]
    """
    parts = line.split("|")
    if len(parts) < 3:
        raise ValueError(f"v3 packet needs at least 3 fields, got {len(parts)}")

    # Field 0: ID (strip ID: prefix if present)
    raw_id = parts[0].strip()
    if raw_id.startswith("ID:"):
        raw_id = raw_id[3:]
    agent_id = raw_id

    # Field 1: OP.CC
    op_cc = parts[1].strip()
    dot = op_cc.index(".")
    op_str = op_cc[:dot]
    cc = int(op_cc[dot + 1:])
    operation = Operation(op_str)

    # Field 2: SUBJ (TAG.value)
    subj = parts[2].strip()
    if subj and subj[0] in _TAG_MAP:
        tag = _TAG_MAP[subj[0]]
        value = subj[1:]
        if value.startswith("."):
            # e.g. @axl.genesis -> tag=@, value=axl.genesis
            # But $BTC -> tag=$, value=BTC
            # The dot is part of the value for entity/domain names
            pass
        value = value.lstrip(".")  # strip leading dot if tag separator
        # Reconstruct: for cases like @dx.patient_47F, keep full value
        if subj[0] in ("@", "#", "!", "~", "^", "$"):
            value = subj[1:]
    else:
        tag = TagType.VALUE
        value = subj

    # Fields 3+: ARG1, ARG2, TEMP, META...
    # The temporal field is the LAST positional field before META (^key:val).
    # We scan from field 3 onward to find where temporal is.
    _VALID_TEMP = frozenset({"NOW", "1H", "4H", "1D", "1W", "1M", "HIST"})
    remaining = [p.strip() for p in parts[3:]]

    arg1 = None
    arg2 = None
    temporal = "NOW"
    meta: dict[str, str] = {}

    # Separate meta fields (^key:val) from positional fields
    positional: list[str] = []
    for f in remaining:
        if f.startswith("^") and ":" in f[1:] and not f.startswith("^c:"):
            # Could be meta or a value arg - check if it looks like key:value meta
            # Meta fields are single ^key:value, not compound like ^67420 or ^fund:-0.02%+^OI:12.4B
            if "+" not in f and len(f.split(":")[0]) < 10:
                key, _, val = f[1:].partition(":")
                meta[key] = val
                continue
        positional.append(f)

    # Find temporal: scan from the end of positional fields
    if positional and positional[-1] in _VALID_TEMP:
        temporal = positional.pop()

    # Assign positional fields to arg1, arg2
    # Extra positional fields beyond arg1/arg2 are joined into arg2
    if len(positional) >= 1:
        arg1 = positional[0]
    if len(positional) == 2:
        arg2 = positional[1]
    elif len(positional) > 2:
        arg2 = positional[1] + "|" + "|".join(positional[2:])

    # Empty strings become None for optional fields
    if arg1 == "":
        arg1 = None
    if arg2 == "":
        arg2 = None

    return V3Packet(
        id=agent_id,
        operation=operation,
        confidence=cc,
        subject_tag=tag,
        subject_value=value,
        arg1=arg1,
        arg2=arg2,
        temporal=temporal,
        meta=meta,
    )

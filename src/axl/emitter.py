"""AXL emitter — convert Packet dataclasses back to AXL wire strings.

Round-trip fidelity: parse(emit(packet)) must produce an equivalent Packet.
Zero external dependencies.
"""

from __future__ import annotations

from axl.models import Operation, Packet, TagType, V3Packet


def emit(packet: Packet) -> str:
    """Emit a Packet as an AXL pipe-delimited string.

    Segment order:
      @rosetta_url | π:id:sig:gas | T:timestamp | S:DOMAIN.TIER | ...fields | ...flags
    """
    segments: list[str] = []

    # Preamble
    if packet.preamble.rosetta_url is not None:
        segments.append(f"@{packet.preamble.rosetta_url}")

    if packet.preamble.payment is not None:
        p = packet.preamble.payment
        segments.append(f"π:{p.agent_id}:{p.signature}:{p.gas}")

    if packet.preamble.timestamp is not None:
        segments.append(f"T:{packet.preamble.timestamp}")

    # Header
    segments.append(f"S:{packet.body.domain}.{packet.body.tier}")

    # Body fields
    segments.extend(packet.body.fields)

    # Flags
    segments.extend(packet.flags)

    return "|".join(segments)


# ─── v3 emitter ────────────────────────────────────────────


def emit_v3(packet: V3Packet) -> str:
    """Emit a V3Packet as a pipe-delimited AXL v3 string."""
    parts = [
        f"ID:{packet.id}",
        f"{packet.operation.value}.{packet.confidence:02d}",
        f"{packet.subject_tag.value}{packet.subject_value}",
    ]
    parts.append(packet.arg1 if packet.arg1 is not None else "")
    parts.append(packet.arg2 if packet.arg2 is not None else "")
    parts.append(packet.temporal)

    for key, val in packet.meta.items():
        parts.append(f"^{key}:{val}")

    # Strip trailing empty fields (but keep at least ID|OP|SUBJ)
    while len(parts) > 3 and parts[-1] == "":
        parts.pop()

    return "|".join(parts)


def v3_to_json(packet: V3Packet) -> dict:
    """Convert a V3Packet to application/vnd.axl+json format."""
    return {
        "v": "3",
        "id": packet.id,
        "op": packet.operation.value,
        "cc": packet.confidence,
        "s": {"t": packet.subject_tag.value, "v": packet.subject_value},
        "a1": packet.arg1,
        "a2": packet.arg2,
        "t": packet.temporal,
        "m": packet.meta,
    }


_TAG_FROM_STR = {t.value: t for t in TagType}
_OP_FROM_STR = {o.value: o for o in Operation}


def v3_from_json(data: dict) -> V3Packet:
    """Build a V3Packet from an application/vnd.axl+json dict."""
    subj = data.get("s", {})
    return V3Packet(
        id=data.get("id", ""),
        operation=_OP_FROM_STR.get(data.get("op", "OBS"), Operation.OBS),
        confidence=int(data.get("cc", 0)),
        subject_tag=_TAG_FROM_STR.get(subj.get("t", "^"), TagType.VALUE),
        subject_value=subj.get("v", ""),
        arg1=data.get("a1"),
        arg2=data.get("a2"),
        temporal=data.get("t", "NOW"),
        meta=data.get("m", {}),
    )

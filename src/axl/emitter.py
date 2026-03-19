"""AXL emitter — convert Packet dataclasses back to AXL wire strings.

Round-trip fidelity: parse(emit(packet)) must produce an equivalent Packet.
Zero external dependencies.
"""

from __future__ import annotations

from axl.models import Packet


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

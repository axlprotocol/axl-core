"""AXL parser — convert raw AXL packet strings into Packet dataclasses.

Zero external dependencies. Uses only stdlib + axl.models.
"""

from __future__ import annotations

from axl.models import FLAGS, Body, Packet, PaymentProof, Preamble


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

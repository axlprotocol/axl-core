"""AXL translator — convert packets to/from human-readable formats.

Three modes: to_english, to_json, from_json.
Zero external dependencies.
"""

from __future__ import annotations

from axl.models import Body, Packet, PaymentProof, Preamble
from axl.schemas import get_schema

# ─── Direction symbols to English words ─────────────────────

_DIR_WORDS: dict[str, str] = {
    "↑": "rising",
    "↓": "falling",
    "↑↑": "surging",
    "↓↓": "plummeting",
    "~": "neutral",
    "++": "strongly rising",
    "--": "strongly falling",
}

# ─── Domain to human-readable label ─────────────────────────

_DOMAIN_LABELS: dict[str, str] = {
    "TRD": "Trade Signal",
    "SIG": "Signal",
    "COMM": "Communication",
    "OPS": "Operations Alert",
    "SEC": "Security Alert",
    "DEV": "Development",
    "RES": "Research",
    "REG": "Registration",
    "PAY": "Payment",
    "FUND": "Funding Request",
}


def _format_field_value(value: str, field_type: str) -> str:
    """Format a single field value for English output."""
    if field_type == "dir":
        return _DIR_WORDS.get(value, value)
    if field_type == "pct":
        # Convert 0-1 float string to percentage
        try:
            if value.startswith("."):
                pct = float(value) * 100
                return f"{pct:.0f}%"
            pct = float(value)
            if pct <= 1.0:
                return f"{pct * 100:.0f}%"
            return f"{pct}%"
        except ValueError:
            return value
    return value


def to_english(packet: Packet) -> str:
    """Build a human-readable English sentence from an AXL packet.

    Example:
        Packet(SIG, tier=3, fields=[BTC, 69200, ↓, RSI, .64])
        → "Agent 5: BTC at 69200, falling. RSI pattern detected with 64% confidence."
    """
    parts: list[str] = []

    # Agent prefix
    agent = packet.agent_id
    if agent:
        parts.append(f"Agent {agent}:")
    else:
        parts.append(f"{_DOMAIN_LABELS.get(packet.domain, packet.domain)}:")

    schema = get_schema(packet.domain)
    fields = packet.body.fields

    if schema and fields:
        field_map: dict[str, str] = {}
        for i, fdef in enumerate(schema):
            if i < len(fields):
                field_map[fdef.name] = fields[i]

        # Build domain-specific English
        parts.append(_build_domain_english(packet.domain, field_map, schema))
    elif fields:
        # No schema — just list raw fields
        parts.append(" | ".join(fields))

    # Payment info
    if packet.preamble.payment:
        p = packet.preamble.payment
        parts.append(f"Gas fee: {p.gas}.")

    # Flags
    if packet.flags:
        parts.append(f"Flags: {', '.join(packet.flags)}.")

    return " ".join(parts)


def _build_domain_english(domain: str, field_map: dict[str, str],
                          schema: list) -> str:
    """Build domain-specific English from field_map."""
    if domain == "SIG":
        asset = field_map.get("asset", "?")
        price = field_map.get("price", "?")
        direction = _DIR_WORDS.get(field_map.get("direction", ""), "unknown")
        pattern = field_map.get("pattern", "")
        confidence = _format_field_value(field_map.get("confidence", "?"), "pct")
        return (
            f"{asset} at {price}, {direction}."
            f" {pattern} pattern detected with {confidence} confidence."
        )

    if domain == "TRD":
        asset = field_map.get("asset", "?")
        price = field_map.get("price", "?")
        momentum = _DIR_WORDS.get(field_map.get("momentum", ""), "unknown")
        action = field_map.get("action", "")
        confidence = _format_field_value(field_map.get("confidence", "?"), "pct")
        size = field_map.get("size", "")
        text = f"{asset} at {price}, momentum {momentum}."
        if action:
            text += f" Action: {action}"
            if size:
                text += f" (size {size})"
            text += f" with {confidence} confidence."
        return text

    if domain == "COMM":
        from_a = field_map.get("from_agent", "?")
        to_a = field_map.get("to_agent", "?")
        intent = field_map.get("intent", "?")
        detail = field_map.get("detail", "")
        return f"From {from_a} to {to_a}: [{intent}] {detail}"

    if domain == "OPS":
        target = field_map.get("target", "?")
        status = field_map.get("status", "?")
        metric = field_map.get("metric", "")
        value = field_map.get("value", "")
        threshold = field_map.get("threshold", "")
        action = field_map.get("action", "")
        text = f"Service {target} status {status}."
        if metric and value:
            text += f" {metric}={value}"
            if threshold:
                text += f" (threshold {threshold})"
            text += "."
        if action:
            text += f" Action: {action}."
        return text

    if domain == "SEC":
        target = field_map.get("target", "?")
        threat = field_map.get("threat", "?")
        severity = field_map.get("severity", "?")
        action = field_map.get("action", "")
        confidence = _format_field_value(field_map.get("confidence", "?"), "pct")
        text = f"Threat {threat} on {target}, severity {severity}."
        text += f" Detection confidence {confidence}."
        if action:
            text += f" Action: {action}."
        return text

    if domain == "DEV":
        repo = field_map.get("repo", "?")
        branch = field_map.get("branch", "?")
        status = field_map.get("status", "?")
        action = field_map.get("action", "")
        return f"Repo {repo}/{branch}: {status}. Action: {action}."

    if domain == "RES":
        topic = field_map.get("topic", "?")
        sources = field_map.get("sources", "?")
        confidence = _format_field_value(field_map.get("confidence", "?"), "pct")
        finding = field_map.get("finding", "")
        return f"Research on {topic} ({sources} sources, {confidence} confidence): {finding}"

    if domain == "REG":
        name = field_map.get("name", "?")
        agent_type = field_map.get("type", "?")
        agent_class = field_map.get("class", "?")
        return f"Agent registration: {name} (type={agent_type}, class={agent_class})."

    if domain == "PAY":
        payee = field_map.get("payee", "?")
        amount = field_map.get("amount", "?")
        currency = field_map.get("currency", "?")
        chain = field_map.get("chain", "")
        memo = field_map.get("memo", "")
        text = f"Payment of {amount} {currency} to {payee}"
        if chain:
            text += f" on {chain}"
        if memo:
            text += f" ({memo})"
        return text + "."

    if domain == "FUND":
        requester = field_map.get("requester", "?")
        amount = field_map.get("amount", "?")
        currency = field_map.get("currency", "?")
        reason = field_map.get("reason", "")
        urgency = field_map.get("urgency", "")
        text = f"Funding request from {requester}: {amount} {currency}"
        if reason:
            text += f" for {reason}"
        if urgency:
            text += f" (urgency: {urgency})"
        return text + "."

    # Fallback for unknown domains
    return " | ".join(f"{k}={v}" for k, v in field_map.items())


def to_json(packet: Packet) -> dict:
    """Convert a Packet to a structured dict.

    Returns:
        {
            "preamble": {"rosetta_url": ..., "payment": {...}, "timestamp": ...},
            "domain": "SIG",
            "tier": 3,
            "fields": {"asset": "BTC", "price": "69200", ...},
            "flags": ["SIG"]
        }
    """
    # Preamble
    preamble_dict: dict[str, object] = {}
    if packet.preamble.rosetta_url is not None:
        preamble_dict["rosetta_url"] = packet.preamble.rosetta_url
    if packet.preamble.payment is not None:
        p = packet.preamble.payment
        preamble_dict["payment"] = {
            "agent_id": p.agent_id,
            "signature": p.signature,
            "gas": p.gas,
        }
    if packet.preamble.timestamp is not None:
        preamble_dict["timestamp"] = packet.preamble.timestamp

    # Fields — use schema names if available
    schema = get_schema(packet.domain)
    fields_dict: dict[str, str] = {}
    if schema:
        for i, fdef in enumerate(schema):
            if i < len(packet.body.fields):
                fields_dict[fdef.name] = packet.body.fields[i]
    else:
        for i, val in enumerate(packet.body.fields):
            fields_dict[f"field_{i}"] = val

    return {
        "preamble": preamble_dict,
        "domain": packet.domain,
        "tier": packet.tier,
        "fields": fields_dict,
        "flags": list(packet.flags),
    }


def from_json(data: dict) -> Packet:
    """Build a Packet from a dict (reverse of to_json).

    Accepts the same structure that to_json produces.
    """
    # Preamble
    preamble_data = data.get("preamble", {})
    payment = None
    if "payment" in preamble_data:
        pd = preamble_data["payment"]
        payment = PaymentProof(
            agent_id=pd["agent_id"],
            signature=pd["signature"],
            gas=float(pd["gas"]),
        )

    preamble = Preamble(
        rosetta_url=preamble_data.get("rosetta_url"),
        payment=payment,
        timestamp=preamble_data.get("timestamp"),
    )

    # Body fields — convert named dict back to positional list
    domain = data.get("domain", "")
    tier = data.get("tier", 1)
    fields_data = data.get("fields", {})

    schema = get_schema(domain)
    if schema and isinstance(fields_data, dict):
        fields_list: list[str] = []
        for fdef in schema:
            if fdef.name in fields_data:
                fields_list.append(str(fields_data[fdef.name]))
            else:
                break  # stop at first missing field
    elif isinstance(fields_data, dict):
        fields_list = list(fields_data.values())
    else:
        fields_list = list(fields_data)

    body = Body(domain=domain, tier=tier, fields=fields_list)

    # Flags
    flags = data.get("flags", [])

    return Packet(preamble=preamble, body=body, flags=list(flags))

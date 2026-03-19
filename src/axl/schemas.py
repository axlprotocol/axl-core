"""AXL domain schemas — all 10 domains from the Rosetta.

Each schema defines the positional field order and expected types.
Position = meaning. No labels. No keys.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class FieldDef:
    """Definition of a single schema field."""
    name: str
    field_type: str  # "str", "num", "pct", "dir", "action", "intent", "currency"
    description: str = ""


# ─── Domain Schemas ──────────────────────────────────────────

SCHEMAS: dict[str, list[FieldDef]] = {
    "TRD": [
        FieldDef("asset", "str", "Asset symbol"),
        FieldDef("price", "num", "Current price"),
        FieldDef("momentum", "dir", "Price momentum direction"),
        FieldDef("volatility", "dir", "Volatility direction"),
        FieldDef("pattern", "str", "Technical pattern name"),
        FieldDef("confidence", "pct", "Confidence 0-1"),
        FieldDef("action", "action", "Trade action"),
        FieldDef("size", "num", "Position size"),
        FieldDef("leverage", "num", "Leverage multiplier"),
        FieldDef("risk", "str", "Risk limit (e.g. R<=.02)"),
    ],
    "SIG": [
        FieldDef("asset", "str", "Asset symbol"),
        FieldDef("price", "num", "Current price"),
        FieldDef("direction", "dir", "Price direction"),
        FieldDef("pattern", "str", "Technical pattern"),
        FieldDef("confidence", "pct", "Confidence 0-1"),
    ],
    "COMM": [
        FieldDef("from_agent", "str", "Sender AXL ID"),
        FieldDef("to_agent", "str", "Recipient AXL ID or 'broadcast'"),
        FieldDef("intent", "intent", "Message intent"),
        FieldDef("detail", "str", "Message content"),
    ],
    "OPS": [
        FieldDef("target", "str", "Service or endpoint"),
        FieldDef("status", "str", "Current status"),
        FieldDef("metric", "str", "Metric name"),
        FieldDef("value", "str", "Metric value"),
        FieldDef("threshold", "str", "Alert threshold"),
        FieldDef("action", "str", "Response action"),
    ],
    "SEC": [
        FieldDef("target", "str", "Target agent or service"),
        FieldDef("threat", "str", "Threat type"),
        FieldDef("severity", "str", "Severity level"),
        FieldDef("action", "str", "Response action"),
        FieldDef("confidence", "pct", "Detection confidence 0-1"),
    ],
    "DEV": [
        FieldDef("repo", "str", "Repository name"),
        FieldDef("branch", "str", "Branch name"),
        FieldDef("status", "str", "Build/review status"),
        FieldDef("action", "str", "Action type"),
        FieldDef("author", "str", "Author identifier"),
        FieldDef("confidence", "pct", "Quality confidence 0-1"),
        FieldDef("risk", "str", "Risk level (e.g. R<=.05)"),
    ],
    "RES": [
        FieldDef("topic", "str", "Research topic"),
        FieldDef("sources", "str", "Source count or description"),
        FieldDef("confidence", "pct", "Confidence 0-1"),
        FieldDef("finding", "str", "Research finding"),
    ],
    "REG": [
        FieldDef("name", "str", "Agent name"),
        FieldDef("pubkey", "str", "Public key"),
        FieldDef("type", "str", "Agent type (AGT, SVC)"),
        FieldDef("class", "str", "Agent class (TRD, OPS, SEC, etc.)"),
        FieldDef("referrer", "str", "Referring agent or _"),
    ],
    "PAY": [
        FieldDef("payee", "str", "Recipient AXL ID"),
        FieldDef("amount", "num", "Payment amount"),
        FieldDef("currency", "currency", "Currency code"),
        FieldDef("chain", "str", "Blockchain or 'local'"),
        FieldDef("memo", "str", "Payment memo"),
    ],
    "FUND": [
        FieldDef("requester", "str", "Requesting agent AXL ID"),
        FieldDef("to", "str", "Target or 'broadcast'"),
        FieldDef("amount", "num", "Requested amount"),
        FieldDef("currency", "currency", "Currency code"),
        FieldDef("reason", "str", "Funding reason"),
        FieldDef("roi", "str", "Expected ROI"),
        FieldDef("balance", "num", "Current balance"),
        FieldDef("urgency", "str", "Urgency level"),
    ],
}


# ─── Valid Value Sets ────────────────────────────────────────

VALID_DIRECTIONS = frozenset({"↑", "↓", "↑↑", "↓↓", "~", "++", "--"})
VALID_ACTIONS = frozenset({"LONG", "SHORT", "HOLD", "CLOSE", "BUY", "SELL"})
VALID_INTENTS = frozenset({"REQUEST", "ACK", "STATUS", "REVIEW", "REJECT", "QUERY", "ROUTE"})
VALID_CURRENCIES = frozenset({"USDC", "USD", "BTC", "ETH", "SOL", "local"})
VALID_FLAGS = frozenset({"LOG", "STRM", "ACK", "URG", "SIG", "QRY"})

ALL_DOMAINS = frozenset(SCHEMAS.keys())


def get_schema(domain: str) -> Optional[list[FieldDef]]:
    """Get the schema for a domain, or None if unknown."""
    return SCHEMAS.get(domain)


def domain_field_count(domain: str) -> int:
    """Expected number of body fields for a domain."""
    schema = SCHEMAS.get(domain)
    return len(schema) if schema else 0

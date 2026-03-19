"""AXL data models — pure Python dataclasses, zero dependencies."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class FieldType(Enum):
    """Type determinatives — inspired by Egyptian hieroglyphs."""
    INTEGER = "#"       # #69200
    FLOAT = "%"         # %.64
    CURRENCY = "$"      # $0.001
    REFERENCE = "@"     # @api.example.com
    ASSERTION = "!"     # !ALERT
    UNCERTAINTY = "?"   # ?RSIdiv
    RAW = ""            # untyped string


class Direction(Enum):
    """Momentum / trend direction indicators."""
    UP = "↑"
    DOWN = "↓"
    STRONG_UP = "++"
    STRONG_DOWN = "--"
    NEUTRAL = "~"
    ARROW_UP = "↑↑"
    ARROW_DOWN = "↓↓"


# Canonical flag set
FLAGS = frozenset({"LOG", "STRM", "ACK", "URG", "SIG", "QRY"})


@dataclass
class PaymentProof:
    """The π proof — identity, signature, and gas fee.

    π:AXL-00000005:0xSIGNATURE:0.001
    """
    agent_id: str
    signature: str
    gas: float

    def __str__(self) -> str:
        return f"π:{self.agent_id}:{self.signature}:{self.gas}"


@dataclass
class TypedField:
    """A single field with optional type prefix."""
    value: str
    field_type: FieldType = FieldType.RAW

    @property
    def is_null(self) -> bool:
        return self.value in ("_", "∅", "")

    def __str__(self) -> str:
        if self.is_null:
            return self.value
        if self.field_type == FieldType.RAW:
            return self.value
        return f"{self.field_type.value}{self.value}"


@dataclass
class Preamble:
    """Optional preamble: @rosetta pointer, π payment proof, T: timestamp."""
    rosetta_url: Optional[str] = None
    payment: Optional[PaymentProof] = None
    timestamp: Optional[int] = None


@dataclass
class Body:
    """Packet body: S:DOMAIN.TIER followed by positional fields."""
    domain: str
    tier: int
    fields: list[str] = field(default_factory=list)


@dataclass
class Packet:
    """A complete AXL packet — preamble + body + flags.

    @axlprotocol.org/rosetta|π:5:0xS:.001|T:1710072600|S:OPS.2|@api.example.com|ERR500|latency|4500ms|500ms|ALERT|LOG
    """
    preamble: Preamble = field(default_factory=Preamble)
    body: Body = field(default_factory=lambda: Body(domain="", tier=1))
    flags: list[str] = field(default_factory=list)

    @property
    def domain(self) -> str:
        return self.body.domain

    @property
    def tier(self) -> int:
        return self.body.tier

    @property
    def agent_id(self) -> Optional[str]:
        if self.preamble.payment:
            return self.preamble.payment.agent_id
        return None

    def __str__(self) -> str:
        from axl.emitter import emit
        return emit(self)


@dataclass
class ValidationWarning:
    """A single validation finding."""
    field_name: str
    message: str
    severity: str = "warning"  # "warning" or "error"


@dataclass
class ValidationResult:
    """Result of validating a packet."""
    valid: bool
    warnings: list[ValidationWarning] = field(default_factory=list)
    errors: list[ValidationWarning] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.valid and len(self.errors) == 0

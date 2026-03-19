"""AXL — Agent eXchange Language.

A universal communication protocol for agents and autonomous machines.
https://axlprotocol.org
"""

__version__ = "0.4.0"

from axl.emitter import emit
from axl.models import (
    FLAGS,
    Body,
    FieldType,
    Packet,
    PaymentProof,
    Preamble,
    TypedField,
    ValidationResult,
    ValidationWarning,
)
from axl.parser import parse
from axl.schemas import ALL_DOMAINS, SCHEMAS
from axl.validator import validate

__all__ = [
    "__version__",
    "parse",
    "emit",
    "validate",
    "Body",
    "FieldType",
    "Packet",
    "PaymentProof",
    "Preamble",
    "TypedField",
    "ValidationResult",
    "ValidationWarning",
    "FLAGS",
    "SCHEMAS",
    "ALL_DOMAINS",
]

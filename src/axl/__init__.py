"""AXL — Agent eXchange Language.

A universal communication protocol for agents and autonomous machines.
https://axlprotocol.org
"""

__version__ = "0.7.0"

from axl.compressor import compress, english_to_v3
from axl.decompressor import decompress, v3_to_english as decompress_to_claims, format_decompressed, parse_packet, strip_kernel
from axl.emitter import emit, emit_v3, v3_from_json, v3_to_json
from axl.models import (
    FLAGS,
    Body,
    FieldType,
    Operation,
    Packet,
    PaymentProof,
    Preamble,
    TagType,
    TypedField,
    V3Packet,
    ValidationResult,
    ValidationWarning,
)
from axl.parser import detect_version, parse, parse_v3
from axl.schemas import ALL_DOMAINS, SCHEMAS
from axl.translator import v3_to_english
from axl.validator import validate, validate_v3

__all__ = [
    "__version__",
    "compress",
    "english_to_v3",
    "decompress",
    "decompress_to_claims",
    "format_decompressed",
    "parse_packet",
    "strip_kernel",
    "parse",
    "parse_v3",
    "detect_version",
    "emit",
    "emit_v3",
    "v3_to_json",
    "v3_from_json",
    "v3_to_english",
    "validate",
    "validate_v3",
    "Body",
    "FieldType",
    "Operation",
    "Packet",
    "PaymentProof",
    "Preamble",
    "TagType",
    "TypedField",
    "V3Packet",
    "ValidationResult",
    "ValidationWarning",
    "FLAGS",
    "SCHEMAS",
    "ALL_DOMAINS",
]

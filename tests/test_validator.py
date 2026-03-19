"""Tests for the AXL validator."""

from axl.parser import parse
from axl.validator import validate


def test_valid_signal():
    pkt = parse("π:5:0xS:.001|S:SIG.3|BTC|69200|↓|RSI|.64|SIG")
    result = validate(pkt)
    assert result.valid
    assert len(result.errors) == 0


def test_valid_payment():
    pkt = parse("π:8:0xS:.01|S:PAY.1|AXL-1|0.02|USDC|local|task_done|LOG")
    result = validate(pkt)
    assert result.valid


def test_invalid_direction():
    pkt = parse("π:5:0xS:.001|S:SIG.3|BTC|69200|WRONG|RSI|.64|SIG")
    result = validate(pkt)
    assert not result.valid
    assert any("direction" in e.field_name for e in result.errors)


def test_invalid_confidence():
    pkt = parse("π:5:0xS:.001|S:SIG.3|BTC|69200|↓|RSI|5.0|SIG")
    result = validate(pkt)
    assert not result.valid
    assert any("confidence" in e.field_name for e in result.errors)


def test_unknown_domain():
    pkt = parse("π:1:0xS:.001|S:FAKE.3|foo|bar")
    result = validate(pkt)
    assert not result.valid
    assert any("Unknown domain" in e.message for e in result.errors)


def test_invalid_tier():
    pkt = parse("π:1:0xS:.001|S:SIG.9|BTC|69200|↓|RSI|.64|SIG")
    result = validate(pkt)
    assert any("Tier" in e.message for e in result.errors)


def test_null_fields_are_valid():
    pkt = parse("π:1:0xS:.001|S:SIG.3|BTC|69200|↓|_|_|SIG")
    result = validate(pkt)
    assert result.valid


def test_valid_ops():
    pkt = parse("π:1:0xS:.001|S:OPS.2|@api.example.com|ERR500|latency|4500ms|500ms|ALERT|LOG")
    result = validate(pkt)
    assert result.valid


def test_valid_security():
    pkt = parse("π:7:0xS:.001|S:SEC.4|AXL-2|THEFT_SUSPECTED|CRIT|ALERT|.90|URG")
    result = validate(pkt)
    assert result.valid


def test_fewer_fields_than_schema():
    """Fewer fields than schema should warn but not error."""
    pkt = parse("π:5:0xS:.001|S:SIG.3|BTC|69200")
    result = validate(pkt)
    # Should still be valid, just with fewer fields
    assert len(result.errors) == 0

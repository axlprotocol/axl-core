"""Tests for the AXL emitter — including round-trip fidelity."""

from axl.emitter import emit
from axl.models import Body, Packet, PaymentProof, Preamble
from axl.parser import parse


def test_emit_simple():
    pkt = Packet(
        preamble=Preamble(payment=PaymentProof("5", "0xS", 0.001)),
        body=Body(domain="SIG", tier=3, fields=["BTC", "69200", "↓", "RSI", ".64"]),
        flags=["SIG"],
    )
    result = emit(pkt)
    assert "π:5:0xS:0.001" in result
    assert "S:SIG.3" in result
    assert result.endswith("|SIG")


def test_emit_with_rosetta():
    pkt = Packet(
        preamble=Preamble(
            rosetta_url="axlprotocol.org/rosetta",
            payment=PaymentProof("11", "0xS", 0.01),
        ),
        body=Body(domain="REG", tier=1, fields=["phantom-x", "pk", "AGT", "TRD", "_"]),
        flags=["LOG"],
    )
    result = emit(pkt)
    assert result.startswith("@axlprotocol.org/rosetta|")


def test_emit_with_timestamp():
    pkt = Packet(
        preamble=Preamble(
            payment=PaymentProof("2", "0xS", 0.01),
            timestamp=1710072600,
        ),
        body=Body(domain="OPS", tier=4, fields=["@prod-srv", "OK", "CPU", "45%", "80%", "_"]),
        flags=["LOG"],
    )
    result = emit(pkt)
    assert "T:1710072600" in result


def test_roundtrip_signal():
    raw = "π:5:0xS:0.001|S:SIG.3|BTC|69200|↓|RSI|.64|SIG"
    assert emit(parse(raw)) == raw


def test_roundtrip_trade():
    raw = "π:2:0xS:0.001|S:TRD.3|BTC|69200|↓|~|RSI|.64|SHORT|.5|2|R<=.02|LOG"
    assert emit(parse(raw)) == raw


def test_roundtrip_payment():
    raw = "π:8:0xS:0.01|S:PAY.1|AXL-1|0.02|USDC|local|crawl_task_completed|LOG"
    assert emit(parse(raw)) == raw


def test_roundtrip_security():
    raw = "π:7:0xS:0.001|S:SEC.4|AXL-2|THEFT_SUSPECTED|CRIT|ALERT|.90|URG"
    assert emit(parse(raw)) == raw


def test_roundtrip_with_rosetta():
    raw = "@axlprotocol.org/rosetta|π:11:0xS:0.01|S:REG.1|rogue/phantom-x|pk|AGT|TRD|_|LOG"
    assert emit(parse(raw)) == raw


def test_roundtrip_idempotent():
    raw = "π:5:0xS:0.001|S:SIG.3|BTC|69200|↓|RSI|.64|SIG"
    pkt = parse(raw)
    assert emit(parse(emit(pkt))) == emit(pkt)

"""Tests for the AXL translator."""

from axl.parser import parse
from axl.translator import from_json, to_english, to_json


def test_to_english_signal():
    pkt = parse("π:5:0xS:.001|S:SIG.3|BTC|69200|↓|RSI|.64|SIG")
    english = to_english(pkt)
    assert "BTC" in english
    assert "69200" in english
    assert "falling" in english or "↓" in english
    assert "64%" in english or ".64" in english


def test_to_english_payment():
    pkt = parse("π:8:0xS:.01|S:PAY.1|AXL-1|0.02|USDC|local|crawl_task|LOG")
    english = to_english(pkt)
    assert "AXL-1" in english
    assert "0.02" in english
    assert "USDC" in english


def test_to_json_signal():
    pkt = parse("π:5:0xS:.001|S:SIG.3|BTC|69200|↓|RSI|.64|SIG")
    j = to_json(pkt)
    assert j["domain"] == "SIG"
    assert j["tier"] == 3
    assert j["fields"]["asset"] == "BTC"
    assert j["fields"]["price"] == "69200"
    assert j["fields"]["direction"] == "↓"
    assert j["preamble"]["payment"]["agent_id"] == "5"


def test_to_json_ops():
    pkt = parse("π:1:0xS:.001|S:OPS.2|@api.example.com|ERR500|latency|4500ms|500ms|ALERT|LOG")
    j = to_json(pkt)
    assert j["domain"] == "OPS"
    assert j["fields"]["target"] == "@api.example.com"
    assert j["fields"]["status"] == "ERR500"


def test_from_json_roundtrip():
    pkt = parse("π:5:0xS:.001|S:SIG.3|BTC|69200|↓|RSI|.64|SIG")
    j = to_json(pkt)
    restored = from_json(j)
    assert restored.domain == pkt.domain
    assert restored.tier == pkt.tier
    assert restored.body.fields == pkt.body.fields
    assert restored.flags == pkt.flags


def test_from_json_payment():
    data = {
        "preamble": {
            "payment": {"agent_id": "8", "signature": "0xPM", "gas": 0.01}
        },
        "domain": "PAY",
        "tier": 1,
        "fields": {
            "payee": "AXL-1",
            "amount": "0.02",
            "currency": "USDC",
            "chain": "local",
            "memo": "test",
        },
        "flags": ["LOG"],
    }
    pkt = from_json(data)
    assert pkt.domain == "PAY"
    assert pkt.body.fields[0] == "AXL-1"
    assert pkt.body.fields[1] == "0.02"


def test_to_english_security():
    pkt = parse("π:7:0xS:.001|S:SEC.4|AXL-2|THEFT_SUSPECTED|CRIT|ALERT|.90|URG")
    english = to_english(pkt)
    assert "THEFT_SUSPECTED" in english
    assert "CRIT" in english

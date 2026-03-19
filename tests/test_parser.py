"""Tests for the AXL parser."""

from axl.parser import parse


def test_parse_simple_signal():
    pkt = parse("π:5:0xS:.001|S:SIG.3|BTC|69200|↓|RSI|.64|SIG")
    assert pkt.domain == "SIG"
    assert pkt.tier == 3
    assert pkt.agent_id == "5"
    assert pkt.preamble.payment.gas == 0.001
    assert pkt.body.fields == ["BTC", "69200", "↓", "RSI", ".64"]
    assert pkt.flags == ["SIG"]


def test_parse_with_rosetta():
    pkt = parse("@axlprotocol.org/rosetta|π:11:0xS:.01|S:REG.1|rogue/phantom-x|pk|AGT|TRD|_|LOG")
    assert pkt.preamble.rosetta_url == "axlprotocol.org/rosetta"
    assert pkt.domain == "REG"
    assert pkt.agent_id == "11"
    assert pkt.body.fields == ["rogue/phantom-x", "pk", "AGT", "TRD", "_"]
    assert pkt.flags == ["LOG"]


def test_parse_with_timestamp():
    pkt = parse("π:2:0xS:.01|T:1710072600|S:OPS.4|@prod-srv|OK|CPU|45%|80%|_|LOG")
    assert pkt.preamble.timestamp == 1710072600
    assert pkt.domain == "OPS"
    assert pkt.body.fields[0] == "@prod-srv"


def test_parse_trade_packet():
    raw = "π:2:0xS:.001|S:TRD.3|BTC|69200|↓|~|RSI|.64|SHORT|.5|2|R<=.02|LOG"
    pkt = parse(raw)
    assert pkt.domain == "TRD"
    assert pkt.tier == 3
    assert pkt.body.fields[0] == "BTC"
    assert pkt.body.fields[6] == "SHORT"
    assert pkt.flags == ["LOG"]


def test_parse_payment():
    pkt = parse("π:8:0xS:.01|S:PAY.1|AXL-1|0.02|USDC|local|crawl_task_completed|LOG")
    assert pkt.domain == "PAY"
    assert pkt.body.fields[0] == "AXL-1"
    assert pkt.body.fields[1] == "0.02"
    assert pkt.body.fields[2] == "USDC"


def test_parse_security_alert():
    pkt = parse("π:7:0xS:.001|S:SEC.4|AXL-2|THEFT_SUSPECTED|CRIT|ALERT|.90|URG")
    assert pkt.domain == "SEC"
    assert pkt.tier == 4
    assert pkt.body.fields[1] == "THEFT_SUSPECTED"
    assert pkt.flags == ["URG"]


def test_parse_sigma_format():
    pkt = parse("π:5:0xS:.001|ΣSIG.3|BTC|69200|↓|RSI|.64|SIG")
    assert pkt.domain == "SIG"
    assert pkt.tier == 3
    assert pkt.body.fields[0] == "BTC"


def test_parse_multiple_flags():
    pkt = parse("π:1:0xS:.001|S:OPS.2|@api|ERR500|latency|4500ms|500ms|ALERT|URG|LOG")
    assert "URG" in pkt.flags
    assert "LOG" in pkt.flags
    assert pkt.body.fields[-1] == "ALERT"


def test_parse_no_payment():
    pkt = parse("S:SIG.3|BTC|69200|↓|RSI|.64")
    assert pkt.domain == "SIG"
    assert pkt.preamble.payment is None
    assert pkt.body.fields == ["BTC", "69200", "↓", "RSI", ".64"]


def test_parse_research():
    raw = "π:4:0xS:.001|S:RES.3|incident_correlation|4_agents|.91|causal_chain|LOG"
    pkt = parse(raw)
    assert pkt.domain == "RES"
    assert pkt.body.fields[0] == "incident_correlation"
    assert pkt.body.fields[2] == ".91"

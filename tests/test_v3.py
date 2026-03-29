"""Tests for v3 AXL parser, emitter, validator, and translator."""

from axl.emitter import emit_v3, v3_from_json, v3_to_json
from axl.models import Operation, TagType, V3Packet
from axl.parser import detect_version, parse, parse_v3
from axl.translator import v3_to_english
from axl.validator import validate_v3

# Test packets from the whitepaper
PACKETS = [
    "ID:MKT-01|OBS.99|$BTC|^67420|^fund:-0.02%+^OI:12.4B|NOW",
    "ID:BULL-3|INF.85|$BTC|<-^fund_neg+^OI_rise+^liq_short|up|4H",
    "ID:BEAR-7|CON.72|$BTC|RE:BULL-3|<-^whale_sell_44K|down|1H",
    "ID:SYNTH-1|MRG.80|$BTC|RE:BULL-3+BEAR-7|^range_67K_69K|4H",
    "ID:BULL-3|YLD.88|$BTC|from:up->range|RE:SYNTH-1|4H",
    "ID:SYNTH-1|PRD.78|$BTC|^69200|<-^demand_hold+^fund_neg|4H",
    "ID:DR-CHEN|OBS.99|@dx.patient_47F|^CA125:285+^imaging:complex_cyst|NOW",
    "ID:AGENT-7A3F|OBS.99|@axl.genesis|^v:3+^from:url+^model:claude|NOW",
]


# ── Parse tests ──────────────────────────────────────────

def test_parse_obs():
    pkt = parse_v3(PACKETS[0])
    assert pkt.id == "MKT-01"
    assert pkt.operation == Operation.OBS
    assert pkt.confidence == 99
    assert pkt.subject_tag == TagType.FINANCIAL
    assert pkt.subject_value == "BTC"
    assert pkt.arg1 == "^67420"
    assert pkt.arg2 == "^fund:-0.02%+^OI:12.4B"
    assert pkt.temporal == "NOW"


def test_parse_inf():
    pkt = parse_v3(PACKETS[1])
    assert pkt.id == "BULL-3"
    assert pkt.operation == Operation.INF
    assert pkt.confidence == 85
    assert pkt.arg1 == "<-^fund_neg+^OI_rise+^liq_short"
    assert pkt.arg2 == "up"
    assert pkt.temporal == "4H"


def test_parse_con():
    pkt = parse_v3(PACKETS[2])
    assert pkt.id == "BEAR-7"
    assert pkt.operation == Operation.CON
    assert pkt.confidence == 72
    assert pkt.arg1 == "RE:BULL-3"
    assert "<-^whale_sell_44K" in pkt.arg2
    assert "down" in pkt.arg2


def test_parse_mrg():
    pkt = parse_v3(PACKETS[3])
    assert pkt.id == "SYNTH-1"
    assert pkt.operation == Operation.MRG
    assert pkt.arg1 == "RE:BULL-3+BEAR-7"
    assert pkt.arg2 == "^range_67K_69K"


def test_parse_yld():
    pkt = parse_v3(PACKETS[4])
    assert pkt.id == "BULL-3"
    assert pkt.operation == Operation.YLD
    assert pkt.confidence == 88
    assert pkt.arg1 == "from:up->range"
    assert pkt.arg2 == "RE:SYNTH-1"


def test_parse_prd():
    pkt = parse_v3(PACKETS[5])
    assert pkt.id == "SYNTH-1"
    assert pkt.operation == Operation.PRD
    assert pkt.confidence == 78
    assert pkt.arg1 == "^69200"
    assert pkt.arg2 == "<-^demand_hold+^fund_neg"


def test_parse_medical():
    pkt = parse_v3(PACKETS[6])
    assert pkt.id == "DR-CHEN"
    assert pkt.subject_tag == TagType.ENTITY
    assert pkt.subject_value == "dx.patient_47F"


def test_parse_genesis():
    pkt = parse_v3(PACKETS[7])
    assert pkt.id == "AGENT-7A3F"
    assert pkt.subject_tag == TagType.ENTITY
    assert pkt.subject_value == "axl.genesis"


# ── Emit tests ───────────────────────────────────────────

def test_emit_obs():
    pkt = parse_v3(PACKETS[0])
    result = emit_v3(pkt)
    assert result == PACKETS[0]


def test_emit_con():
    pkt = parse_v3(PACKETS[2])
    result = emit_v3(pkt)
    assert "ID:BEAR-7" in result
    assert "CON.72" in result
    assert "$BTC" in result
    assert "RE:BULL-3" in result


def test_emit_yld():
    pkt = parse_v3(PACKETS[4])
    result = emit_v3(pkt)
    assert result == PACKETS[4]


# ── Roundtrip tests ──────────────────────────────────────

def test_roundtrip():
    for raw in PACKETS:
        pkt = parse_v3(raw)
        emitted = emit_v3(pkt)
        reparsed = parse_v3(emitted)
        assert reparsed.id == pkt.id
        assert reparsed.operation == pkt.operation
        assert reparsed.confidence == pkt.confidence
        assert reparsed.subject_tag == pkt.subject_tag
        assert reparsed.subject_value == pkt.subject_value
        assert reparsed.temporal == pkt.temporal


def test_json_roundtrip():
    for raw in PACKETS:
        pkt = parse_v3(raw)
        j = v3_to_json(pkt)
        restored = v3_from_json(j)
        assert restored.id == pkt.id
        assert restored.operation == pkt.operation
        assert restored.confidence == pkt.confidence
        assert restored.subject_tag == pkt.subject_tag
        assert restored.subject_value == pkt.subject_value
        assert restored.temporal == pkt.temporal


# ── Validate tests ───────────────────────────────────────

def test_validate_valid_packets():
    for raw in PACKETS:
        pkt = parse_v3(raw)
        errors = validate_v3(pkt)
        assert errors == [], f"Unexpected errors for {raw}: {errors}"


def test_validate_bad_confidence():
    pkt = V3Packet(id="X", operation=Operation.OBS, confidence=100,
                   subject_tag=TagType.FINANCIAL, subject_value="BTC")
    errors = validate_v3(pkt)
    assert any("Confidence" in e for e in errors)


def test_validate_con_needs_re():
    pkt = V3Packet(id="X", operation=Operation.CON, confidence=50,
                   subject_tag=TagType.FINANCIAL, subject_value="BTC",
                   arg1="no_re_prefix")
    errors = validate_v3(pkt)
    assert any("RE:" in e for e in errors)


def test_validate_yld_needs_transition():
    pkt = V3Packet(id="X", operation=Operation.YLD, confidence=50,
                   subject_tag=TagType.FINANCIAL, subject_value="BTC",
                   arg1="RE:other", arg2="just_text")
    errors = validate_v3(pkt)
    assert any("from:" in e or "->" in e for e in errors)


# ── Auto-detect tests ───────────────────────────────────

def test_auto_detect_v3():
    for raw in PACKETS:
        assert detect_version(raw) == "v3", f"Failed to detect v3: {raw}"


def test_auto_detect_v1():
    v1 = "pi:5:0xS:.001|S:SIG.3|BTC|69200"
    assert detect_version(v1) == "v1"


def test_auto_detect_v1_sigma():
    v1 = "pi:5:0xS:.001|SSIG.3|BTC|69200"
    assert detect_version(v1) == "v1"


# ── Backward compat ──────────────────────────────────────

def test_v1_still_works():
    pkt = parse("pi:5:0xS:.001|S:SIG.3|BTC|69200|down|RSI|.64|SIG")
    assert pkt.domain == "SIG"
    assert pkt.tier == 3
    assert pkt.body.fields[0] == "BTC"


# ── Translate tests ──────────────────────────────────────

def test_translate_obs():
    pkt = parse_v3(PACKETS[0])
    eng = v3_to_english(pkt)
    assert "MKT-01" in eng
    assert "observes" in eng
    assert "99%" in eng


def test_translate_con():
    pkt = parse_v3(PACKETS[2])
    eng = v3_to_english(pkt)
    assert "BEAR-7" in eng
    assert "contradicts" in eng


def test_translate_prd():
    pkt = parse_v3(PACKETS[5])
    eng = v3_to_english(pkt)
    assert "SYNTH-1" in eng
    assert "predicts" in eng
    assert "78%" in eng

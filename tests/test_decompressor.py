"""Tests for the AXL decompressor."""
import pytest
from axl.decompressor import parse_packet, strip_kernel, v3_to_english, format_decompressed, decompress


def test_parse_obs_packet():
    r = parse_packet('ID:test|OBS.95|$.revenue|^3800000|NOW')
    assert r is not None
    assert r['op'] == 'OBS'
    assert r['cc'] == 95
    assert r['tag'] == '$'
    assert 'revenue' in r['tag_value']


def test_parse_inf_packet():
    r = parse_packet('ID:analyst|INF.80|@diagnosis|<-imaging+markers|~malignancy|1W')
    assert r is not None
    assert r['op'] == 'INF'
    assert r['cc'] == 80
    assert r['tag'] == '@'
    assert r['temp'] == '1W'


def test_parse_prd_packet():
    r = parse_packet('ID:forecast|PRD.70|$.BTC|^69200|<-demand+funding|4H')
    assert r is not None
    assert r['op'] == 'PRD'
    assert r['temp'] == '4H'


def test_parse_malformed():
    assert parse_packet('') is None
    assert parse_packet('random text') is None
    assert parse_packet('|||||') is None
    assert parse_packet('ID:test|BAD|no') is None
    assert parse_packet(None) is None


def test_v3_to_english_basic():
    text = 'ID:a|OBS.95|$.BTC|^67420|NOW\nID:b|INF.80|@market|<-funding|~bullish|4H\nID:c|PRD.70|$.BTC|^69200|NOW'
    claims = v3_to_english(text)
    assert len(claims) == 3
    assert claims[0]['op'] == 'OBS'
    assert claims[1]['op'] == 'INF'
    assert claims[2]['op'] == 'PRD'


def test_format_grouped():
    claims = [
        {'op': 'OBS', 'cc': 95, 'tag': '$', 'tag_value': 'BTC', 'claim_text': 'BTC is 67420 (95%)', 'temp': 'NOW', 'raw': ''},
        {'op': 'OBS', 'cc': 90, 'tag': '@', 'tag_value': 'market', 'claim_text': 'market is active (90%)', 'temp': 'NOW', 'raw': ''},
    ]
    result = format_decompressed(claims)
    assert '[Entity]' in result
    assert '[Financial]' in result
    assert 'BTC' in result


def test_strip_kernel():
    text = 'DIRECTIVE: blah\nAXL v3 stuff\n\n---PACKETS---\nID:x|OBS.99|$test|^val|NOW'
    stripped = strip_kernel(text)
    assert stripped.startswith('ID:x')
    assert 'DIRECTIVE' not in stripped


def test_strip_kernel_raw():
    text = 'ID:x|OBS.99|$test|^val|NOW\nID:y|INF.80|@z|^w|1H'
    assert strip_kernel(text) == text


def test_empty_input():
    assert v3_to_english('') == []
    assert format_decompressed([]) == 'No valid packets found.'
    assert decompress('') == 'No valid packets found.'


def test_decompress_convenience():
    text = 'ID:a|OBS.95|$.revenue|^3.8M|NOW'
    result = decompress(text)
    assert 'Financial' in result
    assert 'revenue' in result


def test_meta_fields():
    r = parse_packet('ID:test|OBS.95|$.revenue|^3800000|NOW')
    assert r is not None
    # Meta may or may not be present
    assert isinstance(r.get('meta', {}), dict)

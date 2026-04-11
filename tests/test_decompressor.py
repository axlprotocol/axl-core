"""Tests for the AXL decompressor v2.0."""
from axl.decompressor import (
    decompress,
    format_decompressed,
    parse_packet,
    strip_kernel,
    v3_to_english,
)


def test_parse_obs_packet():
    r = parse_packet('ID:test|OBS.95|$.revenue|^3800000|NOW')
    assert r is not None
    assert r['op'] == 'OBS'
    assert r['cc'] == 95
    assert r['tag'] == '$'
    assert 'revenue' in r['tag_value']


def test_parse_inf_packet():
    r = parse_packet(
        'ID:analyst|INF.80|@diagnosis|<-imaging+markers|~malignancy|1W'
    )
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
    text = (
        'ID:a|OBS.95|$.BTC||^amt:67420|NOW'
        '\nID:b|INF.80|@market|<-funding|~bullish|4H'
        '\nID:c|PRD.70|$.BTC||^amt:69200|NOW'
    )
    claims = v3_to_english(text)
    assert len(claims) == 3
    assert claims[0]['op'] == 'OBS'
    assert claims[1]['op'] == 'INF'
    assert claims[2]['op'] == 'PRD'


def test_format_grouped():
    claims = [
        {
            'op': 'OBS', 'cc': 95, 'tag': '$',
            'tag_value': 'BTC', 'base_subject': 'BTC',
            'aspect': None,
            'claim_text': 'BTC reported $67420.',
            'temp': 'NOW', 'raw': '', 'topic': 'Financial Performance',
        },
        {
            'op': 'OBS', 'cc': 90, 'tag': '@',
            'tag_value': 'market', 'base_subject': 'Market',
            'aspect': None,
            'claim_text': 'Market is described as active.',
            'temp': 'NOW', 'raw': '', 'topic': 'Market and Competition',
        },
    ]
    result = format_decompressed(claims)
    assert 'BTC' in result
    assert 'Market' in result


def test_strip_kernel():
    text = (
        'DIRECTIVE: blah\nAXL v3 stuff\n\n'
        '---PACKETS---\nID:x|OBS.99|$test|^val|NOW'
    )
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
    text = 'ID:a|OBS.95|$.revenue||^amt:3.8M|NOW'
    result = decompress(text)
    # Should mention revenue or the amount
    assert '3.8M' in result


def test_meta_fields():
    r = parse_packet('ID:test|OBS.95|$.revenue|^3800000|NOW')
    assert r is not None
    assert isinstance(r.get('meta', {}), dict)


def test_single_labelled_arg2_survives():
    packet = "ID:C|OBS.90|@company.revenue||^amt:5M+^date:2025|NOW"
    parsed = parse_packet(packet)
    assert parsed is not None
    # Raw arg2 preserved
    assert "5M" in (parsed["arg2"] or "")
    assert "2025" in (parsed["arg2"] or "")
    assert parsed["base_subject"] == "company"
    assert parsed["aspect"] == "revenue"


def test_hierarchical_subject_sections():
    text = "\n".join([
        "ID:C|OBS.90|@Sales_team.targets||^pct:30%|NOW",
        "ID:C|OBS.90|@Engineering.features||^count:5+~state:new|NOW",
        "ID:C|OBS.90|@Marketing.campaigns||^count:3|NOW",
    ])
    out = decompress(text)
    # Should produce readable output mentioning teams
    assert "Sales" in out
    assert "Engineering" in out or "engineering" in out
    assert "Marketing" in out or "marketing" in out
    assert "30%" in out
    assert "5" in out


def test_date_not_treated_as_meta_when_in_arg2_position():
    packet = "ID:C|PRD.75|^revenue||^amt:5M+^date:2025|NOW"
    parsed = parse_packet(packet)
    assert parsed is not None
    assert "5M" in (parsed["arg2"] or "")
    assert "2025" in (parsed["arg2"] or "")


def test_alias_expansion():
    text = "\n".join([
        "ID:axl-core|OBS.99|@m.O.doc||^df:CK=CloudKitchen+MC=Marcus|NOW",
        "ID:C|OBS.90|@CK||^rev:8.5M|NOW",
        "ID:C|PRD.70|@MC||^val:34M|NOW",
    ])
    out = decompress(text)
    assert "CloudKitchen" in out
    assert "Marcus" in out
    # Should NOT show raw aliases as headers
    assert "## CK\n" not in out
    assert "## MC\n" not in out


def test_manifest_filtered():
    text = "\n".join([
        "ID:axl-core|OBS.99|@m.O.doc||^df:CK=Test|NOW",
        "ID:axl-core|OBS.99|@m.B.compress|^mode:qa|^f:80|NOW",
        "ID:C|OBS.90|@CK||^rev:5M|NOW",
    ])
    out = decompress(text)
    # Manifests should not appear in output
    assert "m.O." not in out
    assert "m.B." not in out
    assert "Test" in out  # alias expanded


def test_empty_packets_suppressed():
    text = "ID:C|OBS.80|@company|||NOW"
    out = decompress(text)
    # Empty packet should produce nothing
    assert out == "No valid packets found." or "noted" not in out.lower()


def test_confidence_language():
    text = "\n".join([
        "ID:C|OBS.95|@high_conf||^rev:10M|NOW",
        "ID:C|PRD.65|@low_conf||^rev:1M|NOW",
    ])
    out = decompress(text)
    # Low confidence should have qualifier
    assert "estimated" in out.lower() or "possible" in out.lower()

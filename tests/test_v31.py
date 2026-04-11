"""Tests for AXL v3.1 Data Anchoring conventions."""
from axl.decompressor import decompress, parse_packet


def test_numeric_bundle_parsing():
    """label[value,qualifier] bundles should parse correctly."""
    pkt = parse_packet(
        'nv|OBS.99|$CK.rev.parts'
        '|tenant[$1.52M,40%];brands[$1.862M,49%];KitchenOS[$418K,11%]'
        '|<-$CK.rev.FY25|HIST'
    )
    assert pkt is not None
    assert pkt['op'] == 'OBS'
    assert pkt['cc'] == 99
    assert '$1.52M' in (pkt.get('arg1') or pkt.get('arg2') or '')


def test_entity_anchor_parsing():
    """@ent.XX should be recognized as entity anchor."""
    pkt = parse_packet(
        'nv|OBS.99|@ent.WTW|WokThisWay|$624K, 12 locations|HIST'
    )
    assert pkt is not None
    assert 'ent' in pkt['tag_value'] or 'WTW' in pkt['tag_value']


def test_causal_operator_in_arg2():
    """=> causal operator should survive parsing."""
    pkt = parse_packet(
        'nv|INF.85|!CK.margin'
        '|food_inflation[+8.2%] => menu_price[+4.5%] => margin[21.3%->15.8%]'
        '|Q1->Q4 2025|HIST'
    )
    assert pkt is not None
    assert pkt['op'] == 'INF'


def test_numeric_transition():
    """-> numeric transition should survive in values."""
    pkt = parse_packet(
        'nv|OBS.90|$margin||margin[21.3%->15.8%]|HIST'
    )
    assert pkt is not None
    assert '21.3%' in str(pkt.get('arg2', ''))


def test_summary_breakdown_pair():
    """Summary + breakdown packets should both parse."""
    summary = parse_packet(
        'nv|OBS.99|$CK.opex.FY25|$5.94M total, 7 categories|breakdown follows|HIST'
    )
    breakdown = parse_packet(
        'nv|OBS.99|$CK.opex.parts'
        '|facility[$1.68M,28.3%];food[$1.118M,18.8%]'
        '|<-$CK.opex.FY25|HIST'
    )
    assert summary is not None
    assert breakdown is not None
    assert 'breakdown' in str(summary.get('arg2', '')).lower()


def test_bakeoff_payload_all_parse():
    """All 22 packets from bakeoff payload should parse."""
    with open('/home/sudo-claude/bakeoff_payload_B.txt') as f:
        lines = [ln.strip() for ln in f if ln.strip()]

    parsed = 0
    failed = []
    for line in lines:
        result = parse_packet(line)
        if result:
            parsed += 1
        else:
            failed.append(line[:60])

    assert parsed == len(lines), (
        f'Only {parsed}/{len(lines)} parsed. '
        f'Failed: {failed}'
    )


def test_bakeoff_decompression():
    """Bakeoff payload should decompress without errors."""
    with open('/home/sudo-claude/bakeoff_payload_B.txt') as f:
        packets = f.read()
    result = decompress(packets)
    assert len(result) > 100
    # Should mention key entities
    assert any(w in result for w in [
        'tenant', 'brands', 'KitchenOS', 'facility',
        'revenue', 'cost', 'margin',
    ])


def test_backward_compat_v3():
    """Existing v3 packets must still parse."""
    v3_pkt = parse_packet(
        'ID:COMPRESS|OBS.90|@Sales_team||^targets:30%|NOW'
    )
    assert v3_pkt is not None
    assert v3_pkt['op'] == 'OBS'
    assert v3_pkt['cc'] == 90


def test_backward_compat_v3_decompress():
    """Existing v3 packets must still decompress."""
    text = 'ID:C|OBS.90|@Sales_team||^rev:8.5M+^val:34M|NOW'
    result = decompress(text)
    assert '8.5M' in result
    assert '34M' in result


def test_entity_anchor_decompression():
    """Entity anchors should expand in decompressed output."""
    packets = (
        'nv|OBS.99|@ent.WTW|WokThisWay|$624K, 12 locations|HIST\n'
        'nv|OBS.95|@ent.WTW||top brand|NOW'
    )
    result = decompress(packets)
    # Second mention should resolve
    assert 'WokThisWay' in result or 'WTW' in result

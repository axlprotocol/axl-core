"""AXL Decompressor: Deterministic packet-to-English pipeline.

No LLM dependency. Parses AXL v3 packets and produces structured English.

Functions:
- parse_packet(line) -> dict or None
- strip_kernel(text) -> str (packets only)
- v3_to_english(packets_text) -> list[dict]
- format_decompressed(claims) -> str
- decompress(text) -> str (convenience: strip + parse + format)
"""

from __future__ import annotations
import re
from typing import Optional


# Tag type display names
TAG_NAMES = {
    '$': 'Financial',
    '@': 'Entity',
    '#': 'Metric',
    '!': 'Event',
    '~': 'State',
    '^': 'Value',
}

# Operation templates for Step 1 (packet to claim)
OP_TEMPLATES = {
    'OBS': '{value} has {arg2} ({cc}% confidence)',
    'INF': 'Based on {arg1}, {value} {arg2} ({cc}% confidence)',
    'CON': '{value} contradicts {arg1}: {arg2} ({cc}% confidence)',
    'MRG': 'Synthesizing {arg1}: {value} {arg2} ({cc}% confidence)',
    'SEK': 'Information needed: {value} {arg2}',
    'YLD': '{value} changed: {arg2} because {arg1} ({cc}% confidence)',
    'PRD': '{value} predicted: {arg2} within {temp} ({cc}% confidence)',
}


def parse_packet(line: str) -> Optional[dict]:
    """Parse a single AXL v3 packet line into a dict.

    Returns dict with keys: id, op, cc, tag, tag_value, arg1, arg2, temp, meta
    Returns None if the line is not a valid packet.
    """
    if not line or not isinstance(line, str):
        return None

    line = line.strip()
    if not line:
        return None

    try:
        parts = line.split('|')
        if len(parts) < 3:
            return None

        # Field 0: ID
        raw_id = parts[0].strip()
        if raw_id.startswith('ID:'):
            raw_id = raw_id[3:]
        agent_id = raw_id

        # Field 1: OP.CC
        op_cc = parts[1].strip()
        dot = op_cc.find('.')
        if dot < 0:
            return None
        op = op_cc[:dot].upper()
        if op not in ('OBS', 'INF', 'CON', 'MRG', 'SEK', 'YLD', 'PRD'):
            return None
        try:
            cc = int(op_cc[dot + 1:])
        except ValueError:
            cc = 50

        # Field 2: SUBJ (TAG.value)
        subj = parts[2].strip() if len(parts) > 2 else ''
        tag = '^'  # default
        tag_value = subj
        if subj and subj[0] in TAG_NAMES:
            tag = subj[0]
            tag_value = subj[1:].lstrip('.')

        # Clean tag value: replace underscores with spaces
        tag_value = tag_value.replace('_', ' ').strip()

        # Remaining fields: ARG1, ARG2, TEMP, META
        # Scan remaining parts, identify temporal and meta
        remaining = [p.strip() for p in parts[3:]]

        VALID_TEMPS = {'NOW', '1H', '4H', '1D', '1W', '1M', 'HIST'}

        arg1 = None
        arg2 = None
        temp = 'NOW'
        meta = {}

        positional = []
        for field in remaining:
            # Check if it's a meta field (^key:value with no + compound)
            if field.startswith('^') and ':' in field[1:] and '+' not in field and len(field.split(':')[0]) < 12:
                # Could be meta or a value arg
                # If it looks like a standalone key:value pair, treat as meta
                bracket_match = re.match(r'\[?\^(\w+):(.+?)\]?$', field)
                if bracket_match:
                    meta[bracket_match.group(1)] = bracket_match.group(2)
                    continue

            # Check if it's a temporal
            if field in VALID_TEMPS:
                temp = field
                continue

            positional.append(field)

        if len(positional) >= 1:
            arg1 = positional[0]
        if len(positional) >= 2:
            arg2 = positional[1]
        if len(positional) > 2:
            # Extra positional fields, join into arg2
            arg2 = '|'.join(positional[1:])

        # Clean args: expand labeled values for natural English
        def clean_arg(a):
            if not a:
                return ''
            a = re.sub(r'^<-', '', a)
            a = re.sub(r'^RE:', 'references ', a)
            # Expand labeled values: ^key:value or ~key:value
            parts = a.split('+')
            expanded = []
            for part in parts:
                part = part.strip()
                # Remove tag prefixes for display
                clean_part = re.sub(r'^[\^~\$@#!]', '', part)
                if ':' in clean_part:
                    key, val = clean_part.split(':', 1)
                    key = key.replace('_', ' ')
                    val = val.replace('_', ' ')
                    expanded.append(f"{key}: {val}")
                else:
                    clean_part = clean_part.replace('_', ' ')
                    expanded.append(clean_part)
            return ', '.join(expanded).strip()

        return {
            'id': agent_id,
            'op': op,
            'cc': cc,
            'tag': tag,
            'tag_value': tag_value,
            'arg1': clean_arg(arg1),
            'arg2': clean_arg(arg2),
            'temp': temp,
            'meta': meta,
            'raw': line,
        }

    except Exception:
        return None


def strip_kernel(text: str) -> str:
    """Strip the Rosetta v3 kernel from compressed output, returning only packets.

    Handles:
    - Text with ---PACKETS--- marker
    - Text starting with DIRECTIVE: or AXL v3
    - Raw packets (returned as-is)
    """
    if not text or not isinstance(text, str):
        return ''

    # Check for ---PACKETS--- marker
    marker = '---PACKETS---'
    idx = text.find(marker)
    if idx >= 0:
        return text[idx + len(marker):].strip()

    # Check for DIRECTIVE or AXL v3 header, find first packet line
    lines = text.split('\n')
    for i, line in enumerate(lines):
        line = line.strip()
        if line.startswith('ID:') and '|' in line:
            return '\n'.join(lines[i:])

    # Return as-is (assume raw packets)
    return text.strip()


def v3_to_english(packets_text: str) -> list[dict]:
    """Convert AXL v3 packets to English claims.

    Step 1 of the decompression pipeline: each packet becomes one claim.

    Args:
        packets_text: Raw packet text (may include kernel, will be stripped)

    Returns:
        List of claim dicts with keys: op, cc, tag, value, claim_text, temp, raw
    """
    text = strip_kernel(packets_text)
    if not text:
        return []

    claims = []
    for line in text.split('\n'):
        line = line.strip()
        if not line:
            continue

        parsed = parse_packet(line)
        if not parsed:
            continue

        # Apply template
        template = OP_TEMPLATES.get(parsed['op'], '{value} {arg2} ({cc}% confidence)')

        try:
            claim_text = template.format(
                value=parsed['tag_value'] or 'unknown',
                arg1=parsed['arg1'] or '',
                arg2=parsed['arg2'] or '',
                cc=parsed['cc'],
                temp=parsed['temp'],
            )
        except (KeyError, IndexError):
            claim_text = f"{parsed['tag_value']} ({parsed['cc']}% confidence)"

        # Clean up empty parts
        claim_text = re.sub(r'\s+', ' ', claim_text).strip()
        claim_text = claim_text.replace('  ', ' ')
        claim_text = claim_text.replace('has  (', 'noted (')
        claim_text = claim_text.replace('contradicts :', 'contradicts:')
        claim_text = claim_text.replace('Synthesizing :', 'Synthesis:')
        claim_text = claim_text.replace('changed:  because', 'changed because')
        claim_text = claim_text.replace('predicted:  within', 'predicted within')

        claims.append({
            'op': parsed['op'],
            'cc': parsed['cc'],
            'tag': parsed['tag'],
            'tag_value': parsed['tag_value'],
            'claim_text': claim_text,
            'temp': parsed['temp'],
            'raw': parsed['raw'],
        })

    return claims


def format_decompressed(claims: list[dict]) -> str:
    """Format claims into grouped, structured English.

    Step 2-3 of the decompression pipeline:
    - Group by tag type
    - Sort by confidence descending
    - Format as readable sections
    """
    if not claims:
        return 'No valid packets found.'

    # Group by tag
    groups = {}
    for claim in claims:
        tag = claim.get('tag', '^')
        if tag not in groups:
            groups[tag] = []
        groups[tag].append(claim)

    # Sort each group by confidence descending
    for tag in groups:
        groups[tag].sort(key=lambda x: x.get('cc', 0), reverse=True)

    # Format
    sections = []

    # Order: @ entity first, $ financial, # metric, ! event, ~ state, ^ value
    tag_order = ['@', '$', '#', '!', '~', '^']

    for tag in tag_order:
        if tag not in groups:
            continue
        name = TAG_NAMES.get(tag, 'Other')
        lines = []
        for claim in groups[tag]:
            lines.append(f"  - {claim['claim_text']}")
        sections.append(f"[{name}]\n" + '\n'.join(lines))

    # Any tags not in our order
    for tag in groups:
        if tag not in tag_order:
            name = TAG_NAMES.get(tag, 'Other')
            lines = [f"  - {c['claim_text']}" for c in groups[tag]]
            sections.append(f"[{name}]\n" + '\n'.join(lines))

    return '\n\n'.join(sections)


def decompress(text: str) -> str:
    """Convenience function: strip kernel, parse packets, format output.

    Args:
        text: Raw compressed output (may include kernel + packets)

    Returns:
        Formatted English text grouped by subject tag
    """
    claims = v3_to_english(text)
    return format_decompressed(claims)

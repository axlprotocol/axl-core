"""Validate AXL packets — good and bad."""

from axl import parse, validate

# Good packet
good = parse("π:5:0xS:.001|S:SIG.3|BTC|69200|↓|RSI|.64|SIG")
result = validate(good)
print(f"Good packet: valid={result.valid}, errors={len(result.errors)}, warnings={len(result.warnings)}")

# Bad packet — confidence out of range, invalid direction
bad = parse("π:1:0xS:.001|S:SIG.3|BTC|69200|WRONG|RSI|5.0|SIG")
result = validate(bad)
print(f"Bad packet: valid={result.valid}, errors={len(result.errors)}, warnings={len(result.warnings)}")
for w in result.warnings:
    print(f"  {w.severity}: {w.field_name} — {w.message}")

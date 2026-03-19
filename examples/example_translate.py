"""Parse a packet and translate it to English and JSON."""

import json
from axl import parse
from axl.translator import to_english, to_json

raw = "π:5:0xS:.001|S:SIG.3|BTC|69200|↓|RSI|.64|SIG"
packet = parse(raw)

print("English:")
print(to_english(packet))
print()

print("JSON:")
print(json.dumps(to_json(packet), indent=2))

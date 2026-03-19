"""Parse an AXL packet string and inspect its components."""

from axl import parse

raw = "π:5:0xS:.001|S:SIG.3|BTC|69200|↓|RSI|.64|SIG"
packet = parse(raw)

print(f"Domain: {packet.domain}")
print(f"Tier: {packet.tier}")
print(f"Agent: {packet.agent_id}")
print(f"Fields: {packet.body.fields}")
print(f"Flags: {packet.flags}")
print(f"Gas: {packet.preamble.payment.gas}")

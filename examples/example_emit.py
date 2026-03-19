"""Build a Packet programmatically and emit it as an AXL string."""

from axl import emit, Packet, Preamble, Body, PaymentProof

packet = Packet(
    preamble=Preamble(
        payment=PaymentProof(agent_id="AXL-00000008", signature="0xPM", gas=0.01),
    ),
    body=Body(
        domain="PAY",
        tier=1,
        fields=["AXL-00000001", "0.02", "USDC", "local", "crawl_task_completed"],
    ),
    flags=["LOG"],
)

print(emit(packet))
# Output: π:AXL-00000008:0xPM:0.01|S:PAY.1|AXL-00000001|0.02|USDC|local|crawl_task_completed|LOG

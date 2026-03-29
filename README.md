<p align="center">
  <img src="assets/banner.png" alt="AXL Protocol" width="600">
</p>

<h3 align="center">The universal language for AI agents</h3>

<p align="center">
  <em>75 lines teach any LLM to speak it. 10.41x compression. 100% parse validity. Zero dependencies.</em>
</p>

<p align="center">
  <a href="https://github.com/AXLPROTOCOL/axl-core/actions/workflows/ci.yml"><img src="https://github.com/AXLPROTOCOL/axl-core/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="https://pypi.org/project/axl-core/"><img src="https://img.shields.io/pypi/v/axl-core.svg" alt="PyPI"></a>
  <a href="https://pypi.org/project/axl-core/"><img src="https://img.shields.io/pypi/pyversions/axl-core.svg" alt="Python"></a>
  <a href="https://opensource.org/licenses/Apache-2.0"><img src="https://img.shields.io/badge/License-Apache_2.0-blue.svg" alt="License"></a>
  <a href="https://pypi.org/project/axl-core/"><img src="https://img.shields.io/pypi/dm/axl-core.svg" alt="Downloads"></a>
</p>

<p align="center">
  <a href="https://axlprotocol.org/whitepaper/">Whitepaper</a> ·
  <a href="https://axlprotocol.org/rosetta">Rosetta</a> ·
  <a href="https://lang.axlprotocol.org">Documentation</a> ·
  <a href="https://axlprotocol.org/results/v2/">Experiments</a> ·
  <a href="https://axlprotocol.org">Website</a>
</p>

---

## What is AXL?

AI agents can't talk to each other. They communicate in English prose (50-100 tokens), JSON (even worse), or proprietary formats requiring per-framework SDKs. In a 100-agent network, this produces **22.5 million tokens** of negotiation overhead before any productive work happens.

AXL eliminates this. One URL (`@axlprotocol.org/rosetta`) teaches any agent the complete language on first contact. The protocol has been validated across **11 agents from 10 computational paradigms** with **100% parse validity** and **95.8% LLM comprehension** across four major architectures.

## Install

```bash
pip install axl-core
```

## Quick Start

**Parse a packet:**

```python
from axl import parse

packet = parse("π:5:0xSIG:0.001|S:OPS.4|@api.example.com|ERR500|latency|4500ms|500ms|ALERT|URG|LOG")
print(packet.domain)         # "OPS"
print(packet.body.fields)    # ['@api.example.com', 'ERR500', 'latency', '4500ms', '500ms', 'ALERT']
print(packet.flags)          # ['URG', 'LOG']
```

**Emit a packet:**

```python
from axl import emit, Packet, Preamble, Body, PaymentProof

packet = Packet(
    preamble=Preamble(payment=PaymentProof(agent_id="5", signature="0xSIG", gas=0.001)),
    body=Body(domain="OPS", tier=4, fields=["@api.example.com", "ERR500", "latency", "4500ms", "500ms", "ALERT"]),
    flags=["URG", "LOG"]
)
print(emit(packet))
# π:5:0xSIG:0.001|S:OPS.4|@api.example.com|ERR500|latency|4500ms|500ms|ALERT|URG|LOG
```

**CLI:**

```bash
axl parse "π:5:0xSIG:0.001|S:SIG.3|BTC|69200|↓|RSI|.64|SIG"
axl validate "π:5:0xSIG:0.001|S:SIG.3|BTC|69200|↓|RSI|.64|SIG"
axl translate --to english "π:5:0xSIG:0.001|S:SIG.3|BTC|69200|↓|RSI|.64|SIG"
```

## Domains

| Domain | Purpose | Example |
|--------|---------|---------|
| `OPS` | Infrastructure & operations | Server down, latency spike, disk full |
| `SEC` | Security & threat detection | Theft detected, balance discrepancy |
| `DEV` | Development & code lifecycle | PR merged, build failed, review needed |
| `RES` | Research & analysis | Cross-domain correlation, market analysis |
| `SIG` | Signal broadcast | BTC falling, RSI divergence |
| `COMM` | Communication & routing | Request, ACK, status update |
| `TRD` | Trading & economic action | Short BTC, 2x leverage, 2% max risk |
| `PAY` | Payment transfer | Pay agent $0.02 USDC for crawl task |
| `FUND` | Funding request | Request $5 for infrastructure costs |
| `REG` | Registration & identity | New agent joins the network |

## The Stack

AXL is the missing language layer in the agent internet:

| Layer | Protocol | Who |
|-------|----------|-----|
| Payment | x402 | Coinbase / Cloudflare |
| Tool Calling | MCP | Anthropic |
| Discovery | A2A | Google |
| Social | Moltbook | Meta |
| **Language** | **AXL** | **AXLPROTOCOL INC** |

## Proven

Two live experiments. Real agents. Real packets. Real results.

| Metric | Result |
|--------|--------|
| Total packets | 1,502 |
| Parse validity | 100% |
| Agents tested | 11 (10 paradigms) |
| Domains active | 9 |
| LLM comprehension | 95.8% (4 models, first read) |
| Agent-to-agent payments | 38 |
| Compression vs English | 1.3-3x per message, 71x network |

## Architecture

- **Parser**: `parse(string)` -> Packet dataclass
- **Emitter**: `emit(Packet)` -> AXL string (round-trip proven)
- **Validator**: Schema check, type check, tier range
- **Translator**: AXL <-> English <-> JSON
- **CLI**: `axl parse`, `axl emit`, `axl validate`, `axl translate`
- **Zero runtime dependencies**

## Parser Status

axl-core 0.4.x includes a v1 format parser.
Full v3 parser, emitter, validator, and translator ship in 0.5.0.
The v3 kernel is included at `rosetta/v3.md` and live at [axlprotocol.org/v3](https://axlprotocol.org/v3).

Quick v3 parse (positional split):

```python
fields = packet.split("|")
# fields[0]=ID, fields[1]=OP.CC, fields[2]=SUBJ,
# fields[3]=ARG1, fields[4]=ARG2, fields[5]=TEMP
```

## Links

- [Whitepaper](https://axlprotocol.org/whitepaper/) - 14 sections, 5 appendices, every number measured
- [The Rosetta v3](https://axlprotocol.org/v3) - 75 lines, the compressed kernel
- [Evolution](https://lang.axlprotocol.org) - From 300 lines to 75, the full narrative
- [Battleground v2 Results](https://axlprotocol.org/results/v2/) - Full experiment data
- [Terminal Recording](https://axlprotocol.org/terminal/) - Watch the agents run

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

Apache 2.0 - [AXLPROTOCOL INC](https://axlprotocol.org) · Diego Carranza · 2026

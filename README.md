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
  <a href="https://axlprotocol.org">Website</a> ·
  <a href="https://compress.axlprotocol.org">Live Tool</a> ·
  <a href="https://axlprotocol.org/v3">Protocol Spec</a> ·
  <a href="https://docs.axlprotocol.org">Full Docs</a>
</p>

---

## What is AXL?

AI agents can't talk to each other. They communicate in English prose (50-100 tokens), JSON (even worse), or proprietary formats requiring per-framework SDKs. In a 100-agent network, this produces **22.5 million tokens** of negotiation overhead before any productive work happens.

AXL eliminates this. One URL (`@axlprotocol.org/rosetta`) teaches any agent the complete language on first contact. The protocol has been validated across **11 agents from 10 computational paradigms** with **100% parse validity** and **95.8% LLM comprehension** across four major architectures.

## How It Works

AXL compresses English prose into structured semantic packets using a 75-line grammar (the Rosetta v3 kernel) that any LLM can parse on first read. It is designed for AI agents, NLP pipelines, and machine communication systems that need deterministic, low-latency semantic compression without sacrificing human readability.

### Two Ways to Compress

| Method | Speed | Cost | When to Use |
|--------|-------|------|-------------|
| **Fixed Engine** (`axl-core`) | <100ms | Free | Automation, bulk processing, MCP tools |
| **LLM Engine** (any model + kernel) | 2-10s | Token cost | Maximum fidelity, complex documents |

### Two Ways to Decompress

| Method | Speed | Cost | Output |
|--------|-------|------|--------|
| **Receipt Mode** (`axl-core`) | 0.3ms | Free | Structured claims (machine-readable) |
| **LLM Mode** (any model + packets) | 5-30s | Token cost | Full English prose (human-readable) |

### Example

**Input** (English):
> Sales team at CloudKitchen exceeded quarterly revenue targets by 30% in Q1 2025, driven by expansion into 3 new markets.

**Output** (AXL v3):
```
ID:C|OBS.90|@CK.sales|<-expand:3_mkts|^rev:+30%+^date:Q1_2025|NOW
```

**Decompressed** (Receipt Mode):
> [CloudKitchen] sales: revenue +30%, Q1 2025 (90% confidence)

**Decompressed** (LLM Mode - Grok):
> CloudKitchen's sales team exceeded their quarterly revenue targets by 30% in Q1 2025. This growth was primarily driven by the company's expansion into three new metropolitan markets.

---

## Install

```bash
pip install axl-core
```

## Quick Start

**Compress English to AXL packets:**

```python
from axl.compressor import compress, english_to_v3
from axl.decompressor import decompress
from axl.emitter import emit_v3

# Compress English prose to AXL v3 semantic packets
text = "Revenue grew 30% because the company expanded into 3 new markets."
packets = english_to_v3(text)
for p in packets:
    print(emit_v3(p))

# Decompress back to structured English (receipt mode - free, <1ms)
compressed = compress(text, kernel_mode="mini")
result = decompress(compressed)
print(result)
```

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
| Payment | HTTP 402 | W3C (reserved since 1997, free fallback default) |
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

## v3 Support

Full v3 parser, emitter, validator, and translator included.
Auto-detects v1 vs v3 format. All v1 code preserved for backward compatibility.

```python
from axl import parse_v3, emit_v3, validate_v3, v3_to_json, v3_to_english

pkt = parse_v3("ID:MKT-01|OBS.99|$BTC|^67420|^fund:-0.02%+^OI:12.4B|NOW")
print(pkt.operation)      # Operation.OBS
print(pkt.confidence)     # 99
print(pkt.subject_value)  # BTC

print(emit_v3(pkt))       # ID:MKT-01|OBS.99|$BTC|^67420|^fund:-0.02%+^OI:12.4B|NOW
print(v3_to_english(pkt)) # MKT-01 observes $BTC at ^67420 with 99% confidence.
print(v3_to_json(pkt))    # {"v":"3","id":"MKT-01","op":"OBS","cc":99,...}
print(validate_v3(pkt))   # [] (no errors)
```

## Cross-Architecture Validation

The Rosetta v3 kernel has been tested on 7 LLM architectures with 97%+ comprehension on first exposure. No fine-tuning. No examples. One URL, any agent.

| Model | Architecture | Result |
|-------|-------------|--------|
| Grok 3 | xAI | 97.2% - spontaneously emitted genesis packet |
| GPT-4.5 | OpenAI | 97.2% - self-issued loss contract |
| Claude Sonnet 4 | Anthropic | Full swarm test |
| Gemini | Google | 100% |
| Llama 4 | Meta | 97.2% |
| Qwen 3.5 | Alibaba | 91.7% |
| Devstral | Mistral | 100% |

This is the core value proposition: a semantic compression protocol for AI agents that is architecture-agnostic, LLM-native, and requires zero pre-training. Any model that can read English can speak AXL after a single context injection.

---

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

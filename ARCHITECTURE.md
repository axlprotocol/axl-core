# AXL Protocol Architecture

## How AXL Works

AXL compresses English prose into structured semantic packets, then decompresses them back.
There are two compression paths and two decompression paths.

## The Dual-Engine Design

```
                    COMPRESS                              DECOMPRESS
                    --------                              ----------

English Prose --+                          AXL Packets --+
                |                                        |
                v                                        v
        [Fixed Engine]                           [Receipt Mode]
        spaCy NLP                                Template expansion
        Deterministic                            0.3ms, FREE
        No LLM needed                            Deterministic
        axl-core library                         Structured claims
                |                                        |
                v                                        v
          AXL v3 Packets                         Structured Output
                                                 (machine-readable)

English Prose --+                          AXL Packets --+
                |                                        |
                v                                        v
          [LLM Engine]                            [LLM Engine]
          Any LLM reads the                       Any LLM reads packets
          Rosetta v3 kernel                       + kernel and produces
          and compresses                          full English prose
          using the grammar                       (Grok: 17s for full memo)
                |                                        |
                v                                        v
          AXL v3 Packets                         English Prose
                                                 (human-readable)
```

## When to Use Which

| Path | Speed | Cost | Quality | Use When |
|------|-------|------|---------|----------|
| Fixed Compress | <100ms | Free | Good (v0.9.0+) | Bulk processing, automation, MCP tools |
| LLM Compress | 2-10s | Token cost | Excellent | Maximum fidelity, complex documents |
| Receipt Decompress | 0.3ms | Free | Structured claims | Machine consumption, routing, APIs |
| LLM Decompress | 5-30s | Token cost | Full prose | Human reading, reports, briefings |

## Packet Format

Every AXL v3 packet follows this grammar:

```
ID | OP.CC | SUBJ | ARG1 | ARG2 | TEMP [META]
```

- **ID**: Agent identifier (e.g., "C" for compressor)
- **OP.CC**: Operation (OBS/INF/CON/MRG/SEK/YLD/PRD) + confidence 00-99
- **SUBJ**: TAG.value where TAG is one of: $ @ # ! ~ ^
- **ARG1**: Evidence reference (<-cause) or cross-reference (RE:agent)
- **ARG2**: Extracted values (^label:value+^label:value)
- **TEMP**: Temporal scope (NOW/1H/4H/1D/1W/1M/HIST)

Example:
```
ID:C|OBS.90|@CK.sales|<-expand:3_markets|^rev:+30%+^date:Q1_2025|NOW
```
Reads: "Agent C observes CloudKitchen sales, based on expansion into 3 markets, revenue up 30% in Q1 2025, as of now, with 90% confidence."

## The Rosetta v3 Kernel

The kernel is a 75-line grammar specification that any LLM can parse on first read.
7 architectures validated at 97%+ comprehension: Grok, GPT, Claude, Gemini, Qwen, Llama, Mistral.

The kernel is self-bootstrapping: compressed output includes a mini kernel (376 chars) so any receiving LLM can parse without prior knowledge.

Full kernel: https://axlprotocol.org/v3

## Compression Pipeline (Fixed Engine)

```
English Text
    |
    v
[1. Sentence Splitting] -- spaCy sentence boundary detection
    |
    v
[2. Entity Registry] -- scan full document, assign 2-3 char aliases
    |                    CloudKitchen -> CK, Marcus Chen -> MC
    v
[3. NER Extraction] -- spaCy named entity recognition
    |                   PERSON, ORG, GPE, MONEY, PERCENT, DATE, etc.
    v
[4. Operation Classification] -- regex pattern matching
    |                            OBS/INF/CON/MRG/SEK/YLD/PRD
    v
[5. Confidence Scoring] -- operation-aware base + hedging dictionary
    |
    v
[6. Subject Extraction] -- semantic ranking: ORG > PERSON > numbers
    |                      pronoun rejection, entity aliasing
    v
[7. Evidence Extraction] -- causal patterns + spaCy dependency tree
    |                       compressed to verb:object notation
    v
[8. Value Packing] -- all values from sentence packed into one ARG2
    |                  role-labeled: ^rev:8.5M not ^amt:8.5M
    v
[9. Same-Subject Merging] -- adjacent packets with same key merged
    |
    v
[10. Manifest Emission] -- ontology (entity registry) + bundle (loss contract)
    |
    v
AXL v3 Packets
```

## Decompression Pipeline (Receipt Mode)

```
AXL v3 Packets (may include kernel)
    |
    v
[1. Strip Kernel] -- remove Rosetta preamble, find ---PACKETS--- marker
    |
    v
[2. Parse Packets] -- split by pipe, extract fields positionally
    |
    v
[3. Extract Ontology] -- find @m.O.doc manifest, build alias map
    |                     CK -> CloudKitchen, MC -> Marcus Chen
    v
[4. Expand Aliases] -- replace aliases in all packet subjects
    |
    v
[5. Apply Templates] -- operation-specific claim text
    |                    OBS: "{subject} has {values} ({cc}%)"
    |                    INF: "Based on {evidence}, {subject} {values}"
    v
[6. Group by Subject] -- semantic grouping (tag + value), not tag alone
    |
    v
[7. Sort by Confidence] -- highest confidence claims first per group
    |
    v
Structured English Output
```

## Loss Contract

Every compressed bundle includes a manifest packet declaring what was preserved and what was lost:

```
^mode   gist | qa | audit | legal | code | research | plan
^keep   entities | numbers | causality | confidence | temporal
^loss   rhetoric | formatting | redundancy | hedging | style
^f      fidelity score 0-100
^fm     fidelity method identifier
```

A bundle missing a valid loss contract MUST be treated as mode:gist (not safe for audit, legal, or compliance).

## File Structure

```
axl-core/
  src/axl/
    __init__.py      -- package root, version, public API
    models.py        -- Operation, TagType, V3Packet dataclasses
    parser.py        -- parse() and parse_v3() packet parsers
    emitter.py       -- emit() and emit_v3() packet formatters
    validator.py     -- validate() and validate_v3() packet validators
    translator.py    -- v3_to_english() packet-to-prose translator
    compressor.py    -- compress() and english_to_v3() English-to-AXL
    decompressor.py  -- decompress() and v3_to_english() AXL-to-English
    schemas.py       -- domain schemas for v1 validation
    cli.py           -- axl command-line interface
  rosetta/
    v3.md            -- Rosetta v3 kernel (75 lines)
  tests/             -- 80 tests
  ARCHITECTURE.md    -- this file
  CHANGELOG.md       -- version history
  SECURITY.md        -- security policy
```

## Related Services

| Service | URL | What |
|---------|-----|------|
| Protocol website | axlprotocol.org | Landing, kernel, papers |
| Compress tool | compress.axlprotocol.org | Web UI for compression |
| Bridge | bridge.axlprotocol.org | Packet bus (FastAPI + Redis) |
| Documentation | docs.axlprotocol.org | Mintlify docs (36 pages) |
| Project Ark | ark.axlprotocol.org | Hardware sovereignty |

## License

Apache 2.0 - AXL Protocol Inc.

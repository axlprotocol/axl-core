## 0.9.0 (2026-04-10)

- Architecture: two-pass compression pipeline (document scan then packed emission)
- Entity registry: named entities get 2-3 char aliases (CloudKitchen -> CK, Marcus Chen -> MC)
- Ontology manifest: entity->alias mappings emitted as @m.O.doc packet
- Compressed subjects: registered entities aliased, non-entities preserved readable
- Compressed evidence: verb:object notation, max 30 chars (was 80+ chars verbatim)
- Short agent ID: "C" instead of "COMPRESS" (10 chars saved per packet)
- Same-subject merging: adjacent packets with matching key merged into one
- Mini kernel: 376 chars (was 5,853 full kernel, was 958 in v0.8.1)
- kernel_mode parameter: "mini" (default) or "full" on compress()
- Decompressor: ontology alias expansion (aliases -> full names in output)
- Decompressor: manifest packets filtered from decompressed output
- Abbreviation dictionary for role labels (revenue -> rev, technology -> tech)
- Ratio improved from 1.06x to 1.57x on 4.3K sample (mini kernel)
- 80 tests passing
- Reverted from atomic-splitting approach (v0.8.x) to one-packet-per-sentence with packing

## 0.8.0 (2026-04-09)

- Compressor: DATE/year guard prevents year compaction (2025 no longer becomes 2.0K)
- Compressor: word-scale normalization (5 million dollars -> 5M)
- Compressor: pronoun subject rejection (I, it, they no longer used as subjects)
- Compressor: semantic subject ranking (organizations and teams outrank numeric entities)
- Compressor: atomic fact splitting (complex sentences emit multiple coordinated packets)
- Compressor: safer evidence extraction fallback (generic prepositions no longer treated as causal)
- Compressor: synthetic MRG generation disabled (was emitting invalid RE: targets)
- Compressor: include_kernel parameter controls kernel prepend on compress()
- Compressor: fidelity method renamed to axl-fidelity/v0.8.0-heuristic for honesty
- Decompressor: positional field parsing (single ^key:value ARG2 no longer misclassified as META)
- Decompressor: groups by semantic subject (tag + value), not tag alone
- Decompressor: dotted hierarchy support (@company.revenue -> [company] section with revenue bullet)
- Decompressor: improved claim templates per operation type
- Kernel: recommended Step 2 wording change (group by semantic subject, not SUBJ tag alone)
- External code review by GPT-4 identified 7 bugs (4 known, 3 silent), all addressed
- Patches merged from compressor_v080.py, decompressor_v080.py, test_decompressor_v080.py

## 0.7.0 (2026-04-08)

- Deterministic decompressor: v3_to_english(), format_decompressed(), parse_packet(), strip_kernel()
- Receipt mode decompression: 0.3ms, no LLM, deterministic
- CLI: axl decompress <file> and axl decompress --raw <file>
- Compressor: evidence extraction rewritten with 4 pattern groups + spaCy dependency tree
- Compressor: confidence scoring rewritten with operation-aware base scores + 23-word hedging dictionary
- Compressor: bundle manifest (loss contract) appended to every output
- Compressor: NER value prefix map (amt/pct/count/qty/date)
- Compressor: qualitative state extraction from ADJ tokens
- Compressor: word boundary truncation helper
- 77 tests passing

## 0.6.1 (2026-04-07)

- Self-bootstrapping kernel prepend: every compression output starts with Rosetta v3 kernel + ---PACKETS--- separator
- Any receiving LLM can parse output without prior configuration

## 0.6.0 (2026-04-07)

- english_to_v3(): deterministic English-to-AXL compression, no LLM dependency
- 7-step spaCy NLP pipeline: sentence split, NER, operation classification, confidence scoring, temporal extraction, evidence linking, packet emission
- Published to PyPI as axl-core 0.6.0

## 0.5.0 (2026-03-29)

- Full v3 parser, emitter, validator, translator
- v3 Rosetta kernel included (rosetta/v3.md)
- Auto-detection of v1 vs v3 packet format
- JSON lowering (application/vnd.axl+json)
- Backward compatible with v1 packets
- Whitepaper updated to v7

## 0.4.1 (2026-03-29)

- Documentation updated for v3
- Corrected compression claims (10.41x)
- Added Rosetta v3 kernel reference

## 0.4.0 (2026-03-19)

- Initial release of axl-core with full protocol implementation
- Parser: convert raw AXL pipe-delimited strings into Packet dataclasses
- Emitter: serialize Packet objects back to AXL wire format
- Validator: validate packets against domain schemas with warnings and errors
- Translator: convert packets to English prose or structured JSON, and back
- CLI: axl command with parse, validate, translate, emit, and version subcommands
- All 10 Rosetta domains: TRD, SIG, COMM, OPS, SEC, DEV, RES, REG, PAY, FUND
- Zero external dependencies for core library; dev extras for pytest, ruff, mypy
- GitHub Actions CI for Python 3.10, 3.11, 3.12

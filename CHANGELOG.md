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

- Initial release of `axl-core` with full protocol implementation.
- Parser: convert raw AXL pipe-delimited strings into `Packet` dataclasses.
- Emitter: serialize `Packet` objects back to AXL wire format.
- Validator: validate packets against domain schemas with warnings and errors.
- Translator: convert packets to English prose or structured JSON, and back.
- CLI: `axl` command with parse, validate, translate, emit, and version subcommands.
- All 10 Rosetta domains: TRD, SIG, COMM, OPS, SEC, DEV, RES, REG, PAY, FUND.
- Zero external dependencies for core library; dev extras for pytest, ruff, mypy.
- GitHub Actions CI for Python 3.10, 3.11, 3.12.

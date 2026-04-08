"""AXL command-line interface — argparse-based, zero external deps.

Entry point: ``axl`` (defined in pyproject.toml [project.scripts]).
"""

from __future__ import annotations

import argparse
import json
import sys


def _do_parse(args: argparse.Namespace) -> None:
    from axl.parser import detect_version, parse, parse_v3

    version = detect_version(args.packet)
    if version == "v3":
        pkt = parse_v3(args.packet)
        print(f"Version: v3")
        print(f"ID     : {pkt.id}")
        print(f"Op     : {pkt.operation.value}.{pkt.confidence:02d}")
        print(f"Subject: {pkt.subject_tag.value}{pkt.subject_value}")
        if pkt.arg1:
            print(f"ARG1   : {pkt.arg1}")
        if pkt.arg2:
            print(f"ARG2   : {pkt.arg2}")
        print(f"Temporal: {pkt.temporal}")
        if pkt.meta:
            print(f"Meta   : {pkt.meta}")
    else:
        packet = parse(args.packet)
        print(f"Version: v1")
        print(f"Domain : {packet.domain}")
        print(f"Tier   : {packet.tier}")
        if packet.agent_id:
            print(f"Agent  : {packet.agent_id}")
        if packet.preamble.rosetta_url:
            print(f"Rosetta: {packet.preamble.rosetta_url}")
        if packet.preamble.timestamp:
            print(f"Time   : {packet.preamble.timestamp}")
        if packet.preamble.payment:
            p = packet.preamble.payment
            print(f"Payment: agent={p.agent_id} sig={p.signature} gas={p.gas}")
        if packet.body.fields:
            print(f"Fields : {packet.body.fields}")
        if packet.flags:
            print(f"Flags  : {packet.flags}")


def _do_validate(args: argparse.Namespace) -> None:
    from axl.parser import detect_version, parse, parse_v3
    from axl.validator import validate, validate_v3

    version = detect_version(args.packet)
    if version == "v3":
        pkt = parse_v3(args.packet)
        errors = validate_v3(pkt)
        if not errors:
            print("PASS (v3)")
        else:
            print("FAIL (v3)")
            for e in errors:
                print(f"  ERROR: {e}")
    else:
        packet = parse(args.packet)
        result = validate(packet)
        if result.ok:
            print("PASS (v1)")
        else:
            print("FAIL (v1)")
        for w in result.warnings:
            print(f"  WARNING [{w.field_name}]: {w.message}")
        for e in result.errors:
            print(f"  ERROR   [{e.field_name}]: {e.message}")


def _do_translate(args: argparse.Namespace) -> None:
    from axl.emitter import v3_to_json
    from axl.parser import detect_version, parse, parse_v3
    from axl.translator import to_english, to_json, v3_to_english

    version = detect_version(args.packet)

    if args.to == "english":
        if version == "v3":
            print(v3_to_english(parse_v3(args.packet)))
        else:
            print(to_english(parse(args.packet)))
    elif args.to == "json":
        if version == "v3":
            print(json.dumps(v3_to_json(parse_v3(args.packet)), indent=2))
        else:
            print(json.dumps(to_json(parse(args.packet)), indent=2))
    else:
        print(f"Unknown format: {args.to}", file=sys.stderr)
        sys.exit(1)


def _do_emit(args: argparse.Namespace) -> None:
    from axl.emitter import emit
    from axl.models import Body, Packet, PaymentProof, Preamble

    fields = [f.strip() for f in args.fields.split(",")] if args.fields else []
    flags = [f.strip() for f in args.flags.split(",")] if args.flags else []

    preamble = Preamble()

    if args.agent:
        sig = args.signature or "0x0"
        gas = float(args.gas) if args.gas else 0.001
        preamble.payment = PaymentProof(
            agent_id=args.agent, signature=sig, gas=gas
        )

    body = Body(domain=args.domain, tier=int(args.tier), fields=fields)
    packet = Packet(preamble=preamble, body=body, flags=flags)

    print(emit(packet))


def _do_decompress(args: argparse.Namespace) -> None:
    from axl.decompressor import v3_to_english, format_decompressed, decompress

    with open(args.file) as f:
        text = f.read()

    if args.raw:
        claims = v3_to_english(text)
        for c in claims:
            print(f"[{c['op']}.{c['cc']}] {c['claim_text']}")
    else:
        print(decompress(text))


def _do_version(_args: argparse.Namespace) -> None:
    from axl import __version__

    print(f"axl-core {__version__}")


def main() -> None:
    """CLI entry point for the ``axl`` command."""
    parser = argparse.ArgumentParser(
        prog="axl",
        description="AXL Protocol — Agent eXchange Language CLI",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # ── parse ──
    p_parse = subparsers.add_parser("parse", help="Parse an AXL packet string")
    p_parse.add_argument("packet", help="Raw AXL packet string")
    p_parse.set_defaults(func=_do_parse)

    # ── validate ──
    p_validate = subparsers.add_parser("validate", help="Validate an AXL packet")
    p_validate.add_argument("packet", help="Raw AXL packet string")
    p_validate.set_defaults(func=_do_validate)

    # ── translate ──
    p_translate = subparsers.add_parser("translate", help="Translate an AXL packet")
    p_translate.add_argument(
        "--to", required=True, choices=["english", "json"],
        help="Output format",
    )
    p_translate.add_argument("packet", help="Raw AXL packet string")
    p_translate.set_defaults(func=_do_translate)

    # ── emit ──
    p_emit = subparsers.add_parser("emit", help="Emit an AXL packet string")
    p_emit.add_argument("--domain", required=True, help="Domain code (e.g. SIG, TRD)")
    p_emit.add_argument("--tier", default="1", help="Tier level (default: 1)")
    p_emit.add_argument("--fields", default="", help="Comma-separated body fields")
    p_emit.add_argument("--flags", default="", help="Comma-separated flags")
    p_emit.add_argument("--agent", default=None, help="Agent ID for payment proof")
    p_emit.add_argument("--signature", default=None, help="Signature for payment proof")
    p_emit.add_argument("--gas", default=None, help="Gas fee for payment proof")
    p_emit.set_defaults(func=_do_emit)

    # ── decompress ──
    p_decompress = subparsers.add_parser("decompress", help="Decompress AXL packets to English")
    p_decompress.add_argument("file", help="File containing AXL packets (use /dev/stdin for pipe)")
    p_decompress.add_argument("--raw", action="store_true", help="Print raw claims without grouping")
    p_decompress.set_defaults(func=_do_decompress)

    # ── version ──
    p_version = subparsers.add_parser("version", help="Print version")
    p_version.set_defaults(func=_do_version)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    args.func(args)


if __name__ == "__main__":
    main()

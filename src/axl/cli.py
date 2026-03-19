"""AXL command-line interface — argparse-based, zero external deps.

Entry point: ``axl`` (defined in pyproject.toml [project.scripts]).
"""

from __future__ import annotations

import argparse
import json
import sys


def _do_parse(args: argparse.Namespace) -> None:
    from axl.parser import parse

    packet = parse(args.packet)
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
    from axl.parser import parse
    from axl.validator import validate

    packet = parse(args.packet)
    result = validate(packet)

    if result.ok:
        print("PASS")
    else:
        print("FAIL")

    for w in result.warnings:
        print(f"  WARNING [{w.field_name}]: {w.message}")
    for e in result.errors:
        print(f"  ERROR   [{e.field_name}]: {e.message}")


def _do_translate(args: argparse.Namespace) -> None:
    from axl.parser import parse
    from axl.translator import to_english, to_json

    packet = parse(args.packet)

    if args.to == "english":
        print(to_english(packet))
    elif args.to == "json":
        print(json.dumps(to_json(packet), indent=2))
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

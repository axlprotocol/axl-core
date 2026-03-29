"""Tests for the AXL CLI."""

import subprocess
import sys


def run_cli(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "axl.cli", *args],
        capture_output=True, text=True,
    )


def test_cli_parse():
    result = run_cli("parse", "π:5:0xS:.001|S:SIG.3|BTC|69200|↓|RSI|.64|SIG")
    assert result.returncode == 0
    assert "SIG" in result.stdout
    assert "BTC" in result.stdout


def test_cli_validate_good():
    result = run_cli("validate", "π:5:0xS:.001|S:SIG.3|BTC|69200|↓|RSI|.64|SIG")
    assert result.returncode == 0
    assert "PASS" in result.stdout or "valid" in result.stdout.lower()


def test_cli_validate_bad():
    result = run_cli("validate", "π:5:0xS:.001|S:SIG.3|BTC|69200|WRONG|RSI|5.0|SIG")
    assert result.returncode == 0
    assert "warning" in result.stdout.lower() or "FAIL" in result.stdout


def test_cli_translate_english():
    result = run_cli("translate", "--to", "english", "π:5:0xS:.001|S:SIG.3|BTC|69200|↓|RSI|.64|SIG")
    assert result.returncode == 0
    assert "BTC" in result.stdout


def test_cli_translate_json():
    result = run_cli("translate", "--to", "json", "π:5:0xS:.001|S:SIG.3|BTC|69200|↓|RSI|.64|SIG")
    assert result.returncode == 0
    assert '"domain"' in result.stdout
    assert '"SIG"' in result.stdout


def test_cli_version():
    result = run_cli("version")
    assert result.returncode == 0
    assert "0.5.0" in result.stdout

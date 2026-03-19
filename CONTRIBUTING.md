# Contributing to axl-core

Thank you for your interest in contributing to the AXL Protocol.

## Getting Started

1. Fork and clone the repository:
   ```bash
   git clone https://github.com/axlprotocol/axl-core.git
   cd axl-core
   ```

2. Install in development mode:
   ```bash
   pip install -e ".[dev]"
   ```

3. Run the test suite:
   ```bash
   pytest
   ```

4. Run the linter:
   ```bash
   ruff check src/ tests/
   ```

## Making Changes

- Create a feature branch from `main`.
- Write tests for any new functionality.
- Ensure all tests pass and `ruff check` reports no issues.
- Keep commits focused and write clear commit messages.

## Pull Requests

- Open a PR against `main` with a clear description of the change.
- Reference any related issues.
- PRs require passing CI checks before merge.

## Code Style

- Follow PEP 8, enforced by `ruff`.
- Line length limit: 100 characters.
- Use type annotations for all public functions.
- Zero external dependencies for the core library.

## Reporting Bugs

Open an issue on GitHub with:
- A minimal reproducible example (AXL packet string + expected vs. actual behavior).
- Python version and OS.

## Security Issues

Please report security vulnerabilities privately. See [SECURITY.md](SECURITY.md) for details.

## License

By contributing, you agree that your contributions will be licensed under the Apache License 2.0.

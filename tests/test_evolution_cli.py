"""Tests for src/evolution/cli.py — CLI command for strategy evolution."""

from __future__ import annotations

import pytest

from src.evolution.cli import build_evolve_parser, cmd_evolve


# ---------------------------------------------------------------------------
# Parser tests
# ---------------------------------------------------------------------------

class TestEvolveParser:
    """Tests for the evolve CLI argument parser."""

    def test_parser_creation(self):
        parser = build_evolve_parser()
        assert parser is not None

    def test_required_symbol(self):
        parser = build_evolve_parser()
        args = parser.parse_args(["--symbol", "AAPL"])
        assert args.symbol == "AAPL"

    def test_generations_default(self):
        parser = build_evolve_parser()
        args = parser.parse_args(["--symbol", "AAPL"])
        assert args.generations == 10  # default

    def test_generations_custom(self):
        parser = build_evolve_parser()
        args = parser.parse_args(["--symbol", "AAPL", "--generations", "20"])
        assert args.generations == 20

    def test_frontier_size_default(self):
        parser = build_evolve_parser()
        args = parser.parse_args(["--symbol", "AAPL"])
        assert args.frontier_size == 3  # default

    def test_strategy_option(self):
        parser = build_evolve_parser()
        args = parser.parse_args(["--symbol", "AAPL", "--strategy", "golden-cross"])
        assert args.strategy == "golden-cross"

    def test_start_date(self):
        parser = build_evolve_parser()
        args = parser.parse_args(["--symbol", "AAPL", "--start", "2023-01-01"])
        assert args.start == "2023-01-01"

    def test_output_option(self):
        parser = build_evolve_parser()
        args = parser.parse_args(["--symbol", "AAPL", "--output", "best.yaml"])
        assert args.output == "best.yaml"

    def test_verbose_flag(self):
        parser = build_evolve_parser()
        args = parser.parse_args(["--symbol", "AAPL", "--verbose"])
        assert args.verbose is True

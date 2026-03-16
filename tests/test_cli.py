"""CLI 테스트"""
from __future__ import annotations

from unittest.mock import patch, MagicMock

import pytest
from click.testing import CliRunner

from cli.main import cli


class TestCLICommands:
    def test_cli_group_exists(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "Reviewer Intelligence Agent" in result.output

    def test_run_command_help(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["run", "--help"])
        assert result.exit_code == 0
        assert "manuscript_path" in result.output.lower() or "MANUSCRIPT_PATH" in result.output

    def test_profile_command_help(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["profile", "--help"])
        assert result.exit_code == 0

    def test_cost_command_no_log(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "src.optimization.cost_tracker.settings.cost_log_path",
            tmp_path / "nonexistent.jsonl",
        )
        runner = CliRunner()
        result = runner.invoke(cli, ["cost"])
        assert result.exit_code == 0
        assert "$0.0000" in result.output

    def test_upload_command_help(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["upload", "--help"])
        assert result.exit_code == 0

    def test_reset_cost_command(self, tmp_path, monkeypatch):
        log_path = tmp_path / "cost.jsonl"
        log_path.write_text('{"test": true}\n')
        monkeypatch.setattr(
            "src.optimization.cost_tracker.settings.cost_log_path",
            log_path,
        )
        runner = CliRunner()
        result = runner.invoke(cli, ["reset-cost"])
        assert result.exit_code == 0
        assert not log_path.exists()

    def test_run_mode_choices(self):
        runner = CliRunner()
        # Invalid mode should fail
        result = runner.invoke(cli, ["run", "Name", "file.docx", "--mode", "invalid"])
        assert result.exit_code != 0

import os
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from ..client.diagnostics import close_diagnostic_logger, create_diagnostic_logger, default_data_root


class TestDiagnosticLog(TestCase):
    def test_explicit_cross_platform_data_root_wins(self) -> None:
        with TemporaryDirectory() as temporary, patch.dict(
            os.environ, {"LOTF_AP_DATA_DIR": temporary}, clear=False
        ):
            self.assertEqual(Path(temporary), default_data_root())

    def test_log_appends_across_client_runs_and_has_run_ids(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            first, path, first_id = create_diagnostic_logger(root)
            first.info("first_marker")
            close_diagnostic_logger(first)

            second, second_path, second_id = create_diagnostic_logger(root)
            second.info("second_marker")
            close_diagnostic_logger(second)

            self.assertEqual(path, second_path)
            self.assertNotEqual(first_id, second_id)
            payload = path.read_text(encoding="utf-8")
            self.assertIn(f"run={first_id}", payload)
            self.assertIn(f"run={second_id}", payload)
            self.assertIn("first_marker", payload)
            self.assertIn("second_marker", payload)

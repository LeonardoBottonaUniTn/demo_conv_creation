"""Unit tests for Supabase-backed helpers in database.py."""
from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

CURRENT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = CURRENT_DIR.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import database  # noqa: E402  pylint: disable=wrong-import-position


class DatabaseSupabaseTests(unittest.TestCase):
    """Exercise Supabase-specific helpers without making live API calls."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.backend_dir = self.temp_dir.name
        self.sample_path = os.path.join(self.backend_dir, "files_root", "sample.json")
        os.makedirs(os.path.dirname(self.sample_path), exist_ok=True)
        with open(self.sample_path, "w", encoding="utf-8") as fh:
            json.dump({"users": []}, fh)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_upsert_file_record_sends_metadata_to_supabase(self) -> None:
        """Ensure payload includes classification and author metadata."""

        table_mock = MagicMock()
        table_mock.upsert.return_value = table_mock
        table_mock.select.return_value = table_mock

        def execute_side_effect(*_args, **_kwargs):
            payload = table_mock.upsert.call_args.args[0]
            supabase_row = dict(payload)
            supabase_row.update(
                {
                    "id": 99,
                    "structure_ok": True,
                    "created_at": "2024-01-01T00:00:00Z",
                    "updated_at": "2024-01-01T00:00:00Z",
                }
            )
            return SimpleNamespace(data=[supabase_row], error=None)

        table_mock.execute.side_effect = execute_side_effect

        client_mock = MagicMock()
        client_mock.table.return_value = table_mock

        def classify(_: str):
            return 1, "discussion"

        with patch("database.get_supabase_client", return_value=client_mock):
            record = database._upsert_file_record(
                self.sample_path,
                self.backend_dir,
                classify,
                created_by="user-42",
            )

        payload = table_mock.upsert.call_args.args[0]
        self.assertEqual(payload["name"], "sample.json")
        self.assertEqual(payload["created_by"], "user-42")
        self.assertTrue(payload["structure_ok"])
        self.assertEqual(table_mock.upsert.call_args.kwargs["on_conflict"], "name")
        self.assertEqual(record["id"], 99)
        self.assertEqual(record["structure_ok"], 1)

    def test_delete_files_with_prefix_removes_every_match(self) -> None:
        """The helper should delete each id returned by the preview query."""

        select_table = MagicMock()
        select_table.select.return_value = select_table
        select_table.like.return_value = select_table
        select_table.execute.return_value = SimpleNamespace(data=[{"id": 1}, {"id": 2}], error=None)

        delete_table = MagicMock()
        delete_table.delete.return_value = delete_table
        delete_table.in_.return_value = delete_table
        delete_table.execute.return_value = SimpleNamespace(data=None, error=None)

        client_mock = MagicMock()
        client_mock.table.side_effect = [select_table, delete_table]

        with patch("database.get_supabase_client", return_value=client_mock):
            removed = database._delete_files_with_prefix("drafts/")

        self.assertEqual(removed, 2)
        delete_table.in_.assert_called_once_with("id", [1, 2])
        select_table.like.assert_called_once_with("rel_path", "drafts/%")

    def test_get_file_record_by_id_normalizes_supabase_row(self) -> None:
        """Supabase rows with datetime + bool fields become API-friendly dicts."""

        table_mock = MagicMock()
        table_mock.select.return_value = table_mock
        table_mock.eq.return_value = table_mock
        table_mock.limit.return_value = table_mock
        table_mock.execute.return_value = SimpleNamespace(
            data=[
                {
                    "id": 7,
                    "name": "tree.json",
                    "size": 3210,
                    "upload_date": datetime(2024, 1, 5, 12, 0, 0),
                    "file_type": "json",
                    "rel_path": "files_root/tree.json",
                    "structure_ok": True,
                }
            ],
            error=None,
        )

        client_mock = MagicMock()
        client_mock.table.return_value = table_mock

        with patch("database.get_supabase_client", return_value=client_mock):
            row = database._get_file_record_by_id(7)

        self.assertEqual(row["id"], 7)
        self.assertEqual(row["name"], "tree.json")
        self.assertEqual(row["structure_ok"], 1)
        self.assertIn("T", row["uploadDate"])
        table_mock.eq.assert_called_once_with("id", 7)


if __name__ == "__main__":
    unittest.main()

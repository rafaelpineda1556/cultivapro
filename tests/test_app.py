import sqlite3
import tempfile
import unittest
from pathlib import Path

import app


class AppDBTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmpdir.name) / "test_crm.db"
        app.DB_PATH = self.db_path
        app.init_db()

    def tearDown(self):
        self.tmpdir.cleanup()

    def _conn(self):
        conn = app.connect_db()
        conn.row_factory = sqlite3.Row
        return conn

    def test_init_db_creates_expected_tables(self):
        with self._conn() as conn:
            tables = {
                row[0]
                for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            }

        for expected in {"clients", "items", "sales", "sale_items", "payments"}:
            self.assertIn(expected, tables)

    def test_client_balance_calculation(self):
        with self._conn() as conn:
            with conn:
                conn.execute(
                    "INSERT INTO clients(name, phone, email, address, created_at) VALUES (?, ?, ?, ?, ?)",
                    ("Ana", "555", "ana@mail.com", "Calle 1", "2026-01-01 00:00:00"),
                )
                client_id = conn.execute("SELECT id FROM clients LIMIT 1").fetchone()[0]

                conn.execute(
                    "INSERT INTO sales(client_id, sale_date, total, notes) VALUES (?, ?, ?, ?)",
                    (client_id, "2026-01-01 00:00:00", 300.0, "Venta inicial"),
                )
                conn.execute(
                    "INSERT INTO payments(client_id, sale_id, payment_date, amount, method, notes) VALUES (?, ?, ?, ?, ?, ?)",
                    (client_id, None, "2026-01-02 00:00:00", 120.0, "efectivo", "abono"),
                )

            sold, paid, balance = app.client_balance(conn, client_id)

        self.assertEqual(sold, 300.0)
        self.assertEqual(paid, 120.0)
        self.assertEqual(balance, 180.0)


if __name__ == "__main__":
    unittest.main()

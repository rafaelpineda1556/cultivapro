#!/usr/bin/env python3
"""App CLI para control de clientes, ventas, servicios/productos, abonos y saldos."""

from __future__ import annotations

import sqlite3
from contextlib import closing
from datetime import datetime
from pathlib import Path

DB_PATH = Path("crm_ventas.db")


def connect_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    with closing(connect_db()) as conn, conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS clients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                phone TEXT,
                email TEXT,
                address TEXT,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                kind TEXT NOT NULL CHECK(kind IN ('producto', 'servicio')),
                price REAL NOT NULL CHECK(price >= 0),
                active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS sales (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_id INTEGER NOT NULL,
                sale_date TEXT NOT NULL,
                total REAL NOT NULL CHECK(total >= 0),
                notes TEXT,
                FOREIGN KEY (client_id) REFERENCES clients(id)
            );

            CREATE TABLE IF NOT EXISTS sale_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sale_id INTEGER NOT NULL,
                item_id INTEGER NOT NULL,
                item_name TEXT NOT NULL,
                qty REAL NOT NULL CHECK(qty > 0),
                unit_price REAL NOT NULL CHECK(unit_price >= 0),
                subtotal REAL NOT NULL CHECK(subtotal >= 0),
                FOREIGN KEY (sale_id) REFERENCES sales(id) ON DELETE CASCADE,
                FOREIGN KEY (item_id) REFERENCES items(id)
            );

            CREATE TABLE IF NOT EXISTS payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_id INTEGER NOT NULL,
                sale_id INTEGER,
                payment_date TEXT NOT NULL,
                amount REAL NOT NULL CHECK(amount > 0),
                method TEXT,
                notes TEXT,
                FOREIGN KEY (client_id) REFERENCES clients(id),
                FOREIGN KEY (sale_id) REFERENCES sales(id)
            );
            """
        )


def now_text() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def input_float(label: str, min_value: float = 0.0) -> float:
    while True:
        raw = input(label).strip().replace(",", ".")
        try:
            value = float(raw)
        except ValueError:
            print("⚠️  Valor inválido. Intenta nuevamente.")
            continue
        if value < min_value:
            print(f"⚠️  El valor debe ser mayor o igual a {min_value}.")
            continue
        return value


def input_int(label: str, min_value: int = 1) -> int:
    while True:
        raw = input(label).strip()
        if not raw.isdigit():
            print("⚠️  Ingresa un número entero válido.")
            continue
        value = int(raw)
        if value < min_value:
            print(f"⚠️  El valor debe ser >= {min_value}.")
            continue
        return value


def list_clients(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    rows = conn.execute(
        "SELECT id, name, phone, email FROM clients ORDER BY name COLLATE NOCASE"
    ).fetchall()
    if not rows:
        print("No hay clientes registrados.")
        return []

    print("\nClientes:")
    print("-" * 70)
    for r in rows:
        print(f"[{r['id']}] {r['name']} | Tel: {r['phone'] or '-'} | Email: {r['email'] or '-'}")
    print("-" * 70)
    return rows


def add_client(conn: sqlite3.Connection) -> None:
    print("\n== Nuevo cliente ==")
    name = input("Nombre: ").strip()
    if not name:
        print("⚠️  El nombre es obligatorio.")
        return
    phone = input("Teléfono: ").strip()
    email = input("Email: ").strip()
    address = input("Dirección: ").strip()
    with conn:
        conn.execute(
            """
            INSERT INTO clients(name, phone, email, address, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (name, phone, email, address, now_text()),
        )
    print("✅ Cliente guardado.")


def list_items(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    rows = conn.execute(
        """
        SELECT id, name, kind, price, active
        FROM items
        ORDER BY kind, name COLLATE NOCASE
        """
    ).fetchall()

    if not rows:
        print("No hay productos/servicios registrados.")
        return []

    print("\nCatálogo:")
    print("-" * 70)
    for r in rows:
        estado = "activo" if r["active"] else "inactivo"
        print(f"[{r['id']}] {r['name']} ({r['kind']}) - ${r['price']:.2f} [{estado}]")
    print("-" * 70)
    return rows


def add_item(conn: sqlite3.Connection) -> None:
    print("\n== Nuevo producto/servicio ==")
    name = input("Nombre: ").strip()
    if not name:
        print("⚠️  El nombre es obligatorio.")
        return

    kind = input("Tipo [producto/servicio]: ").strip().lower()
    if kind not in {"producto", "servicio"}:
        print("⚠️  Tipo inválido. Debe ser 'producto' o 'servicio'.")
        return

    price = input_float("Precio base: $", min_value=0)
    with conn:
        conn.execute(
            """
            INSERT INTO items(name, kind, price, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (name, kind, price, now_text()),
        )
    print("✅ Producto/servicio guardado.")


def create_sale(conn: sqlite3.Connection) -> None:
    print("\n== Registrar venta ==")
    clients = list_clients(conn)
    if not clients:
        return

    client_id = input_int("ID del cliente: ")
    exists = conn.execute("SELECT 1 FROM clients WHERE id = ?", (client_id,)).fetchone()
    if not exists:
        print("⚠️  Cliente no encontrado.")
        return

    items = list_items(conn)
    if not items:
        return

    sale_lines: list[tuple[int, str, float, float, float]] = []
    total = 0.0

    while True:
        item_id = input_int("ID del producto/servicio (0 para terminar): ", min_value=0)
        if item_id == 0:
            break

        item = conn.execute(
            "SELECT id, name, price, active FROM items WHERE id = ?", (item_id,)
        ).fetchone()
        if not item:
            print("⚠️  Ítem no encontrado.")
            continue
        if not item["active"]:
            print("⚠️  El ítem está inactivo.")
            continue

        qty = input_float("Cantidad: ", min_value=0.0001)
        raw_price = input(f"Precio unitario (enter = {item['price']:.2f}): $").strip()
        if raw_price:
            try:
                unit_price = float(raw_price.replace(",", "."))
            except ValueError:
                print("⚠️  Precio inválido; se usará el precio base.")
                unit_price = float(item["price"])
        else:
            unit_price = float(item["price"])
        subtotal = qty * unit_price
        total += subtotal
        sale_lines.append((item["id"], item["name"], qty, unit_price, subtotal))
        print(f"➕ Agregado: {item['name']} x {qty} = ${subtotal:.2f}")

    if not sale_lines:
        print("⚠️  No se agregaron líneas. Venta cancelada.")
        return

    notes = input("Notas de venta (opcional): ").strip()
    with conn:
        cur = conn.execute(
            """
            INSERT INTO sales(client_id, sale_date, total, notes)
            VALUES (?, ?, ?, ?)
            """,
            (client_id, now_text(), total, notes),
        )
        sale_id = cur.lastrowid
        conn.executemany(
            """
            INSERT INTO sale_items(sale_id, item_id, item_name, qty, unit_price, subtotal)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            [(sale_id, item_id, name, qty, unit_price, subtotal) for item_id, name, qty, unit_price, subtotal in sale_lines],
        )
    print(f"✅ Venta registrada (folio #{sale_id}) por ${total:.2f}.")


def register_payment(conn: sqlite3.Connection) -> None:
    print("\n== Registrar abono/pago ==")
    clients = list_clients(conn)
    if not clients:
        return

    client_id = input_int("ID del cliente: ")
    exists = conn.execute("SELECT 1 FROM clients WHERE id = ?", (client_id,)).fetchone()
    if not exists:
        print("⚠️  Cliente no encontrado.")
        return

    sale_id_raw = input("ID de venta relacionada (opcional): ").strip()
    sale_id = int(sale_id_raw) if sale_id_raw.isdigit() else None
    if sale_id is not None:
        sale_exists = conn.execute(
            "SELECT 1 FROM sales WHERE id = ? AND client_id = ?", (sale_id, client_id)
        ).fetchone()
        if not sale_exists:
            print("⚠️  La venta no existe para este cliente.")
            return

    amount = input_float("Monto abonado: $", min_value=0.01)
    method = input("Método [efectivo/transferencia/tarjeta/etc]: ").strip()
    notes = input("Notas: ").strip()

    with conn:
        conn.execute(
            """
            INSERT INTO payments(client_id, sale_id, payment_date, amount, method, notes)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (client_id, sale_id, now_text(), amount, method, notes),
        )
    print("✅ Pago/abono registrado.")


def client_balance(conn: sqlite3.Connection, client_id: int) -> tuple[float, float, float]:
    sales_total = conn.execute(
        "SELECT COALESCE(SUM(total), 0) FROM sales WHERE client_id = ?", (client_id,)
    ).fetchone()[0]
    payments_total = conn.execute(
        "SELECT COALESCE(SUM(amount), 0) FROM payments WHERE client_id = ?", (client_id,)
    ).fetchone()[0]
    return float(sales_total), float(payments_total), float(sales_total - payments_total)


def show_client_statement(conn: sqlite3.Connection) -> None:
    print("\n== Estado de cuenta de cliente ==")
    clients = list_clients(conn)
    if not clients:
        return

    client_id = input_int("ID del cliente: ")
    client = conn.execute(
        "SELECT id, name, phone, email FROM clients WHERE id = ?", (client_id,)
    ).fetchone()
    if not client:
        print("⚠️  Cliente no encontrado.")
        return

    sales_total, payments_total, balance = client_balance(conn, client_id)
    print(f"\nCliente: {client['name']} (ID {client['id']})")
    print(f"Contacto: Tel {client['phone'] or '-'} | Email {client['email'] or '-'}")
    print(f"Total vendido: ${sales_total:.2f}")
    print(f"Total abonado: ${payments_total:.2f}")
    print(f"Saldo actual: ${balance:.2f}")

    print("\nÚltimas ventas:")
    sales = conn.execute(
        """
        SELECT id, sale_date, total, notes
        FROM sales
        WHERE client_id = ?
        ORDER BY id DESC
        LIMIT 10
        """,
        (client_id,),
    ).fetchall()
    if not sales:
        print("  (sin ventas)")
    for s in sales:
        print(f"  Venta #{s['id']} | {s['sale_date']} | ${s['total']:.2f} | {s['notes'] or '-'}")

    print("\nÚltimos abonos:")
    payments = conn.execute(
        """
        SELECT id, payment_date, amount, method, sale_id
        FROM payments
        WHERE client_id = ?
        ORDER BY id DESC
        LIMIT 10
        """,
        (client_id,),
    ).fetchall()
    if not payments:
        print("  (sin abonos)")
    for p in payments:
        venta_ref = f"Venta #{p['sale_id']}" if p["sale_id"] else "Sin venta"
        print(
            f"  Abono #{p['id']} | {p['payment_date']} | ${p['amount']:.2f} | "
            f"{p['method'] or '-'} | {venta_ref}"
        )


def show_global_balances(conn: sqlite3.Connection) -> None:
    print("\n== Saldos por cliente ==")
    rows = conn.execute(
        """
        SELECT
            c.id,
            c.name,
            COALESCE((SELECT SUM(s.total) FROM sales s WHERE s.client_id = c.id), 0) AS sold,
            COALESCE((SELECT SUM(p.amount) FROM payments p WHERE p.client_id = c.id), 0) AS paid
        FROM clients c
        ORDER BY c.name COLLATE NOCASE
        """
    ).fetchall()

    if not rows:
        print("No hay clientes.")
        return

    for r in rows:
        balance = float(r["sold"] - r["paid"])
        print(
            f"[{r['id']}] {r['name']}: vendido ${r['sold']:.2f} | "
            f"abonado ${r['paid']:.2f} | saldo ${balance:.2f}"
        )


def menu() -> None:
    init_db()
    with closing(connect_db()) as conn:
        while True:
            print(
                """
==============================
 CRM Ventas y Cobranza (CLI)
==============================
1) Alta de cliente
2) Listar clientes
3) Alta de producto/servicio
4) Listar catálogo
5) Registrar venta
6) Registrar abono/pago
7) Estado de cuenta por cliente
8) Saldos de todos los clientes
0) Salir
"""
            )
            option = input("Selecciona una opción: ").strip()

            if option == "1":
                add_client(conn)
            elif option == "2":
                list_clients(conn)
            elif option == "3":
                add_item(conn)
            elif option == "4":
                list_items(conn)
            elif option == "5":
                create_sale(conn)
            elif option == "6":
                register_payment(conn)
            elif option == "7":
                show_client_statement(conn)
            elif option == "8":
                show_global_balances(conn)
            elif option == "0":
                print("👋 Hasta luego.")
                break
            else:
                print("⚠️  Opción no válida.")


if __name__ == "__main__":
    menu()

# CRM Ventas y Cobranza (CLI)

Programa en Python para **control de clientes, ventas de servicios/productos, abonos, saldos y datos de contacto** usando SQLite.

## Funciones incluidas

- Alta y consulta de clientes (nombre, teléfono, email, dirección).
- Alta y consulta de productos/servicios.
- Registro de ventas con múltiples conceptos por venta.
- Registro de abonos/pagos (vinculados opcionalmente a una venta).
- Estado de cuenta por cliente.
- Resumen global de saldos por cliente.

## Requisitos

- Python 3.10+

## Uso

```bash
python3 app.py
```

Al iniciar, se crea automáticamente la base de datos `crm_ventas.db` en la misma carpeta.

## Cómo probarlo

### 1) Pruebas automáticas

```bash
python3 -m unittest discover -s tests -p 'test_*.py' -v
```

### 2) Prueba rápida manual (flujo sugerido)

1. Ejecuta `python3 app.py`.
2. Crea un cliente (opción `1`).
3. Crea un producto o servicio (opción `3`).
4. Registra una venta (opción `5`).
5. Registra un abono (opción `6`).
6. Consulta estado de cuenta (opción `7`) y saldos globales (opción `8`).

## Menú principal

1. Alta de cliente
2. Listar clientes
3. Alta de producto/servicio
4. Listar catálogo
5. Registrar venta
6. Registrar abono/pago
7. Estado de cuenta por cliente
8. Saldos de todos los clientes
0. Salir

## Notas

- Los saldos se calculan como: **total vendido - total abonado**.
- Puedes capturar abonos sin ligarlos a una venta específica.

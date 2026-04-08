"""
Shopping List — Backend REST API
FastAPI + PostgreSQL
Ejecutar:  uvicorn main:app --reload
"""

import os
from typing import Optional, Union, List, Dict, Any

import psycopg2
import psycopg2.extras
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# ---------------------------------------------------------------
#  Config
# ---------------------------------------------------------------
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

SEED_CATALOG: Dict[str, List[str]] = {
    "costco": [
        "Aguas Kirkland chicas", "Aguas Kirkland 1L", "Aguas Santa María",
        "Pellegrino", "Kleenex grandes", "Kleenex chicos", "Toallas de papel",
        "Papel de baño", "Servilletas", "Huggies", "Fresas y moras congeladas",
        "Chips Kirkland", "Cepillo de dientes", "Pasta de dientes", "Navajas",
        "Enjuague bucal", "Bolsas grandes", "Platos grandes desechables",
        "Queso crema", "Crema batida", "Dexivant", "Lagricel", "Riopan",
        "Jugo de toronja"
    ],
    "super": [
        "Limones", "Desodorante Nívea", "Bicarbonato refri", "Leche deslactosada",
        "Kleenex chicos", "Kleenex circulares", "Jabón líquido", "Jabón antibacterial",
        "Lili chocolate", "Lecheritas chocolate", "Pellegrino", "Enjuague bucal",
        "Pasta de dientes", "Cepillos de dientes", "Twinnings manzanilla",
        "Twinnings naranja canela", "Te rooibos", "Throat coat tea", "Ginger ale",
        "Welchs uva", "Ensure", "Shampoo", "Shower gel", "Gel de rasurar",
        "Fabuloso", "Pan blanco", "Azúcar morena", "Mermeladas", "Popotes",
        "Lagricel", "Dexivant", "Electrolit", "Cubrebocas", "Trapos absorbentes",
        "Boeing", "Invisi fix", "Vick VapoRub"
    ],
}

ALLOWED_TABS = {"costco", "super", "varios", "other"}


# ---------------------------------------------------------------
#  Database
# ---------------------------------------------------------------
def get_conn():
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)
    return conn


def init_db() -> None:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS catalog (
            id       SERIAL PRIMARY KEY,
            tab      TEXT    NOT NULL,
            name     TEXT    NOT NULL,
            position INTEGER NOT NULL DEFAULT 0,
            UNIQUE (tab, name)
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS items (
            id       SERIAL PRIMARY KEY,
            tab      TEXT    NOT NULL,
            name     TEXT    NOT NULL,
            qty      TEXT    NOT NULL DEFAULT '1',
            checked  INTEGER NOT NULL DEFAULT 0,
            priority TEXT,
            position INTEGER NOT NULL DEFAULT 0
        )
    """)
    # Sembrado inicial del catálogo
    cur.execute("SELECT COUNT(*) FROM catalog")
    if cur.fetchone()["count"] == 0:
        for tab, names in SEED_CATALOG.items():
            for pos, name in enumerate(names):
                cur.execute(
                    "INSERT INTO catalog (tab, name, position) VALUES (%s, %s, %s) ON CONFLICT (tab, name) DO NOTHING",
                    (tab, name, pos),
                )
    conn.commit()
    cur.close()
    conn.close()


# ---------------------------------------------------------------
#  Schemas
# ---------------------------------------------------------------
class AddItem(BaseModel):
    tab: str
    name: str
    qty: Union[int, str] = 1
    priority: Optional[str] = None


class UpdateItem(BaseModel):
    checked: Optional[bool] = None
    qty: Optional[Union[int, str]] = None
    priority: Optional[str] = None
    name: Optional[str] = None


class CatalogEntry(BaseModel):
    tab: str
    name: str


# ---------------------------------------------------------------
#  App
# ---------------------------------------------------------------
app = FastAPI(title="Shopping List API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def _startup() -> None:
    init_db()


# ---------------------------------------------------------------
#  Helpers
# ---------------------------------------------------------------
def _check_tab(tab: str) -> None:
    if tab not in ALLOWED_TABS:
        raise HTTPException(status_code=400, detail=f"Invalid tab '{tab}'")


def _serialize_item(row: Dict[str, Any]) -> Dict[str, Any]:
    qty_raw = row["qty"]
    qty: Union[int, str]
    try:
        qty = int(qty_raw)
    except (ValueError, TypeError):
        qty = qty_raw
    return {
        "id": row["id"],
        "tab": row["tab"],
        "name": row["name"],
        "qty": qty,
        "checked": bool(row["checked"]),
        "priority": row["priority"],
    }


# ---------------------------------------------------------------
#  Endpoints
# ---------------------------------------------------------------
@app.get("/")
def root() -> Dict[str, str]:
    return {"status": "ok", "service": "Shopping List API"}


@app.get("/api/cart")
def get_cart() -> Dict[str, Any]:
    """Devuelve todo el estado: catálogos + listas por pestaña."""
    conn = get_conn()
    cur  = conn.cursor()

    catalog: Dict[str, List[str]] = {t: [] for t in ALLOWED_TABS}
    cur.execute("SELECT tab, name FROM catalog ORDER BY tab, position, id")
    for row in cur.fetchall():
        catalog[row["tab"]].append(row["name"])

    lists: Dict[str, List[Dict[str, Any]]] = {t: [] for t in ALLOWED_TABS}
    cur.execute("SELECT * FROM items ORDER BY tab, position, id")
    for row in cur.fetchall():
        lists[row["tab"]].append(_serialize_item(row))

    cur.close()
    conn.close()
    return {"catalog": catalog, "lists": lists}


@app.post("/api/add")
def add_item(payload: AddItem) -> Dict[str, Any]:
    """Agrega un item a la lista de la pestaña indicada."""
    _check_tab(payload.tab)
    conn = get_conn()
    cur  = conn.cursor()
    cur.execute(
        "SELECT COALESCE(MAX(position), -1) + 1 AS next_pos FROM items WHERE tab = %s",
        (payload.tab,),
    )
    pos = cur.fetchone()["next_pos"]
    cur.execute(
        "INSERT INTO items (tab, name, qty, checked, priority, position) VALUES (%s, %s, %s, 0, %s, %s) RETURNING id",
        (payload.tab, payload.name, str(payload.qty), payload.priority, pos),
    )
    new_id = cur.fetchone()["id"]
    conn.commit()
    cur.execute("SELECT * FROM items WHERE id = %s", (new_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    return _serialize_item(row)


@app.put("/api/item/{item_id}")
def update_item(item_id: int, payload: UpdateItem) -> Dict[str, Any]:
    """Actualiza parcialmente un item (checked, qty, priority, name)."""
    conn = get_conn()
    cur  = conn.cursor()
    cur.execute("SELECT * FROM items WHERE id = %s", (item_id,))
    row = cur.fetchone()
    if not row:
        cur.close()
        conn.close()
        raise HTTPException(status_code=404, detail="Item not found")

    fields: List[str] = []
    values: List[Any] = []
    if payload.checked is not None:
        fields.append("checked = %s")
        values.append(1 if payload.checked else 0)
    if payload.qty is not None:
        fields.append("qty = %s")
        values.append(str(payload.qty))
    if payload.priority is not None:
        fields.append("priority = %s")
        values.append(payload.priority)
    if payload.name is not None:
        fields.append("name = %s")
        values.append(payload.name)

    if fields:
        values.append(item_id)
        cur.execute(f"UPDATE items SET {', '.join(fields)} WHERE id = %s", values)
        conn.commit()

    cur.execute("SELECT * FROM items WHERE id = %s", (item_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    return _serialize_item(row)


@app.delete("/api/item/{item_id}")
def delete_item(item_id: int) -> Dict[str, Any]:
    """Elimina un item por id."""
    conn = get_conn()
    cur  = conn.cursor()
    cur.execute("DELETE FROM items WHERE id = %s", (item_id,))
    conn.commit()
    cur.close()
    conn.close()
    return {"deleted": item_id}


@app.delete("/api/cart/{tab}/checked")
def clear_checked(tab: str) -> Dict[str, Any]:
    """Elimina solo los items completados de una pestaña."""
    _check_tab(tab)
    conn = get_conn()
    cur  = conn.cursor()
    cur.execute("DELETE FROM items WHERE tab = %s AND checked = 1", (tab,))
    conn.commit()
    count = cur.rowcount
    cur.close()
    conn.close()
    return {"tab": tab, "cleared": count}


@app.delete("/api/cart/{tab}")
def clear_tab(tab: str) -> Dict[str, Any]:
    """Vacía todos los items de una pestaña."""
    _check_tab(tab)
    conn = get_conn()
    cur  = conn.cursor()
    cur.execute("DELETE FROM items WHERE tab = %s", (tab,))
    conn.commit()
    count = cur.rowcount
    cur.close()
    conn.close()
    return {"tab": tab, "cleared": count}


@app.post("/api/catalog/add")
def add_catalog(payload: CatalogEntry) -> Dict[str, Any]:
    """Agrega una entrada al catálogo (productos frecuentes)."""
    _check_tab(payload.tab)
    conn = get_conn()
    cur  = conn.cursor()
    cur.execute(
        "SELECT COALESCE(MAX(position), -1) + 1 AS next_pos FROM catalog WHERE tab = %s",
        (payload.tab,),
    )
    pos = cur.fetchone()["next_pos"]
    try:
        cur.execute(
            "INSERT INTO catalog (tab, name, position) VALUES (%s, %s, %s) ON CONFLICT (tab, name) DO NOTHING",
            (payload.tab, payload.name, pos),
        )
        conn.commit()
    except psycopg2.IntegrityError:
        conn.rollback()  # ya existe, idempotente
    cur.close()
    conn.close()
    return {"tab": payload.tab, "name": payload.name}


@app.delete("/api/catalog/remove")
def remove_catalog(payload: CatalogEntry) -> Dict[str, Any]:
    """Elimina una entrada del catálogo."""
    _check_tab(payload.tab)
    conn = get_conn()
    cur  = conn.cursor()
    cur.execute("DELETE FROM catalog WHERE tab = %s AND name = %s", (payload.tab, payload.name))
    conn.commit()
    cur.close()
    conn.close()
    return {"tab": payload.tab, "name": payload.name, "deleted": True}

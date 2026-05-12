"""
database.py
-----------
Catálogo de produtos corporativos (sem necessidade de especificações detalhadas).
Campos: id, nome, categoria, icone, criado_em
"""

import json
import os
import time
import uuid
from typing import List, Dict, Any, Optional

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(BASE_DIR, "catalogo.json")

# Catálogo inicial padrão — carregado apenas se o arquivo não existir
DEFAULT_CATALOG = [
    {"id": str(uuid.uuid4()), "nome": "Notebook",           "categoria": "Informática",   "icone": "💻", "criado_em": "2026-01-01T00:00:00"},
    {"id": str(uuid.uuid4()), "nome": "Monitor",            "categoria": "Informática",   "icone": "🖥️", "criado_em": "2026-01-01T00:00:00"},
    {"id": str(uuid.uuid4()), "nome": "Teclado",            "categoria": "Informática",   "icone": "⌨️", "criado_em": "2026-01-01T00:00:00"},
    {"id": str(uuid.uuid4()), "nome": "Mouse",              "categoria": "Informática",   "icone": "🖱️", "criado_em": "2026-01-01T00:00:00"},
    {"id": str(uuid.uuid4()), "nome": "Headset",            "categoria": "Periféricos",   "icone": "🎧", "criado_em": "2026-01-01T00:00:00"},
    {"id": str(uuid.uuid4()), "nome": "Webcam",             "categoria": "Periféricos",   "icone": "📷", "criado_em": "2026-01-01T00:00:00"},
    {"id": str(uuid.uuid4()), "nome": "Impressora",         "categoria": "Escritório",    "icone": "🖨️", "criado_em": "2026-01-01T00:00:00"},
    {"id": str(uuid.uuid4()), "nome": "Projetor",           "categoria": "Escritório",    "icone": "📽️", "criado_em": "2026-01-01T00:00:00"},
    {"id": str(uuid.uuid4()), "nome": "Telefone IP",        "categoria": "Telecom",       "icone": "📞", "criado_em": "2026-01-01T00:00:00"},
    {"id": str(uuid.uuid4()), "nome": "Roteador",           "categoria": "Rede",          "icone": "📡", "criado_em": "2026-01-01T00:00:00"},
    {"id": str(uuid.uuid4()), "nome": "Switch de Rede",     "categoria": "Rede",          "icone": "🔌", "criado_em": "2026-01-01T00:00:00"},
    {"id": str(uuid.uuid4()), "nome": "Nobreak",            "categoria": "Elétrica",      "icone": "🔋", "criado_em": "2026-01-01T00:00:00"},
    {"id": str(uuid.uuid4()), "nome": "Cadeira Ergonômica", "categoria": "Mobiliário",    "icone": "🪑", "criado_em": "2026-01-01T00:00:00"},
    {"id": str(uuid.uuid4()), "nome": "Mesa de Trabalho",   "categoria": "Mobiliário",    "icone": "🗂️", "criado_em": "2026-01-01T00:00:00"},
    {"id": str(uuid.uuid4()), "nome": "Smartphone",         "categoria": "Telefonia",     "icone": "📱", "criado_em": "2026-01-01T00:00:00"},
    {"id": str(uuid.uuid4()), "nome": "Tablet",             "categoria": "Informática",   "icone": "📟", "criado_em": "2026-01-01T00:00:00"},
]


def _load() -> List[Dict[str, Any]]:
    if not os.path.exists(DB_FILE):
        _save(DEFAULT_CATALOG)
        return DEFAULT_CATALOG
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return DEFAULT_CATALOG


def _save(items: List[Dict[str, Any]]) -> None:
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)


def get_all_items() -> List[Dict[str, Any]]:
    return _load()


def get_item_by_id(item_id: str) -> Optional[Dict[str, Any]]:
    return next((p for p in _load() if p["id"] == item_id), None)


def create_item(nome: str, categoria: str = "Geral", icone: str = "📦") -> Dict[str, Any]:
    items = _load()
    item = {
        "id": str(uuid.uuid4()),
        "nome": nome.strip(),
        "categoria": categoria.strip() if categoria else "Geral",
        "icone": icone.strip() if icone else "📦",
        "criado_em": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    items.append(item)
    _save(items)
    return item


def delete_item(item_id: str) -> bool:
    items = _load()
    new_list = [p for p in items if p["id"] != item_id]
    if len(new_list) == len(items):
        return False
    _save(new_list)
    return True

def update_item(item_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    items = _load()
    for item in items:
        if item["id"] == item_id:
            item.update(updates)
            _save(items)
            return item
    return None

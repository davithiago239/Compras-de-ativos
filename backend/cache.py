"""
cache.py
--------
Cache simples em memória + persistência JSON para evitar
requisições repetidas à API do Mercado Livre.
TTL padrão: 1 hora (3600 segundos).
"""

import json
import os
import time
from typing import Any, Optional

CACHE_FILE = os.path.join(os.path.dirname(__file__), "cache.json")
DEFAULT_TTL = 3600  # 1 hora em segundos


def _load_cache() -> dict:
    """Carrega o cache do arquivo JSON. Retorna dict vazio se não existir."""
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}
    return {}


def _save_cache(data: dict) -> None:
    """Persiste o cache no arquivo JSON."""
    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except IOError as e:
        print(f"[Cache] Erro ao salvar cache: {e}")


def get_cached(key: str) -> Optional[Any]:
    """
    Busca um valor no cache pela chave.
    Retorna None se a chave não existir ou se o TTL tiver expirado.
    """
    cache = _load_cache()
    entry = cache.get(key)

    if entry is None:
        return None

    # Verifica se o TTL expirou
    if time.time() - entry["timestamp"] > DEFAULT_TTL:
        # Remove entrada expirada
        del cache[key]
        _save_cache(cache)
        return None

    return entry["data"]


def set_cached(key: str, value: Any) -> None:
    """Armazena um valor no cache com timestamp atual."""
    cache = _load_cache()
    cache[key] = {
        "timestamp": time.time(),
        "data": value
    }
    _save_cache(cache)


def clear_cache() -> int:
    """Limpa todo o cache. Retorna o número de entradas removidas."""
    if os.path.exists(CACHE_FILE):
        cache = _load_cache()
        count = len(cache)
        os.remove(CACHE_FILE)
        return count
    return 0


def cache_stats() -> dict:
    """Retorna estatísticas do cache."""
    cache = _load_cache()
    now = time.time()
    valid = sum(1 for e in cache.values() if now - e["timestamp"] <= DEFAULT_TTL)
    return {
        "total_entries": len(cache),
        "valid_entries": valid,
        "expired_entries": len(cache) - valid
    }

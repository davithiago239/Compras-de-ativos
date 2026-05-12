"""
logger.py
---------
Módulo de log de consultas realizadas no sistema.
Registra data/hora, produto buscado, número de resultados e origem.
Arquivo de log: consultas.log (na pasta backend/)
"""

import logging
import os
from datetime import datetime

LOG_FILE = os.path.join(os.path.dirname(__file__), "consultas.log")

# Configura o logger do módulo
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler()  # Também exibe no console
    ]
)

_logger = logging.getLogger("compras_corporativas")


def log_query(produto: str, modelo: str, marketplace: str, resultados: int) -> None:
    """
    Registra uma consulta no log.

    Args:
        produto: Categoria do produto (ex: 'Mouse')
        modelo: Modelo buscado (ex: 'Logitech M170')
        marketplace: Nome do marketplace consultado
        resultados: Número de resultados encontrados
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    msg = (
        f"[{timestamp}] CONSULTA | Produto: {produto} | "
        f"Modelo: {modelo} | Marketplace: {marketplace} | "
        f"Resultados: {resultados}"
    )
    _logger.info(msg)


def log_upload(filename: str, produtos_identificados: int) -> None:
    """Registra o upload de um arquivo Excel."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    msg = (
        f"[{timestamp}] UPLOAD | Arquivo: {filename} | "
        f"Produtos identificados: {produtos_identificados}"
    )
    _logger.info(msg)


def log_error(context: str, error: str) -> None:
    """Registra um erro no log."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    msg = f"[{timestamp}] ERRO | Contexto: {context} | Detalhe: {error}"
    _logger.error(msg)


def log_cache_hit(modelo: str) -> None:
    """Registra quando um resultado veio do cache."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    msg = f"[{timestamp}] CACHE_HIT | Modelo: {modelo}"
    _logger.info(msg)

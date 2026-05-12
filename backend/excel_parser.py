"""
excel_parser.py
---------------
Módulo responsável por ler e processar o arquivo Excel de histórico
de compras corporativas.

Colunas esperadas:
    - Produto       : Categoria (ex: Mouse, Teclado, Notebook)
    - Modelo        : Modelo específico (ex: Logitech M170)
    - Último Preço  : Preço pago na última compra (float)
    - Data da Compra: Data da aquisição (datetime)
"""

import pandas as pd
import io
from typing import List, Dict, Any


COLUMN_ALIASES = {
    "produto": ["produto", "category", "categoria", "item", "tipo"],
    "modelo": ["modelo", "model", "produto/modelo", "descrição", "descricao", "descrição\\modelo", "descricao\\modelo", "marca", "descrição/modelo", "descricao/modelo"],
    "ultimo_preco": ["último preço", "ultimo preco", "preço", "preco", "price", "valor", "valor unitário", "valor unitario"],
    "data_compra": ["data da compra", "data compra", "data", "date", "data_compra"],
}


def _normalize_column_name(name: str) -> str:
    """Remove espaços extras e converte para minúsculas."""
    return name.strip().lower()


def _find_column(df_columns: List[str], aliases: List[str]) -> str:
    """
    Encontra o nome real de uma coluna no DataFrame a partir de apelidos.
    Retorna o nome encontrado ou lança ValueError.
    """
    normalized = {_normalize_column_name(c): c for c in df_columns}
    for alias in aliases:
        if alias in normalized:
            return normalized[alias]
    return None


def parse_excel(file_bytes: bytes, filename: str) -> List[Dict[str, Any]]:
    """
    Lê o arquivo Excel e retorna a lista de produtos mais recentes por categoria.

    Args:
        file_bytes: Conteúdo binário do arquivo .xlsx ou .csv
        filename: Nome do arquivo (para determinar o formato)

    Returns:
        Lista de dicts com keys: produto, modelo, ultimo_preco, data_compra

    Raises:
        ValueError: Se o arquivo estiver em formato inválido ou colunas faltando
    """
    try:
        buffer = io.BytesIO(file_bytes)

        # Suporte a .xlsx e .csv
        if filename.lower().endswith(".csv"):
            df = pd.read_csv(buffer, encoding="utf-8-sig")
        else:
            df = pd.read_excel(buffer, engine="openpyxl")

    except Exception as e:
        raise ValueError(f"Erro ao ler o arquivo '{filename}': {str(e)}")

    if df.empty:
        raise ValueError("O arquivo está vazio.")

    # Mapeia as colunas encontradas
    col_map = {}

    for key, aliases in COLUMN_ALIASES.items():
        found = _find_column(list(df.columns), aliases)
        if found:
            col_map[key] = found

    if "produto" not in col_map and "modelo" not in col_map:
        raise ValueError(
            f"Nenhuma coluna identificadora (Produto ou Modelo) encontrada. "
            f"Colunas presentes: {', '.join(df.columns.tolist())}"
        )

    # Renomeia para nomes padronizados
    rename_dict = {v: k for k, v in col_map.items()}
    df = df.rename(columns=rename_dict)

    # Assegura que todas as colunas existem (preenche com None se não existir)
    for col in ["produto", "modelo", "ultimo_preco", "data_compra"]:
        if col not in df.columns:
            df[col] = None

    # Seleciona apenas as colunas necessárias
    df = df[["produto", "modelo", "ultimo_preco", "data_compra"]].copy()

    # Remove linhas que não têm produto E não têm modelo
    df.dropna(subset=["produto", "modelo"], how="all", inplace=True)

    # Converte tipos
    df["data_compra"] = pd.to_datetime(df["data_compra"], dayfirst=True, errors="coerce")
    df["ultimo_preco"] = pd.to_numeric(df["ultimo_preco"], errors="coerce")

    # Identifica o produto mais recente (ordena por data e remove duplicatas)
    # Se a data falhar, a ordenação simplesmente manterá a ordem original.
    df_sorted = df.sort_values("data_compra", ascending=False, na_position="last")
    
    # Remove duplicatas. Se temos 'produto', usamos para dedup. Senão usamos 'modelo'.
    subset_dedup = ["produto"] if "produto" in df_sorted.columns and not df_sorted["produto"].isna().all() else ["modelo"]
    df_recentes = df_sorted.drop_duplicates(subset=subset_dedup).reset_index(drop=True)

    if df_recentes.empty:
        raise ValueError("Nenhuma linha válida encontrada após processamento.")

    # Converte para lista de dicts serializáveis
    result = []
    for _, row in df_recentes.iterrows():
        preco = row["ultimo_preco"]
        data = row["data_compra"]
        
        prod = str(row["produto"]).strip() if pd.notna(row["produto"]) else ""
        mod =  str(row["modelo"]).strip() if pd.notna(row["modelo"]) else ""
        
        # Se um estiver vazio, usa o outro
        if not prod: prod = mod
        if not mod: mod = prod
        
        result.append({
            "produto": prod,
            "modelo": mod,
            "ultimo_preco": float(preco) if pd.notna(preco) else None,
            "data_compra": data.strftime("%d/%m/%Y") if pd.notna(data) else "",
        })

    return result


def validate_columns_preview(file_bytes: bytes, filename: str) -> Dict[str, Any]:
    """
    Retorna um preview das colunas e primeiras linhas do arquivo
    para validação antes do processamento completo.
    """
    try:
        buffer = io.BytesIO(file_bytes)
        if filename.lower().endswith(".csv"):
            df = pd.read_csv(buffer, encoding="utf-8-sig", nrows=5)
        else:
            df = pd.read_excel(buffer, engine="openpyxl", nrows=5)

        return {
            "columns": df.columns.tolist(),
            "row_count_preview": len(df),
            "sample": df.head(3).to_dict(orient="records")
        }
    except Exception as e:
        return {"error": str(e)}

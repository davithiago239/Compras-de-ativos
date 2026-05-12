"""
main.py — Sistema de Compras Corporativas v3
Endpoints:
    GET    /                          → Frontend
    GET    /api/health                → Health check
    GET    /api/catalogo              → Lista todos os itens do catálogo
    POST   /api/catalogo              → Adiciona novo item ao catálogo
    DELETE /api/catalogo/{id}         → Remove item do catálogo
    GET    /api/buscar/{item_id}      → Busca preços no ML para o item clicado
    GET    /api/export                → Exporta últimos resultados em Excel
    GET    /api/cache/stats           → Stats do cache
    DELETE /api/cache                 → Limpa cache
"""

import os
import time
from typing import List, Dict, Any, Optional

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import Response, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, validator

from database import get_all_items, get_item_by_id, create_item, delete_item, update_item
from marketplaces.mercado_livre import search_mercado_livre, do_search
from cache import get_cached, set_cached, clear_cache, cache_stats
from logger import log_query, log_error, log_cache_hit
from exporter import export_to_excel

# ── Config ────────────────────────────────────────────────────────────────────

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.join(BASE_DIR, "..", "frontend")

_last_results: List[Dict[str, Any]] = []

_auto_foto_status: Dict[str, Any] = {
    "running": False,
    "total": 0,
    "processed": 0,
    "success": 0,
    "skipped": 0,
    "failed": 0,
    "current": "",
}


def run_auto_fotos() -> None:
    """Busca thumbnails do ML para todos os itens sem foto e salva no catálogo."""
    import random
    global _auto_foto_status

    items = get_all_items()
    sem_foto = [i for i in items if not i.get("foto")]

    _auto_foto_status.update({
        "running": True,
        "total": len(sem_foto),
        "processed": 0,
        "success": 0,
        "skipped": len(items) - len(sem_foto),
        "failed": 0,
        "current": "",
    })

    for item in sem_foto:
        # Usa apenas as primeiras palavras antes de qualquer ponto-e-vírgula
        nome_limpo = item["nome"].split(";")[0].strip()
        _auto_foto_status["current"] = nome_limpo

        try:
            results = do_search(nome_limpo)
            if results and results[0].get("thumbnail"):
                foto = results[0]["thumbnail"].replace("I.jpg", "O.jpg")
                if foto and foto.startswith("http"):
                    update_item(item["id"], {"foto": foto})
                    _auto_foto_status["success"] += 1
                else:
                    _auto_foto_status["failed"] += 1
            else:
                _auto_foto_status["failed"] += 1
        except Exception as e:
            log_error("auto_fotos", str(e))
            _auto_foto_status["failed"] += 1

        _auto_foto_status["processed"] += 1
        time.sleep(random.uniform(1.0, 1.8))   # Respeita rate-limit do ML

    _auto_foto_status["running"] = False
    _auto_foto_status["current"] = ""

# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(title="Sistema de Compras Corporativas", version="3.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Modelos ───────────────────────────────────────────────────────────────────

class ItemCreate(BaseModel):
    nome: str = Field(..., min_length=1, max_length=100)
    categoria: Optional[str] = Field("Geral", max_length=60)
    icone: Optional[str] = Field("📦", max_length=10)

    @validator("nome")
    def nome_nao_vazio(cls, v):
        if not v.strip():
            raise ValueError("Nome não pode ser vazio")
        return v

# ── Health ────────────────────────────────────────────────────────────────────

@app.get("/api/health")
async def health():
    return {"status": "ok", "timestamp": time.time()}

# ── Catálogo ──────────────────────────────────────────────────────────────────

@app.get("/api/catalogo")
async def listar_catalogo():
    """Retorna todo o catálogo de itens."""
    return get_all_items()


@app.post("/api/catalogo", status_code=201)
async def adicionar_item(body: ItemCreate):
    """Adiciona um novo item ao catálogo."""
    item = create_item(
        nome=body.nome,
        categoria=body.categoria or "Geral",
        icone=body.icone or "📦",
    )
    return item


@app.delete("/api/catalogo/{item_id}", status_code=204)
async def remover_item(item_id: str):
    """Remove um item do catálogo."""
    removed = delete_item(item_id)
    if not removed:
        raise HTTPException(status_code=404, detail="Item não encontrado.")
    return Response(status_code=204)

class ItemUpdate(BaseModel):
    foto: str

@app.put("/api/catalogo/{item_id}", status_code=200)
async def atualizar_item(item_id: str, body: ItemUpdate):
    """Atualiza a imagem de um item no catálogo."""
    updated = update_item(item_id, {"foto": body.foto})
    if not updated:
        raise HTTPException(status_code=404, detail="Item não encontrado.")
    return updated

# ── Busca ─────────────────────────────────────────────────────────────────────

@app.get("/api/buscar/{item_id}")
async def buscar_item(item_id: str):
    """
    Retorna detalhes de ultima compra para o item (consulta de modelo, cor, foto).
    """
    item = get_item_by_id(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item não encontrado no catálogo.")

    nome = item["nome"]
    cache_key = f"ml:{nome.lower().strip()}"

    cached = get_cached(cache_key)
    
    # Valores genéricos caso não tenha histórico
    foto = f"https://placehold.co/400x300/2a2a35/ffffff?text=Sem+Foto"
    modelo = "Padrão (Última Compra)"
    cor = "Padrão"
    preco = 0.0

    if cached and len(cached) > 0:
        first = cached[0]
        # Pegue uma foto mais bonita do histórico de ML
        foto = first.get("thumbnail", foto).replace("I.jpg", "O.jpg")
        modelo = first.get("titulo", modelo)
        preco = first.get("preco", preco)
        log_cache_hit(nome)

    # Se o item possuir uma foto customizada sobrescreve o cache/placeholder
    if "foto" in item and item["foto"]:
        foto = item["foto"]

    log_query(nome, nome, "Consulta Interna", 1)

    resultado = {
        "item_id": item["id"],
        "item_nome": item["nome"],
        "item_icone": item.get("icone", "📦"),
        "item_categoria": item.get("categoria", "Geral"),
        "modelo": modelo,
        "cor": cor,
        "ultimo_preco": preco,
        "foto": foto,
    }

    return {
        "success": True,
        "item": item,
        "detalhes": resultado
    }

# ── Auto-fotos ───────────────────────────────────────────────────────────────

@app.post("/api/catalogo/auto-fotos", status_code=202)
async def iniciar_auto_fotos(background_tasks: BackgroundTasks):
    """Inicia a busca automática de fotos para todos os itens sem foto."""
    if _auto_foto_status.get("running"):
        raise HTTPException(status_code=409, detail="Processo já está em execução.")
    background_tasks.add_task(run_auto_fotos)
    return {"message": "Processo iniciado em segundo plano."}


@app.get("/api/catalogo/auto-fotos/status")
async def status_auto_fotos():
    """Retorna o andamento do processo de auto-fotos."""
    return _auto_foto_status


# ── Cache ─────────────────────────────────────────────────────────────────────

@app.get("/api/cache/stats")
async def get_cache_stats():
    return cache_stats()

@app.delete("/api/cache")
async def limpar_cache():
    count = clear_cache()
    return {"message": f"Cache limpo. {count} entradas removidas."}

# ── Export ────────────────────────────────────────────────────────────────────

@app.get("/api/export")
async def exportar_excel():
    if not _last_results:
        raise HTTPException(status_code=404, detail="Nenhum resultado disponível. Clique em um produto primeiro.")
    try:
        excel_bytes = export_to_excel(_last_results)
    except Exception as e:
        log_error("export_excel", str(e))
        raise HTTPException(status_code=500, detail="Erro ao gerar o arquivo Excel.")

    filename = f"compras_corporativas_{int(time.time())}.xlsx"
    return Response(
        content=excel_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )

# ── Frontend ──────────────────────────────────────────────────────────────────

if os.path.exists(FRONTEND_DIR):
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True, log_level="info")

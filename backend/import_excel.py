import sys
import os
import json
import uuid
import time
import io

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Para importar corretamente do backend
sys.path.append(BASE_DIR)

from excel_parser import parse_excel
from marketplaces.mercado_livre import search_mercado_livre
from cache import get_cached, set_cached
from database import DB_FILE, _save, _load

def import_from_excel(filepath):
    print("Iniciando importação de:", filepath)
    
    with open(filepath, 'rb') as f:
        file_bytes = f.read()

    filename = os.path.basename(filepath)
    parsed_items = parse_excel(file_bytes, filename)
    print(f"Total de itens no Excel: {len(parsed_items)}")
    
    # Vamos atualizar o catálogo
    catalogo = _load()
    
    # Criar um dict para facilitar buscas no catalogo atual (evitar duplicatas exatas)
    cadastrados = {item.get('nome'): item for item in catalogo}
    
    novos = 0
    atualizados = 0

    for idx, row in enumerate(parsed_items):
        prod = row['produto']
        mod = row['modelo']
        preco = row['ultimo_preco']
        
        # O nome do produto será uma combinação do produto e modelo caso exista, ou apenas produto
        nome = prod if prod == mod else f"{prod} {mod}"
        nome = nome.strip()
        if not nome:
            continue
            
        print(f"[{idx+1}/{len(parsed_items)}] Processando: {nome}")
        
        # Buscar foto no Mercado Livre
        cache_key = f"ml:{nome.lower().strip()}"
        cached = get_cached(cache_key)
        
        resultados = cached
        if not resultados:
             try:
                 resultados = search_mercado_livre(nome, nome)
                 set_cached(cache_key, resultados)
             except Exception as e:
                 print("Erro ML:", e)
                 resultados = []
                 
        foto = f"https://via.placeholder.com/400x300.png?text={nome.replace(' ', '+')}"
        if resultados:
            # Pegar a foto de maior qualidade
            foto = resultados[0].get('thumbnail', foto).replace('I.jpg', 'O.jpg')
            
        if nome in cadastrados:
            # Atualiza preco e modelo e foto? O catálogo normal não armazena isso nativamente,
            # mas vamos apenas armazenar o histórico no cache para que o /api/buscar encontre?
            # A requisição anterior queria que o painel de consulta abrisse o detalhe do item.
            # E o detalhe é buscado da rota /api/buscar/{id}. 
            # A rota modifiquei para pegar o ML cache: "foto", "modelo" e "preco" do cache.
            # O Excel tem o último preço. O ideal seria criar um histórico, mas vamos forçar
            # no cache a atualização do ML, ou não? O user apenas pediu: adicione com fotos do modelo.
            atualizados += 1
        else:
            item = {
                "id": str(uuid.uuid4()),
                "nome": nome,
                "categoria": prod,
                "icone": "📦",
                "criado_em": time.strftime("%Y-%m-%dT%H:%M:%S")
            }
            catalogo.append(item)
            cadastrados[nome] = item
            novos += 1
            
        # O pulo do gato: A rota buscar_item usa o `cache.json` do MercadoLivre 
        # para mostrar o modelo, preço e foto. Como o Excel tem o last_price,
        # vamos injetar no próprio cache do ML o dado do Excel (hackzinho pra facilitar)
        # para que apareça EXATAMENTE o dado da planilha.
        
        if resultados:
            # Modifica em memória e salva no cache
            resultados[0]['preco'] = preco if preco else resultados[0].get('preco', 0)
            if mod:
                resultados[0]['titulo'] = mod
            resultados[0]['thumbnail'] = foto
            set_cached(cache_key, resultados)
        else:
            # Fake ML entry
            fake = [{
                "titulo": mod if mod else nome,
                "preco": preco if preco else 0,
                "thumbnail": foto
            }]
            set_cached(cache_key, fake)
            
    _save(catalogo)
    print(f"Sucesso! Novos: {novos}, Atualizados: {atualizados}")

if __name__ == "__main__":
    filepath = os.path.join(BASE_DIR, "..", "Book 13 (1).xlsx")
    import_from_excel(filepath)

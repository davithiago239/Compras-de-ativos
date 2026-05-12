"""
mercado_livre.py
----------------
Integração com o Mercado Livre através de Web Scraping (BeautifulSoup).
Contorna a nova limitação da API pública (Status 403 Forbidden).
"""

import requests
from bs4 import BeautifulSoup
import re
import random
import time
from typing import List, Dict, Any

MAX_RESULTS = 5
REQUEST_TIMEOUT = 15

# Headers simulando um navegador real
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
}

def _clean_query(text: str, max_words: int = 6) -> str:
    """
    Limpa a string removendo caracteres especiais e pegando as X 
    primeiras palavras para garantir uma URL válida de busca.
    """
    if not text:
        return ""
    text = re.sub(r'[;/\\]', ' ', text)
    text = text.replace(",", " ")
    words = text.split()
    return "-".join(words[:max_words])


def _extract_number(text: str) -> float:
    """Extrai valor numérico de strings como 1.499"""
    if not text:
        return 0.0
    text = text.replace(".", "").replace(",", ".")
    try:
        return float(text)
    except ValueError:
        return 0.0


def format_currency(val: float) -> str:
    """Formata valor em Real"""
    return f"R$ {val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def do_search(term: str) -> List[Dict[str, Any]]:
    """Função central de web scraping para o Mercado Livre."""
    query = _clean_query(term)
    # Lista com as condições: novo.
    url = f"https://lista.mercadolivre.com.br/{query}_ITEM*CONDITION_2230284"
    
    results = []
    
    try:
        r = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        r.raise_for_status()
        
        soup = BeautifulSoup(r.text, 'lxml')
        items = soup.select('li.ui-search-layout__item')
        
        for item in items[:MAX_RESULTS]:
            # === Título e Link ===
            title_el = item.select_one('h2.poly-component__title a') or item.select_one('a[class*="title"]')
            titulo = "Sem título"
            link = "#"
            if title_el:
                titulo = title_el.get_text(strip=True)
                link = title_el.get("href", "#")
            
            # Caso não ache via a, tenta pegar direto do texto do h2
            if titulo == "Sem título":
                title_h2 = item.select_one('h2.poly-component__title') or item.select_one('h2')
                if title_h2:
                    titulo = title_h2.get_text(strip=True)
            
            # === Preço ===
            # Pega o bloco principal de preço para evitar pegar o preço cortado (antigo)
            preco_float = 0.0
            price_block = item.select_one('.poly-component__price')
            if price_block:
                fraction = price_block.select_one('.andes-money-amount__fraction')
                if fraction:
                    preco_float = _extract_number(fraction.get_text(strip=True))

            # Se falhou, tenta genérico
            if preco_float == 0.0:
                fraction_gen = item.select_one('.andes-money-amount__fraction')
                if fraction_gen:
                    preco_float = _extract_number(fraction_gen.get_text(strip=True))

            # === Frete ===
            frete_text = "Consultar no site"
            frete_el = item.select_one('.poly-component__shipping') or item.select_one('[class*="fulfillment"]')
            frete_gratis = False
            
            if frete_el:
                f_texto = frete_el.get_text(strip=True)
                if "grátis" in f_texto.lower():
                    frete_gratis = True
                    frete_text = "Frete grátis"
                elif "full" in f_texto.lower():
                    frete_text = "Full ≈ 1-2 dias"
                else:
                    frete_text = f_texto
                    
            # Thumbnail (nem sempre é simples porque o ML pode usar lazy load com src ou data-src ou srcset)
            thumbnail = ""
            img_el = item.select_one('img')
            if img_el:
                thumbnail = img_el.get('data-src') or img_el.get('src') or ""
                
            results.append({
                "titulo": titulo,
                "preco": preco_float,
                "preco_formatado": format_currency(preco_float),
                "prazo": frete_text,
                "link": link,
                "marketplace": "Mercado Livre",
                "thumbnail": thumbnail,
                "condicao": "Novo",
                "vendedor": "",
                "frete_gratis": frete_gratis,
            })
            
    except Exception as e:
        print(f"[ML Scraping Error]: {str(e)}")
        
    return results


def search_mercado_livre(produto: str, modelo: str) -> List[Dict[str, Any]]:
    """
    Função principal chamada pelo backend/main.py.
    """
    print(f"[ML] Buscando: '{modelo}' via Web Scraping...")
    
    # Tentativa principal com o termo completo
    results = do_search(modelo)
    
    # Se encontrou poucos resultados, faz uma busca fallback
    if len(results) < 2:
        print(f"[ML] Poucos resultados para '{modelo}', tentando fallback...")
        time.sleep(random.uniform(0.5, 1.0))
        fallback_query = f"{produto} {modelo.split()[0]}" if modelo else produto
        fallback_res = do_search(fallback_query)
        
        existing_links = {r["link"] for r in results}
        for item in fallback_res:
            if item["link"] not in existing_links:
                results.append(item)
            if len(results) >= MAX_RESULTS:
                break
                
    # Ordena por preço
    results.sort(key=lambda x: x["preco"] if x["preco"] > 0 else float("inf"))
    
    print(f"[ML] Retornando {len(results)} resultados para '{modelo}'")
    return results[:MAX_RESULTS]

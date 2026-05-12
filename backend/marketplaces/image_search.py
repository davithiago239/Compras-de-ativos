"""
image_search.py
---------------
Busca imagens de produtos na internet (Google Images scraping),
usado como fallback quando o Mercado Livre não retorna thumbnail.
"""

import re
import time
import random
import requests
from typing import Optional
from urllib.parse import quote_plus

REQUEST_TIMEOUT = 12

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8",
    "Referer": "https://www.google.com/",
}


def _is_valid_image_url(url: str) -> bool:
    """Verifica se a URL parece ser uma imagem real e acessível."""
    if not url or len(url) < 10:
        return False
    # Ignora ícones e placeholders
    bad = ["logo", "icon", "favicon", "placeholder", "pixel", "1x1", "blank", "data:image/gif"]
    url_lower = url.lower()
    if any(b in url_lower for b in bad):
        return False
    # Precisa ter extensão de imagem ou ser URL de CDN comum
    good_ext = [".jpg", ".jpeg", ".png", ".webp", ".avif"]
    has_ext = any(e in url_lower for e in good_ext)
    cdn_domains = ["gstatic", "ggpht", "googleusercontent", "wp.com", "cloudinary",
                   "shopify", "amazon", "ssl-images", "mlstatic", "magazineluiza",
                   "americanas", "buscape", "kabum", "dell", "lenovo"]
    has_cdn = any(d in url_lower for d in cdn_domains)
    return has_ext or has_cdn


def search_google_images(query: str) -> Optional[str]:
    """
    Busca no Google Images e extrai a URL da primeira imagem real encontrada.
    Usa o endpoint de busca de imagens do Google.
    """
    try:
        safe_query = quote_plus(query)
        url = f"https://www.google.com/search?q={safe_query}&tbm=isch&hl=pt-BR&gl=BR"
        
        response = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        
        if response.status_code != 200:
            return None
        
        text = response.text
        
        # Padrão 1: URLs dentro dos dados JSON do Google
        # Google embute as URLs das imagens em blocos JSON no HTML
        patterns = [
            r'"(https?://[^"]+\.(?:jpg|jpeg|png|webp))"',
            r'imgurl=(https?://[^&"]+)',
            r'"ou":"(https?://[^"]+)"',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                # Decodifica escape unicode se necessário
                try:
                    clean = match.encode().decode('unicode_escape')
                except Exception:
                    clean = match
                if _is_valid_image_url(clean):
                    return clean
                    
        return None
        
    except Exception as e:
        print(f"[ImageSearch Google] Erro: {e}")
        return None


def search_bing_images(query: str) -> Optional[str]:
    """
    Alternativa usando Bing Images como fallback.
    """
    try:
        safe_query = quote_plus(query)
        url = f"https://www.bing.com/images/search?q={safe_query}&first=1&mkt=pt-BR"
        
        response = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        
        if response.status_code != 200:
            return None
            
        text = response.text
        
        # Bing embute dados em atributo m="" contendo JSON
        # Padrão: m="{...,"murl":"URL_DA_IMAGEM"...}"
        pattern = r'murl&quot;:&quot;(https?://[^&"]+?)&quot;'
        matches = re.findall(pattern, text)
        
        for match in matches:
            if _is_valid_image_url(match):
                return match
                
        # Fallback: procura imgurl
        pattern2 = r'"imgurl":"(https?://[^"]+)"'
        matches2 = re.findall(pattern2, text)
        for match in matches2:
            if _is_valid_image_url(match):
                return match
                
        return None
        
    except Exception as e:
        print(f"[ImageSearch Bing] Erro: {e}")
        return None


def find_product_image(nome: str, categoria: str = "") -> Optional[str]:
    """
    Função principal: tenta buscar a foto de um produto pelo nome.
    Usa Google como primária e Bing como fallback.
    
    Retorna a URL da imagem ou None.
    """
    # Monta query inteligente usando nome + categoria para contexto
    # Limita o tamanho para evitar queries sem sentido
    words = nome.split()[:8]
    query = " ".join(words)
    
    if categoria and categoria.lower() not in query.lower():
        # Adiciona a categoria se não estiver na query
        cat_words = categoria.split()[:2]
        query = f"{' '.join(cat_words)} {query}"
    
    print(f"[ImageSearch] Buscando foto para: '{query}'")
    
    # Tentativa 1: Google Images
    img_url = search_google_images(query)
    if img_url:
        print(f"[ImageSearch] Google: {img_url[:80]}...")
        return img_url
    
    # Delay para não sobrecarregar
    time.sleep(random.uniform(0.3, 0.8))
    
    # Tentativa 2: Bing Images
    img_url = search_bing_images(query)
    if img_url:
        print(f"[ImageSearch] Bing: {img_url[:80]}...")
        return img_url
    
    # Tentativa 3: Tenta query simplificada no Google
    simple_query = " ".join(words[:4])
    img_url = search_google_images(simple_query)
    if img_url:
        print(f"[ImageSearch] Google (simplificado): {img_url[:80]}...")
        return img_url
    
    print(f"[ImageSearch] Nenhuma imagem encontrada para: '{nome}'")
    return None

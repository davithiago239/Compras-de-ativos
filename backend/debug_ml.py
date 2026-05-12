import requests
from bs4 import BeautifulSoup
import re

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Accept-Language': 'pt-BR,pt;q=0.9',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
}

url = 'https://lista.mercadolivre.com.br/headset'
r = requests.get(url, headers=headers, timeout=15)
soup = BeautifulSoup(r.text, 'lxml')

items = soup.select('li.ui-search-layout__item')
item = items[0]

# Mapa completo de seletores
print('=== TITULO ===')
for sel in ['h2.poly-component__title', 'h2[class*="title"]', '.poly-component__title', '[class*="title"] a', 'h2 a', 'a[class*="title"]']:
    el = item.select_one(sel)
    if el:
        print(f'  {sel}: {el.get_text(strip=True)[:80]}')
        break

print('\n=== PRECO ===')
# O preco pode estar em varios seletores
for sel in ['.poly-component__price', '[class*="poly-price"]', '.price-tag-fraction', 
            '.andes-money-amount__fraction', '[class*="price__fraction"]',
            '[class*="amount__fraction"]', 'span[class*="fraction"]']:
    els = item.select(sel)
    if els:
        print(f'  {sel}: {[e.get_text(strip=True) for e in els]}')
        break

print('\n=== LINK ===')
link = item.select_one('a.poly-component__title, a[class*="title"], h2 a, a[href*="MLB"]')
print(f'  Link: {link["href"][:100] if link and link.get("href") else "N/A"}')

print('\n=== FRETE ===')
for sel in ['.poly-component__shipping', '[class*="shipping"]', '[class*="free-shipping"]', 
            'span[class*="fulfillment"]', '[class*="fulfillment"]']:
    el = item.select_one(sel)
    if el:
        print(f'  {sel}: {el.get_text(strip=True)[:60]}')
        break

print('\n=== HTML PRIMEIRO ITEM (1500c) ===')
print(str(item)[:1500])

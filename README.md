# Sistema de Compras Corporativas

Sistema web completo para automação de compras corporativas. Ele aceita um arquivo Excel (ou CSV) contendo o histórico de compras, identifica o produto mais recente por categoria e pesquisa automaticamente no Mercado Livre para encontrar as melhores ofertas.

## Funcionalidades

- **Upload de Excel/CSV** com histórico de compras.
- **Identificação Automática:** Agrupa por produto e usa a `Data da Compra` mais recente.
- **Integração com Mercado Livre:** Busca oficial nativa via API para dados como precos, prazo de entrega e links.
- **Cache Local:** Reduz o número de requisições armazenando buscas repetidas.
- **Design Premium:** Dark theme avançado utilizando apenas HTML, CSS e JS puros e altamente customizáveis.
- **Exportação para Excel:** Com relatórios enfeitados de dados da busca.

## Requisitos
- Python 3.10 ou superior.

## Como instalar e executar

1. Abra o Terminal ou Prompt de Comando.
2. Navegue até a pasta `backend/`:
   ```bash
   cd caminho/para/compras-corporativas/backend
   ```
3. Instale as dependências:
   ```bash
   pip install -r requirements.txt
   ```
4. Inicie o servidor:
   ```bash
   uvicorn main:app --reload --port 8000
   ```
5. Acesse no navegador:
   http://localhost:8000

## Gerando Dados de Exemplo

Se você não tiver uma planilha em mãos, pode gerar uma fictícia executando o seguinte comando na pasta `backend/`:
```bash
python create_sample.py
```
Isso criará o arquivo `sample_data/historico_compras.xlsx`.

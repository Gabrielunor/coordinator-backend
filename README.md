# Coordinator Backend

Serviço FastAPI responsável por expor informações de tiles hilbertianos no sistema de coordenadas SIRGAS 2000 / Brazil Albers.

## Executando o projeto

```bash
pip install -e .
uvicorn script:app --reload
```

### Endpoints disponíveis

- `GET /health` – verificação de saúde.
- `GET /tiles/{level}/{tile_id}` – retorna o tile correspondente em GeoJSON.
- `GET /tiles/lookup?level={nivel}&lon={longitude}&lat={latitude}` – encontra o tile que contém a coordenada.

## Estrutura do projeto

- `script.py`: módulo principal que expõe a API REST.
- `coordinator_backend/`: pacote com a lógica de projeção e tiles.
- `pyproject.toml`: arquivo de configuração e dependências do projeto.

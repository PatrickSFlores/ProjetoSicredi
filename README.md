# Projeto Sicredi — ETL + Docker + PostgreSQL + Python

Pipeline de ETL para processar extratos `.PRN` do Sicredi, gerar datasets limpos/enriquecidos, métricas e persistir no PostgreSQL — tudo **containerizado** com Docker.

> **Stack:** Python 3.11 • Polars/Pandas • PostgreSQL 15 • Docker Compose • FastAPI/Uvicorn (api)

---

## 🚀 Visão Geral

1. **Entrada**: arquivos brutos `.PRN` em `dados/brutos/`.
2. **ETL** (4 etapas em `codigos/`):
   - `01_carga_bruta.py` → leitura/ingestão do `.PRN`
   - `02_limpeza_dados.py` → parse, normalização e tipos
   - `03_processamento.py` → enriquecimento (Data/Hora, dia da semana, diferença débito–crédito…)
   - `04_metricas.py` → métricas agregadas (por origem, dia com > e < movimentos, soma diária, RX1/PX1, etc.)
3. **Saídas**:
   - Parquet/CSV em `dados/limpos` e `dados/resultados`
   - Tabela `public.movimentos` e `public.logs` no PostgreSQL do container

---

## 🧱 Arquitetura & Pastas

.
├─ docker-compose.yml
├─ .env # variáveis de ambiente (NÃO versionar)
├─ .gitignore
├─ backend/
│ ├─ Dockerfile
│ └─ app/
│ ├─ main.py
│ ├─ db.py, models.py, schemas.py, utils.py
│ └─ etl.py
├─ codigos/
│ ├─ 01_carga_bruta.py
│ ├─ 02_limpeza_dados.py
│ ├─ 03_processamento.py
│ └─ 04_metricas.py
└─ dados/
├─ brutos/ # coloque aqui seus .PRN
├─ intermediarios/
├─ limpos/
├─ processados/
└─ resultados/

---

## ⚙️ Pré-requisitos

- Windows 10/11 com **WSL2** atualizado
- **Docker Desktop** (com Compose v2 habilitado)
- **Git** instalado
- (Opcional) Python 3.11 local para testes e debugging

---

## 🔐 Arquivo `.env`

Crie um arquivo `.env` na **raiz do projeto** (mesmo nível do `docker-compose.yml`) com o conteúdo abaixo:

POSTGRES_DB=sicredi
POSTGRES_USER=etl
POSTGRES_PASSWORD=etlpass
POSTGRES_HOST=db
POSTGRES_PORT=5432

API_HOST=0.0.0.0
API_PORT=8000

> 🔒 O arquivo `.env` não deve ser versionado — ele já está incluído no `.gitignore`.

---

## 🧪 Como Rodar o Projeto (Passo a Passo)

### 1️⃣ Clonar o repositório

```bash
git clone https://github.com/PatrickSFlores/ProjetoSicredi.git
cd ProjetoSicredi


```

# ComplyRoute — Backend API

Gateway de Pagamento com roteamento inteligente entre múltiplos subadquirentes.

**Stack:** Python 3.12 · FastAPI · Neon (PostgreSQL serverless) · SQLAlchemy · Alembic · Redis · Celery

---

## Estrutura do Projeto

```
complyroute-backend/
├── app/
│   ├── api/
│   │   └── v1/
│   │       └── endpoints/
│   │           ├── transactions.py   # CRUD de transações
│   │           ├── routing.py        # Motor de roteamento
│   │           ├── acquirers.py      # Subadquirentes
│   │           ├── webhooks.py       # Webhooks
│   │           ├── auth.py           # Autenticação JWT
│   │           ├── users.py          # Usuários
│   │           ├── reconciliation.py # Conciliação
│   │           └── settings.py       # Configurações
│   ├── core/
│   │   ├── config.py      # Variáveis de ambiente
│   │   ├── security.py    # JWT, hashing, HMAC
│   │   ├── logging.py     # Logger estruturado
│   │   └── exceptions.py  # Exceções customizadas
│   ├── db/
│   │   ├── base.py        # Base declarativa SQLAlchemy
│   │   ├── session.py     # Conexão Neon (async)
│   │   └── migrations/    # Alembic migrations
│   ├── models/            # Modelos ORM (tabelas)
│   ├── schemas/           # Pydantic schemas (request/response)
│   ├── services/          # Lógica de negócio
│   │   ├── routing_engine.py   # Motor de roteamento
│   │   ├── fraud_engine.py     # Antifraude
│   │   └── acquirer_clients/   # Clientes HTTP por subadquirente
│   └── workers/           # Celery tasks (webhooks, conciliação)
├── tests/
│   ├── unit/
│   └── integration/
├── scripts/
│   ├── seed.py            # Dados iniciais
│   └── migrate.py         # Helper migrations
├── .env.example
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── alembic.ini
└── main.py
```

## Quickstart

```bash
# 1. Clonar e entrar na pasta
git clone https://github.com/complysoft/complyroute-backend.git
cd complyroute-backend

# 2. Criar ambiente virtual
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
.venv\Scripts\activate     # Windows

# 3. Instalar dependências
pip install -r requirements.txt

# 4. Configurar variáveis de ambiente
cp .env.example .env
# Editar .env com suas credenciais

# 5. Rodar migrations
alembic upgrade head

# 6. Iniciar servidor
uvicorn main:app --reload --port 8000
```

## Documentação da API

Disponível em `http://localhost:8000/docs` (Swagger UI) e `http://localhost:8000/redoc` (ReDoc).

## Variáveis de Ambiente

Ver `.env.example` para a lista completa.

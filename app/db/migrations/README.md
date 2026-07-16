# Migrações Alembic

Para criar uma nova migração:

```bash
alembic revision --autogenerate -m "descricao"
```

Para aplicar:

```bash
alembic upgrade head
```

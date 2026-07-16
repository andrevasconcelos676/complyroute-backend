"""Base declarativa SQLAlchemy — importar todos os modelos aqui para Alembic."""

from sqlalchemy.orm import DeclarativeBase, declared_attr


class Base(DeclarativeBase):
    """Classe base para todos os modelos ORM."""

    @declared_attr.directive
    def __tablename__(cls) -> str:
        """Gera nome da tabela em snake_case a partir do nome da classe."""
        import re
        name = re.sub(r"(?<!^)(?=[A-Z])", "_", cls.__name__).lower()
        return name


def import_all_models() -> None:
    """Importa todos os modelos para registrar as tabelas no metadata."""
    from app.models import (  # noqa: F401
        acquirer,
        api_key,
        audit_log,
        routing_rule,
        transaction,
        user,
        webhook,
    )

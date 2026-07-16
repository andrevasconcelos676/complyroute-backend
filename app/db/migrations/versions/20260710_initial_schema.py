"""Initial schema

Revision ID: 20260710_initial_schema
Revises: None
Create Date: 2026-07-10 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by alembic.
revision = "20260710_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("role", sa.Enum("admin", "financial", "technical", "readonly", name="user_role"), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=True),
        sa.Column("is_2fa_enabled", sa.Boolean(), nullable=True),
        sa.Column("totp_secret", sa.String(length=64), nullable=True),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)

    op.create_table(
        "transactions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("amount", sa.BigInteger(), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("installments", sa.Integer(), nullable=False),
        sa.Column("method", sa.Enum("credit", "debit", "pix", "boleto", name="payment_method"), nullable=False),
        sa.Column("status", sa.Enum("pending", "processing", "approved", "declined", "refunded", "chargeback", name="txn_status"), nullable=False),
        sa.Column("acquirer", sa.String(length=50), nullable=True),
        sa.Column("acquirer_txn_id", sa.String(length=255), nullable=True),
        sa.Column("authorization_code", sa.String(length=50), nullable=True),
        sa.Column("nsu", sa.String(length=50), nullable=True),
        sa.Column("routing_rule_applied", sa.String(length=255), nullable=True),
        sa.Column("fraud_score", sa.Integer(), nullable=True),
        sa.Column("fraud_blocked", sa.Boolean(), nullable=True),
        sa.Column("customer_name", sa.String(length=255), nullable=False),
        sa.Column("customer_document", sa.String(length=20), nullable=False),
        sa.Column("customer_email", sa.String(length=255), nullable=False),
        sa.Column("card_last4", sa.String(length=4), nullable=True),
        sa.Column("card_brand", sa.String(length=30), nullable=True),
        sa.Column("card_country", sa.String(length=2), nullable=True),
        sa.Column("card_bin", sa.String(length=6), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("retries", sa.Integer(), nullable=True),
        sa.Column("metadata", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_transactions_acquirer"), "transactions", ["acquirer"], unique=False)
    op.create_index(op.f("ix_transactions_created_at"), "transactions", ["created_at"], unique=False)
    op.create_index(op.f("ix_transactions_status"), "transactions", ["status"], unique=False)

    op.create_table(
        "acquirers",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=50), nullable=False),
        sa.Column("display_name", sa.String(length=100), nullable=False),
        sa.Column("api_url", sa.String(length=500), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=True),
        sa.Column("is_primary", sa.Boolean(), nullable=True),
        sa.Column("is_fallback", sa.Boolean(), nullable=True),
        sa.Column("priority", sa.Integer(), nullable=True),
        sa.Column("traffic_pct", sa.Float(), nullable=True),
        sa.Column("supports_credit", sa.Boolean(), nullable=True),
        sa.Column("supports_debit", sa.Boolean(), nullable=True),
        sa.Column("supports_pix", sa.Boolean(), nullable=True),
        sa.Column("supports_boleto", sa.Boolean(), nullable=True),
        sa.Column("approval_rate", sa.Float(), nullable=True),
        sa.Column("avg_latency_ms", sa.Integer(), nullable=True),
        sa.Column("credentials", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )

    op.create_table(
        "routing_rules",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("condition", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column("action", sa.String(length=20), nullable=False),
        sa.Column("target_acquirer", sa.String(length=50), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_routing_rules_is_active"), "routing_rules", ["is_active"], unique=False)
    op.create_index(op.f("ix_routing_rules_priority"), "routing_rules", ["priority"], unique=True)

    op.create_table(
        "webhooks",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("url", sa.String(length=2048), nullable=False),
        sa.Column("events", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column("secret", sa.String(length=256), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=True),
        sa.Column("success_rate", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "webhook_deliveries",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("webhook_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event", sa.String(length=100), nullable=False),
        sa.Column("payload", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column("response_status", sa.Integer(), nullable=True),
        sa.Column("response_body", sa.Text(), nullable=True),
        sa.Column("attempt", sa.Integer(), nullable=True),
        sa.Column("success", sa.Boolean(), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["webhook_id"], ["webhooks.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_webhook_deliveries_webhook_id"), "webhook_deliveries", ["webhook_id"], unique=False)

    op.create_table(
        "api_keys",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("key_hash", sa.String(length=64), nullable=False),
        sa.Column("key_prefix", sa.String(length=10), nullable=False),
        sa.Column("key_preview", sa.String(length=8), nullable=False),
        sa.Column("scope", sa.Enum("full", "readonly", "sandbox", name="api_key_scope"), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=True),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_api_keys_key_hash"), "api_keys", ["key_hash"], unique=True)
    op.create_index(op.f("ix_api_keys_user_id"), "api_keys", ["user_id"], unique=False)

    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("resource", sa.String(length=50), nullable=False),
        sa.Column("resource_id", sa.String(length=255), nullable=True),
        sa.Column("ip_address", sa.String(length=45), nullable=True),
        sa.Column("user_agent", sa.String(length=512), nullable=True),
        sa.Column("payload", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("result", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_audit_logs_created_at"), "audit_logs", ["created_at"], unique=False)
    op.create_index(op.f("ix_audit_logs_user_id"), "audit_logs", ["user_id"], unique=False)
    op.create_index(op.f("ix_audit_logs_action"), "audit_logs", ["action"], unique=False)


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("api_keys")
    op.drop_table("webhook_deliveries")
    op.drop_table("webhooks")
    op.drop_table("routing_rules")
    op.drop_table("acquirers")
    op.drop_table("transactions")
    op.drop_table("users")
    op.execute("DROP TYPE IF EXISTS api_key_scope")
    op.execute("DROP TYPE IF EXISTS user_role")
    op.execute("DROP TYPE IF EXISTS payment_method")
    op.execute("DROP TYPE IF EXISTS txn_status")

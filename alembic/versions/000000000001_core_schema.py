"""core schema: symbols, candles, fetch_runs, scan_runs, config

Revision ID: 000000000001
Revises: 
Create Date: 2025-09-15 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '000000000001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Create enum for scan_runs.status
    scan_status_enum = postgresql.ENUM(
        'pending', 'running', 'completed', 'failed',
        name='scanrunstatus',
        create_type=True
    )
    scan_status_enum.create(op.get_bind(), checkfirst=True)

    # symbols
    op.create_table(
        'symbols',
        sa.Column('id', sa.BigInteger(), primary_key=True),
        sa.Column('name', sa.String(length=128), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('base_asset', sa.String(length=64), nullable=True),
        sa.Column('quote_asset', sa.String(length=64), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.UniqueConstraint('name', name='uq_symbols_name')
    )

    # fetch_runs
    op.create_table(
        'fetch_runs',
        sa.Column('id', sa.BigInteger(), primary_key=True),
        sa.Column('started_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('finished_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('source', sa.String(length=64), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
    )

    # config
    op.create_table(
        'config',
        sa.Column('id', sa.BigInteger(), primary_key=True),
        sa.Column('name', sa.String(length=128), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('params', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.UniqueConstraint('name', name='uq_config_name')
    )

    # scan_runs
    op.create_table(
        'scan_runs',
        sa.Column('id', sa.BigInteger(), primary_key=True),
        sa.Column('started_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('finished_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('config_id', sa.BigInteger(), sa.ForeignKey('config.id', ondelete='CASCADE'), nullable=False),
        sa.Column('status', sa.Enum('pending', 'running', 'completed', 'failed', name='scanrunstatus'), nullable=False, server_default='pending'),
        sa.Column('stats', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
    )

    # candles
    op.create_table(
        'candles',
        sa.Column('id', sa.BigInteger(), primary_key=True),
        sa.Column('symbol_id', sa.BigInteger(), sa.ForeignKey('symbols.id', ondelete='CASCADE'), nullable=False),
        sa.Column('timeframe', sa.String(length=16), nullable=False),
        sa.Column('open_time', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('close_time', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('open', sa.Numeric(), nullable=False),
        sa.Column('high', sa.Numeric(), nullable=False),
        sa.Column('low', sa.Numeric(), nullable=False),
        sa.Column('close', sa.Numeric(), nullable=False),
        sa.Column('volume', sa.Numeric(), nullable=True),
        sa.Column('extra', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('fetch_run_id', sa.BigInteger(), sa.ForeignKey('fetch_runs.id', ondelete='CASCADE'), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.UniqueConstraint('symbol_id', 'timeframe', 'open_time', name='uq_candles_symbol_tf_open'),
    )

    # index for open_time for fast range queries
    op.create_index('ix_candles_open_time', 'candles', ['open_time'])


def downgrade():
    # drop index and tables in reverse order
    op.drop_index('ix_candles_open_time', table_name='candles')
    op.drop_table('candles')
    op.drop_table('scan_runs')
    op.drop_table('config')
    op.drop_table('fetch_runs')
    op.drop_table('symbols')

    # drop enum
    scan_status_enum = postgresql.ENUM(name='scanrunstatus')
    scan_status_enum.drop(op.get_bind(), checkfirst=True)

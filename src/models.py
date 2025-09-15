from datetime import datetime
import sqlalchemy as sa
from sqlalchemy import orm
from sqlalchemy.ext.declarative import declarative_base

# Prefer PostgreSQL JSONB/ENUM when available; fall back for SQLite tests
try:
    from sqlalchemy.dialects.postgresql import JSONB as PGJSONB, ENUM as PGENUM
    JSONB = PGJSONB
    PG_ENUM_AVAILABLE = True
except Exception:
    JSONB = sa.JSON
    PG_ENUM_AVAILABLE = False

Base = declarative_base()


class Symbol(Base):
    __tablename__ = 'symbols'
    id = sa.Column(sa.BigInteger, primary_key=True, autoincrement=True)
    name = sa.Column(sa.String(128), nullable=False, unique=True)
    description = sa.Column(sa.Text, nullable=True)
    base_asset = sa.Column(sa.String(64), nullable=True)
    quote_asset = sa.Column(sa.String(64), nullable=True)
    created_at = sa.Column(sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False)

    candles = orm.relationship('Candle', back_populates='symbol', cascade='all, delete-orphan')

    def __repr__(self):
        return f"<Symbol(id={self.id}, name={self.name})>"


class FetchRun(Base):
    __tablename__ = 'fetch_runs'
    id = sa.Column(sa.BigInteger, primary_key=True, autoincrement=True)
    started_at = sa.Column(sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False)
    finished_at = sa.Column(sa.TIMESTAMP(timezone=True), nullable=True)
    source = sa.Column(sa.String(64), nullable=False)
    notes = sa.Column(sa.Text, nullable=True)
    created_at = sa.Column(sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False)

    candles = orm.relationship('Candle', back_populates='fetch_run', cascade='all, delete-orphan')

    def __repr__(self):
        return f"<FetchRun(id={self.id}, source={self.source})>"


class Config(Base):
    __tablename__ = 'config'
    id = sa.Column(sa.BigInteger, primary_key=True, autoincrement=True)
    name = sa.Column(sa.String(128), nullable=False, unique=True)
    description = sa.Column(sa.Text, nullable=True)
    params = sa.Column(JSONB, nullable=True)
    active = sa.Column(sa.Boolean, nullable=False, server_default=sa.text('true'))
    created_at = sa.Column(sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False)

    scan_runs = orm.relationship('ScanRun', back_populates='config', cascade='all, delete-orphan')

    def __repr__(self):
        return f"<Config(id={self.id}, name={self.name})>"


# Enum for scan status
if PG_ENUM_AVAILABLE:
    scan_status_type = sa.Enum('pending', 'running', 'completed', 'failed', name='scanrunstatus')
else:
    scan_status_type = sa.Enum('pending', 'running', 'completed', 'failed', name='scanrunstatus', native_enum=False)


class ScanRun(Base):
    __tablename__ = 'scan_runs'
    id = sa.Column(sa.BigInteger, primary_key=True, autoincrement=True)
    started_at = sa.Column(sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False)
    finished_at = sa.Column(sa.TIMESTAMP(timezone=True), nullable=True)
    config_id = sa.Column(sa.BigInteger, sa.ForeignKey('config.id', ondelete='CASCADE'), nullable=False)
    status = sa.Column(scan_status_type, nullable=False, server_default='pending')
    stats = sa.Column(JSONB, nullable=True)
    created_at = sa.Column(sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False)

    config = orm.relationship('Config', back_populates='scan_runs')

    def __repr__(self):
        return f"<ScanRun(id={self.id}, status={self.status})>"


class Candle(Base):
    __tablename__ = 'candles'
    id = sa.Column(sa.BigInteger, primary_key=True, autoincrement=True)
    symbol_id = sa.Column(sa.BigInteger, sa.ForeignKey('symbols.id', ondelete='CASCADE'), nullable=False)
    timeframe = sa.Column(sa.String(16), nullable=False)
    open_time = sa.Column(sa.TIMESTAMP(timezone=True), nullable=False, index=True)
    close_time = sa.Column(sa.TIMESTAMP(timezone=True), nullable=True)
    open = sa.Column(sa.Numeric, nullable=False)
    high = sa.Column(sa.Numeric, nullable=False)
    low = sa.Column(sa.Numeric, nullable=False)
    close = sa.Column(sa.Numeric, nullable=False)
    volume = sa.Column(sa.Numeric, nullable=True)
    extra = sa.Column(JSONB, nullable=True)
    fetch_run_id = sa.Column(sa.BigInteger, sa.ForeignKey('fetch_runs.id', ondelete='CASCADE'), nullable=True)
    created_at = sa.Column(sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False)

    symbol = orm.relationship('Symbol', back_populates='candles')
    fetch_run = orm.relationship('FetchRun', back_populates='candles')

    __table_args__ = (
        sa.UniqueConstraint('symbol_id', 'timeframe', 'open_time', name='uq_candles_symbol_tf_open'),
    )

    def __repr__(self):
        return f"<Candle(symbol_id={self.symbol_id}, timeframe={self.timeframe}, open_time={self.open_time})>"

import os
import csv
from typing import Optional

import typer
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src import models

app = typer.Typer()


def get_database_url() -> str:
    return os.environ.get('DATABASE_URL') or os.environ.get('SQLALCHEMY_DATABASE_URL') or 'sqlite:///./data/dev.db'


def get_session():
    url = get_database_url()
    engine = create_engine(url)
    Session = sessionmaker(bind=engine)
    return Session()


@app.command()
def seed_db(csv_path: Optional[str] = typer.Option(None, "--csv", help="Path to CSV file of candles")):
    """Seed DB with example symbols and candles."""
    session = get_session()
    # create tables if needed
    models.Base.metadata.create_all(bind=session.get_bind())

    # add sample symbols
    for name in ("BTCUSDT", "ETHUSDT"):
        sym = session.query(models.Symbol).filter_by(name=name).one_or_none()
        if not sym:
            sym = models.Symbol(name=name)
            session.add(sym)
    session.commit()

    csv_path = csv_path or os.path.join(os.path.dirname(__file__), '..', 'scripts', 'sample_candles.csv')
    csv_path = os.path.abspath(csv_path)
    if os.path.exists(csv_path):
        with open(csv_path, newline='') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # simple parse; use UTC naive timestamps for sqlite
                symbol_name = row.get('symbol') or 'BTCUSDT'
                symbol = session.query(models.Symbol).filter_by(name=symbol_name).one()
                from datetime import datetime
                def parse_dt(s: str):
                    if not s:
                        return None
                    if s.endswith('Z'):
                        s = s[:-1]
                    try:
                        return datetime.fromisoformat(s)
                    except Exception:
                        return None

                def parse_num(s: str):
                    try:
                        return float(s)
                    except Exception:
                        return None

                candle = models.Candle(
                    symbol_id=symbol.id,
                    timeframe=row.get('timeframe') or '1m',
                    open_time=parse_dt(row.get('time')),
                    open=parse_num(row.get('open')) or 0,
                    high=parse_num(row.get('high')) or 0,
                    low=parse_num(row.get('low')) or 0,
                    close=parse_num(row.get('close')) or 0,
                    volume=parse_num(row.get('volume')) or 0,
                )
                session.add(candle)
        session.commit()
        typer.echo(f"Seeded candles from {csv_path}")
    else:
        typer.echo(f"CSV not found at {csv_path}; seeded symbols only")


@app.command()
def list_symbols():
    """List all symbols in the DB."""
    session = get_session()
    models.Base.metadata.create_all(bind=session.get_bind())
    syms = session.query(models.Symbol).order_by(models.Symbol.name).all()
    for s in syms:
        typer.echo(f"{s.id}\t{s.name}")


@app.command()
def add_symbol(name: str):
    """Add a new symbol."""
    session = get_session()
    models.Base.metadata.create_all(bind=session.get_bind())
    existing = session.query(models.Symbol).filter_by(name=name).one_or_none()
    if existing:
        typer.echo(f"Symbol {name} already exists (id={existing.id})")
        raise typer.Exit(code=1)
    sym = models.Symbol(name=name)
    session.add(sym)
    session.commit()
    typer.echo(f"Added symbol {name} (id={sym.id})")


@app.command()
def show_config():
    """Show config entries."""
    session = get_session()
    models.Base.metadata.create_all(bind=session.get_bind())
    configs = session.query(models.Config).order_by(models.Config.name).all()
    for c in configs:
        typer.echo(f"{c.name}\t{c.params}")


@app.command()
def update_config(key: str, value: str):
    """Update or insert a config entry."""
    session = get_session()
    models.Base.metadata.create_all(bind=session.get_bind())
    cfg = session.query(models.Config).filter_by(name=key).one_or_none()
    if cfg:
        cfg.params = value
        session.add(cfg)
    else:
        cfg = models.Config(name=key, params=value)
        session.add(cfg)
    session.commit()
    typer.echo(f"Set config {key} = {value}")


if __name__ == '__main__':
    app()

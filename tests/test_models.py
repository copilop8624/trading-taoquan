import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timezone, timedelta

from src import models


@pytest.fixture
def engine():
    return create_engine('sqlite:///:memory:', echo=False)


@pytest.fixture
def tables(engine):
    models.Base.metadata.create_all(engine)
    yield
    models.Base.metadata.drop_all(engine)


@pytest.fixture
def dbsession(engine, tables):
    Session = sessionmaker(bind=engine)
    s = Session()
    try:
        yield s
    finally:
        s.close()


def test_basic_inserts(dbsession):
    # create symbol
    sym = models.Symbol(name='BTCUSDT', description='Test pair', base_asset='BTC', quote_asset='USDT')
    dbsession.add(sym)
    dbsession.commit()
    assert sym.id is not None

    # create fetch run
    fr = models.FetchRun(source='binance_csv', notes='test fetch')
    dbsession.add(fr)
    dbsession.commit()
    assert fr.id is not None

    # insert a few candles from CSV-like rows
    open_time = datetime.now(timezone.utc).replace(microsecond=0)
    rows = [
        {
            'time': open_time,
            'open': 6.61,
            'high': 7.5694,
            'low': 6.535,
            'close': 7.3808,
            'volume': 7593739.9,
            'quote_volume': 123.45,
            'trades_count': 500
        },
        {
            'time': open_time + timedelta(minutes=1),
            'open': 7.38,
            'high': 7.58,
            'low': 7.30,
            'close': 7.50,
            'volume': 1000.0,
            'quote_volume': 200.5,
            'trades_count': 10
        }
    ]

    # refresh sym id in session
    dbsession.refresh(sym)

    for r in rows:
        c = models.Candle(
            symbol_id=sym.id,
            timeframe='1m',
            open_time=r['time'],
            close_time=r['time'] + timedelta(minutes=1),
            open=r['open'],
            high=r['high'],
            low=r['low'],
            close=r['close'],
            volume=r['volume'],
            extra={'quote_volume': r['quote_volume'], 'trades_count': r['trades_count']},
            fetch_run_id=fr.id
        )
        dbsession.add(c)
    dbsession.commit()

    # query back
    candles = dbsession.query(models.Candle).filter_by(symbol_id=sym.id).order_by(models.Candle.open_time).all()
    assert len(candles) == 2
    assert candles[0].extra['quote_volume'] == 123.45
    assert candles[1].extra['trades_count'] == 10

    # create config and scan_run
    cfg = models.Config(name='daily_scan', description='Daily scan config', params={'lookback_days': 7}, active=True)
    dbsession.add(cfg)
    dbsession.commit()
    assert cfg.id is not None

    sr = models.ScanRun(config_id=cfg.id, status='pending', stats={'symbols_scanned': 1})
    dbsession.add(sr)
    dbsession.commit()
    assert sr.id is not None

    # verify relationships
    got_cfg = dbsession.query(models.Config).filter_by(name='daily_scan').one()
    assert len(got_cfg.scan_runs) == 1
    assert got_cfg.scan_runs[0].id == sr.id

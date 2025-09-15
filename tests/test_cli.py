import os
import sys
from pathlib import Path
import pytest
from typer.testing import CliRunner

# Ensure repo root is importable as `src`
repo_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(repo_root))

from src import cli
from src import models

runner = CliRunner()


@pytest.fixture(autouse=True)
def set_sqlite_env(tmp_path):
    # Use a temporary file-based SQLite DB so multiple commands in the same test see the same DB
    db_file = tmp_path / 'test.db'
    os.environ['DATABASE_URL'] = f"sqlite:///{db_file}"
    yield
    os.environ.pop('DATABASE_URL', None)


def test_seed_db_and_list_symbols(tmp_path):
    # create a small CSV file
    csv_path = tmp_path / 'sample.csv'
    csv_path.write_text('time,symbol,timeframe,open,high,low,close,volume\n2025-09-15T00:00:00Z,BTCUSDT,1m,1,2,0.5,1.5,10\n')

    # seed DB
    result = runner.invoke(cli.app, ['seed-db', '--csv', str(csv_path)])
    assert result.exit_code == 0

    # list symbols should show BTCUSDT
    result = runner.invoke(cli.app, ['list-symbols'])
    assert 'BTCUSDT' in result.stdout


def test_add_symbol_and_duplicate(tmp_path):
    # Add a new symbol
    result = runner.invoke(cli.app, ['add-symbol', 'TESTUSD'])
    assert result.exit_code == 0
    assert 'Added symbol TESTUSD' in result.stdout

    # Adding again should error
    result = runner.invoke(cli.app, ['add-symbol', 'TESTUSD'])
    assert result.exit_code != 0

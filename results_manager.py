"""
Results Manager - Layer 4: Results Management
Quản lý kết quả backtest, indexing, storage, và query API
Tích hợp với optimization_log_manager và SQLite database
"""

import sqlite3
import pandas as pd
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
import hashlib
from dataclasses import dataclass
from optimization_log_manager import OptimizationLogManager

@dataclass
class BacktestResult:
    """Standard backtest result structure"""
    id: str
    symbol: str
    timeframe: str
    strategy: str
    parameters: Dict[str, Any]
    metrics: Dict[str, float]
    details: List[Dict]
    metadata: Dict[str, Any]
    created_at: datetime

class ResultsManager:
    """
    Centralized results management with fast indexing and query
    - Store backtest results in SQLite with proper indexing
    - Fast query by symbol, timeframe, strategy, date range
    - Integration with existing optimization_log_manager
    - Export/import capabilities
    """
    
    def __init__(self, db_path: str = "backtest_results.db"):
        self.db_path = db_path
        self.opt_log_manager = OptimizationLogManager()
        
        # Initialize database
        self._init_database()
        
    def _init_database(self):
        """Initialize results database with proper schema and indexes"""
        
        with sqlite3.connect(self.db_path) as conn:
            # Create main results table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS backtest_results (
                    id TEXT PRIMARY KEY,
                    symbol TEXT NOT NULL,
                    timeframe TEXT NOT NULL,
                    strategy TEXT NOT NULL,
                    parameters_json TEXT NOT NULL,
                    metrics_json TEXT NOT NULL,
                    details_json TEXT,
                    metadata_json TEXT,
                    created_at TIMESTAMP NOT NULL,
                    user_id TEXT DEFAULT 'default',
                    project_name TEXT DEFAULT 'default',
                    
                    -- Extracted metrics for fast querying
                    total_pnl REAL,
                    winrate REAL,
                    profit_factor REAL,
                    max_drawdown REAL,
                    sharpe_ratio REAL,
                    total_trades INTEGER,
                    
                    -- Extracted parameters for fast filtering
                    sl_value REAL,
                    be_value REAL,
                    ts_trig_value REAL,
                    ts_step_value REAL
                )
            """)
            
            # Create indexes for fast querying
            indexes = [
                "CREATE INDEX IF NOT EXISTS idx_symbol ON backtest_results(symbol)",
                "CREATE INDEX IF NOT EXISTS idx_timeframe ON backtest_results(timeframe)", 
                "CREATE INDEX IF NOT EXISTS idx_strategy ON backtest_results(strategy)",
                "CREATE INDEX IF NOT EXISTS idx_created_at ON backtest_results(created_at)",
                "CREATE INDEX IF NOT EXISTS idx_total_pnl ON backtest_results(total_pnl)",
                "CREATE INDEX IF NOT EXISTS idx_winrate ON backtest_results(winrate)",
                "CREATE INDEX IF NOT EXISTS idx_profit_factor ON backtest_results(profit_factor)",
                "CREATE INDEX IF NOT EXISTS idx_symbol_timeframe ON backtest_results(symbol, timeframe)",
                "CREATE INDEX IF NOT EXISTS idx_symbol_strategy ON backtest_results(symbol, strategy)"
            ]
            
            for idx_sql in indexes:
                conn.execute(idx_sql)
            
            # Create summary view for quick statistics
            conn.execute("""
                CREATE VIEW IF NOT EXISTS results_summary AS
                SELECT 
                    symbol,
                    timeframe,
                    strategy,
                    COUNT(*) as total_runs,
                    AVG(total_pnl) as avg_pnl,
                    MAX(total_pnl) as best_pnl,
                    AVG(winrate) as avg_winrate,
                    MAX(winrate) as best_winrate,
                    AVG(profit_factor) as avg_pf,
                    MAX(profit_factor) as best_pf,
                    MAX(created_at) as last_run
                FROM backtest_results
                GROUP BY symbol, timeframe, strategy
            """)
            
            conn.commit()
    
    def store_result(self, 
                    symbol: str,
                    timeframe: str, 
                    strategy: str,
                    parameters: Dict[str, Any],
                    metrics: Dict[str, float],
                    details: List[Dict] = None,
                    metadata: Dict[str, Any] = None,
                    user_id: str = "default",
                    project_name: str = "default") -> str:
        """Store backtest result and return unique ID"""
        
        # Generate unique ID based on content
        content_hash = self._generate_result_id(symbol, timeframe, strategy, parameters, metrics)
        
        # Create result object
        result = BacktestResult(
            id=content_hash,
            symbol=symbol,
            timeframe=timeframe,
            strategy=strategy,
            parameters=parameters,
            metrics=metrics,
            details=details or [],
            metadata=metadata or {},
            created_at=datetime.now()
        )
        
        # Extract key metrics for fast querying
        extracted_metrics = self._extract_key_metrics(metrics)
        extracted_params = self._extract_key_parameters(parameters)
        
        # Store in database
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO backtest_results 
                (id, symbol, timeframe, strategy, parameters_json, metrics_json, 
                 details_json, metadata_json, created_at, user_id, project_name,
                 total_pnl, winrate, profit_factor, max_drawdown, sharpe_ratio, total_trades,
                 sl_value, be_value, ts_trig_value, ts_step_value)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                result.id,
                result.symbol,
                result.timeframe, 
                result.strategy,
                json.dumps(result.parameters),
                json.dumps(result.metrics),
                json.dumps(result.details),
                json.dumps(result.metadata),
                result.created_at,
                user_id,
                project_name,
                extracted_metrics.get('total_pnl'),
                extracted_metrics.get('winrate'),
                extracted_metrics.get('profit_factor'),
                extracted_metrics.get('max_drawdown'),
                extracted_metrics.get('sharpe_ratio'),
                extracted_metrics.get('total_trades'),
                extracted_params.get('sl'),
                extracted_params.get('be'),
                extracted_params.get('ts_trig'),
                extracted_params.get('ts_step')
            ))
            
            conn.commit()
        
        # Also log to optimization log manager for compatibility
        self._log_to_optimization_manager(symbol, timeframe, strategy, parameters, metrics, user_id, project_name)
        
        print(f"💾 Stored result: {symbol} {timeframe}m {strategy} -> {result.id[:8]}")
        return result.id
    
    def _generate_result_id(self, symbol: str, timeframe: str, strategy: str, 
                           parameters: Dict, metrics: Dict) -> str:
        """Generate unique ID for result based on content"""
        content = f"{symbol}_{timeframe}_{strategy}_{json.dumps(parameters, sort_keys=True)}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def _extract_key_metrics(self, metrics: Dict[str, float]) -> Dict[str, Optional[float]]:
        """Extract key metrics for indexing"""
        return {
            'total_pnl': metrics.get('total_pnl') or metrics.get('pnl_total') or metrics.get('pnl'),
            'winrate': metrics.get('winrate') or metrics.get('win_rate'),
            'profit_factor': metrics.get('profit_factor') or metrics.get('pf'),
            'max_drawdown': metrics.get('max_drawdown') or metrics.get('drawdown'),
            'sharpe_ratio': metrics.get('sharpe_ratio') or metrics.get('sharpe'),
            'total_trades': metrics.get('total_trades') or metrics.get('count')
        }
    
    def _extract_key_parameters(self, parameters: Dict[str, Any]) -> Dict[str, Optional[float]]:
        """Extract key parameters for indexing"""
        return {
            'sl': parameters.get('sl') or parameters.get('sl_value'),
            'be': parameters.get('be') or parameters.get('be_value'),
            'ts_trig': parameters.get('ts_trig') or parameters.get('ts_trigger'),
            'ts_step': parameters.get('ts_step') or parameters.get('ts_step_value')
        }
    
    def _log_to_optimization_manager(self, symbol: str, timeframe: str, strategy: str,
                                   parameters: Dict, metrics: Dict, user_id: str, project_name: str):
        """Log to existing optimization manager for compatibility"""
        try:
            # Extract parameter ranges (assume single values for now)
            param_ranges = {
                'sl_min': parameters.get('sl', 0),
                'sl_max': parameters.get('sl', 0),
                'be_min': parameters.get('be', 0),
                'be_max': parameters.get('be', 0),
                'ts_trig_min': parameters.get('ts_trig', 0),
                'ts_trig_max': parameters.get('ts_trig', 0),
                'ts_step_min': parameters.get('ts_step', 0),
                'ts_step_max': parameters.get('ts_step', 0)
            }
            
            best_result = {
                'params': parameters,
                'pnl': metrics.get('total_pnl') or metrics.get('pnl_total', 0),
                'winrate': metrics.get('winrate') or metrics.get('win_rate', 0),
                'pf': metrics.get('profit_factor') or metrics.get('pf', 0)
            }
            
            self.opt_log_manager.log_optimization(
                user=user_id,
                project=project_name,
                symbol=symbol,
                timeframe=timeframe,
                param_ranges=param_ranges,
                best_result=best_result,
                notes=f"Strategy: {strategy}"
            )
        except Exception as e:
            print(f"⚠️ Failed to log to optimization manager: {e}")
    
    def query_results(self,
                     symbol: Optional[str] = None,
                     timeframe: Optional[str] = None,
                     strategy: Optional[str] = None,
                     date_from: Optional[datetime] = None,
                     date_to: Optional[datetime] = None,
                     min_pnl: Optional[float] = None,
                     min_winrate: Optional[float] = None,
                     limit: int = 100,
                     order_by: str = "total_pnl",
                     ascending: bool = False) -> List[BacktestResult]:
        """Query results with flexible filtering and sorting"""
        
        # Build SQL query
        where_conditions = []
        params = []
        
        if symbol:
            where_conditions.append("symbol = ?")
            params.append(symbol)
        
        if timeframe:
            where_conditions.append("timeframe = ?")
            params.append(timeframe)
        
        if strategy:
            where_conditions.append("strategy = ?")
            params.append(strategy)
        
        if date_from:
            where_conditions.append("created_at >= ?")
            params.append(date_from)
        
        if date_to:
            where_conditions.append("created_at <= ?")
            params.append(date_to)
        
        if min_pnl is not None:
            where_conditions.append("total_pnl >= ?")
            params.append(min_pnl)
        
        if min_winrate is not None:
            where_conditions.append("winrate >= ?")
            params.append(min_winrate)
        
        where_clause = "WHERE " + " AND ".join(where_conditions) if where_conditions else ""
        order_direction = "ASC" if ascending else "DESC"
        
        sql = f"""
            SELECT * FROM backtest_results 
            {where_clause}
            ORDER BY {order_by} {order_direction}
            LIMIT ?
        """
        params.append(limit)
        
        # Execute query
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(sql, params)
            rows = cursor.fetchall()
        
        # Convert to BacktestResult objects
        results = []
        for row in rows:
            result = BacktestResult(
                id=row['id'],
                symbol=row['symbol'],
                timeframe=row['timeframe'],
                strategy=row['strategy'],
                parameters=json.loads(row['parameters_json']),
                metrics=json.loads(row['metrics_json']),
                details=json.loads(row['details_json']) if row['details_json'] else [],
                metadata=json.loads(row['metadata_json']) if row['metadata_json'] else {},
                created_at=datetime.fromisoformat(row['created_at'])
            )
            results.append(result)
        
        return results
    
    def get_best_results(self, 
                        symbol: str,
                        timeframe: str,
                        strategy: str = None,
                        metric: str = "total_pnl",
                        top_n: int = 5) -> List[BacktestResult]:
        """Get top N best results for a symbol/timeframe"""
        
        return self.query_results(
            symbol=symbol,
            timeframe=timeframe,
            strategy=strategy,
            limit=top_n,
            order_by=metric,
            ascending=False
        )
    
    def get_summary_statistics(self, 
                              symbol: Optional[str] = None,
                              timeframe: Optional[str] = None,
                              strategy: Optional[str] = None) -> Dict:
        """Get summary statistics for results"""
        
        where_conditions = []
        params = []
        
        if symbol:
            where_conditions.append("symbol = ?")
            params.append(symbol)
        
        if timeframe:
            where_conditions.append("timeframe = ?")
            params.append(timeframe)
        
        if strategy:
            where_conditions.append("strategy = ?")
            params.append(strategy)
        
        where_clause = "WHERE " + " AND ".join(where_conditions) if where_conditions else ""
        
        sql = f"""
            SELECT 
                COUNT(*) as total_runs,
                AVG(total_pnl) as avg_pnl,
                MAX(total_pnl) as best_pnl,
                MIN(total_pnl) as worst_pnl,
                AVG(winrate) as avg_winrate,
                MAX(winrate) as best_winrate,
                AVG(profit_factor) as avg_pf,
                MAX(profit_factor) as best_pf,
                COUNT(DISTINCT symbol) as unique_symbols,
                COUNT(DISTINCT timeframe) as unique_timeframes,
                COUNT(DISTINCT strategy) as unique_strategies
            FROM backtest_results
            {where_clause}
        """
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(sql, params)
            row = cursor.fetchone()
        
        return dict(row) if row else {}
    
    def get_available_symbols(self) -> List[str]:
        """Get list of symbols with results"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT DISTINCT symbol FROM backtest_results ORDER BY symbol")
            return [row[0] for row in cursor.fetchall()]
    
    def get_available_timeframes(self, symbol: Optional[str] = None) -> List[str]:
        """Get list of timeframes with results"""
        if symbol:
            sql = "SELECT DISTINCT timeframe FROM backtest_results WHERE symbol = ? ORDER BY timeframe"
            params = [symbol]
        else:
            sql = "SELECT DISTINCT timeframe FROM backtest_results ORDER BY timeframe"
            params = []
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(sql, params)
            return [row[0] for row in cursor.fetchall()]
    
    def get_available_strategies(self) -> List[str]:
        """Get list of strategies with results"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT DISTINCT strategy FROM backtest_results ORDER BY strategy")
            return [row[0] for row in cursor.fetchall()]
    
    def export_results(self, 
                      file_path: str,
                      symbol: Optional[str] = None,
                      timeframe: Optional[str] = None,
                      format: str = "csv") -> str:
        """Export results to CSV/JSON file"""
        
        results = self.query_results(symbol=symbol, timeframe=timeframe, limit=10000)
        
        if format.lower() == "csv":
            # Flatten results for CSV export
            rows = []
            for result in results:
                row = {
                    'id': result.id,
                    'symbol': result.symbol,
                    'timeframe': result.timeframe,
                    'strategy': result.strategy,
                    'created_at': result.created_at.isoformat(),
                    **{f"param_{k}": v for k, v in result.parameters.items()},
                    **{f"metric_{k}": v for k, v in result.metrics.items()}
                }
                rows.append(row)
            
            df = pd.DataFrame(rows)
            df.to_csv(file_path, index=False)
        
        elif format.lower() == "json":
            # Export as JSON
            data = []
            for result in results:
                data.append({
                    'id': result.id,
                    'symbol': result.symbol,
                    'timeframe': result.timeframe,
                    'strategy': result.strategy,
                    'parameters': result.parameters,
                    'metrics': result.metrics,
                    'details': result.details,
                    'metadata': result.metadata,
                    'created_at': result.created_at.isoformat()
                })
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        
        print(f"📤 Exported {len(results)} results to {file_path}")
        return file_path
    
    def compare_results(self, result_ids: List[str]) -> Dict:
        """Compare multiple results side by side"""
        
        results = []
        for result_id in result_ids:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("SELECT * FROM backtest_results WHERE id = ?", [result_id])
                row = cursor.fetchone()
                if row:
                    results.append(dict(row))
        
        if not results:
            return {'error': 'No results found for given IDs'}
        
        # Create comparison
        comparison = {
            'results': results,
            'comparison_matrix': self._create_comparison_matrix(results),
            'winner_analysis': self._analyze_winners(results)
        }
        
        return comparison
    
    def _create_comparison_matrix(self, results: List[Dict]) -> Dict:
        """Create side-by-side comparison matrix"""
        if not results:
            return {}
        
        # Key metrics to compare
        metrics = ['total_pnl', 'winrate', 'profit_factor', 'max_drawdown', 'total_trades']
        
        matrix = {}
        for metric in metrics:
            matrix[metric] = []
            for result in results:
                value = result.get(metric)
                matrix[metric].append(value)
        
        return matrix
    
    def _analyze_winners(self, results: List[Dict]) -> Dict:
        """Analyze which result wins in each category"""
        if not results:
            return {}
        
        analysis = {}
        metrics = ['total_pnl', 'winrate', 'profit_factor']
        
        for metric in metrics:
            values = [(i, result.get(metric, 0)) for i, result in enumerate(results)]
            values = [(i, v) for i, v in values if v is not None]
            
            if values:
                winner_idx, winner_value = max(values, key=lambda x: x[1])
                analysis[metric] = {
                    'winner_index': winner_idx,
                    'winner_value': winner_value,
                    'winner_id': results[winner_idx]['id']
                }
        
        return analysis

# Global instance
results_manager = ResultsManager()

def get_results_manager() -> ResultsManager:
    """Get global results manager instance"""
    return results_manager

if __name__ == "__main__":
    # Test the results manager
    rm = ResultsManager()
    
    print("\n=== Results Manager Test ===")
    
    # Test storing a sample result
    sample_params = {'sl': 2.5, 'be': 3.0, 'ts_trig': 4.0, 'ts_step': 0.5}
    sample_metrics = {'total_pnl': 125.5, 'winrate': 65.2, 'profit_factor': 1.8, 'total_trades': 50}
    
    result_id = rm.store_result(
        symbol="BTCUSDT",
        timeframe="60",
        strategy="SL_BE_TS_V3",
        parameters=sample_params,
        metrics=sample_metrics,
        metadata={'test': True}
    )
    
    print(f"Stored test result: {result_id}")
    
    # Test querying
    results = rm.query_results(symbol="BTCUSDT", limit=5)
    print(f"Query returned {len(results)} results")
    
    # Test summary
    summary = rm.get_summary_statistics()
    print(f"Summary: {summary}")
    
    # Test available data
    symbols = rm.get_available_symbols()
    timeframes = rm.get_available_timeframes()
    strategies = rm.get_available_strategies()
    
    print(f"Available: {len(symbols)} symbols, {len(timeframes)} timeframes, {len(strategies)} strategies")
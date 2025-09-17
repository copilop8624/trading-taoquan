"""
Multi-Symbol Batch Processor - Production-Ready Engine
Tích hợp data_manager, tradelist_manager, results_manager
Advanced batch optimization với parallel processing
"""

import os
import sys
import threading
import multiprocessing
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
import time
import json
import traceback
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union, Tuple
from dataclasses import dataclass, asdict
import pandas as pd
import numpy as np
import optuna
from pathlib import Path

# Import our managers
from data_manager import DataManager, get_data_manager
from results_manager import ResultsManager, get_results_manager
from src.tradelist_manager import TradelistManager

# Import backtest engine
try:
    from backtest_gridsearch_slbe_ts_Version3 import (
        simulate_trade, grid_search_parallel
    )
    ADVANCED_MODE = True
except ImportError:
    print("⚠️ Advanced backtest engine not available, using fallback mode")
    ADVANCED_MODE = False

@dataclass
class BatchConfig:
    """Batch optimization configuration"""
    symbols: List[str]
    timeframes: List[str]
    sl_range: Tuple[float, float, float]  # min, max, step
    be_range: Tuple[float, float, float]
    ts_trig_range: Tuple[float, float, float]
    ts_step_range: Tuple[float, float, float]
    optimization_method: str = "optuna"  # "optuna" or "grid"
    n_trials: int = 500
    timeout_per_symbol: int = 300  # 5 minutes per symbol
    parallel_symbols: int = 2  # Max parallel symbol processing
    save_results: bool = True
    generate_reports: bool = True
    user_id: str = "batch_user"
    project_name: str = "multi_symbol_batch"

@dataclass
class SymbolProgress:
    """Track progress for individual symbol"""
    symbol: str
    timeframe: str
    status: str = "pending"  # pending, running, completed, error
    progress: float = 0.0
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    best_result: Optional[Dict] = None
    error_message: Optional[str] = None
    trials_completed: int = 0
    total_trials: int = 0

@dataclass
class BatchResult:
    """Complete batch processing result"""
    batch_id: str
    config: BatchConfig
    symbol_results: List[SymbolProgress]
    start_time: datetime
    end_time: Optional[datetime] = None
    total_symbols: int = 0
    completed_symbols: int = 0
    failed_symbols: int = 0
    best_overall: Optional[Dict] = None
    summary_stats: Optional[Dict] = None

class MultiSymbolProcessor:
    """
    Production-ready multi-symbol batch processor
    Features:
    - Parallel processing with configurable workers
    - Real-time progress tracking
    - Error handling and recovery
    - Results storage and reporting
    - Resource management and timeouts
    """
    
    def __init__(self):
        self.data_manager = get_data_manager()
        self.results_manager = get_results_manager()
        self.tradelist_manager = TradelistManager()
        
        # Active batch tracking
        self.active_batches: Dict[str, BatchResult] = {}
        self.batch_lock = threading.Lock()
        
        # Performance monitoring
        self.start_time = None
        self.stats = {
            'total_batches': 0,
            'total_symbols_processed': 0,
            'total_optimizations': 0,
            'avg_time_per_symbol': 0.0
        }
        
        print("✅ Multi-Symbol Processor initialized")
        
    def start_batch(self, config: BatchConfig) -> str:
        """Start a new batch optimization process"""
        
        # Generate unique batch ID
        batch_id = f"batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{len(self.active_batches)}"
        
        # Create batch result tracker
        batch_result = BatchResult(
            batch_id=batch_id,
            config=config,
            symbol_results=[],
            start_time=datetime.now(),
            total_symbols=len(config.symbols) * len(config.timeframes)
        )
        
        # Initialize symbol progress tracking
        for symbol in config.symbols:
            for timeframe in config.timeframes:
                progress = SymbolProgress(
                    symbol=symbol,
                    timeframe=timeframe,
                    total_trials=config.n_trials if config.optimization_method == "optuna" else self._calculate_grid_size(config)
                )
                batch_result.symbol_results.append(progress)
        
        # Store batch
        with self.batch_lock:
            self.active_batches[batch_id] = batch_result
        
        # Start processing in background thread
        thread = threading.Thread(target=self._process_batch, args=(batch_id,))
        thread.daemon = True
        thread.start()
        
        print(f"🚀 Started batch {batch_id}: {batch_result.total_symbols} symbol-timeframe combinations")
        return batch_id
    
    def get_batch_status(self, batch_id: str) -> Optional[BatchResult]:
        """Get current status of a batch"""
        with self.batch_lock:
            return self.active_batches.get(batch_id)
    
    def cancel_batch(self, batch_id: str) -> bool:
        """Cancel a running batch"""
        with self.batch_lock:
            if batch_id in self.active_batches:
                batch = self.active_batches[batch_id]
                # Mark all pending/running as cancelled
                for progress in batch.symbol_results:
                    if progress.status in ["pending", "running"]:
                        progress.status = "cancelled"
                        progress.end_time = datetime.now()
                batch.end_time = datetime.now()
                return True
        return False
    
    def _process_batch(self, batch_id: str):
        """Process entire batch with parallel execution"""
        try:
            batch = self.active_batches[batch_id]
            config = batch.config
            
            print(f"📊 Processing batch {batch_id} with {config.parallel_symbols} parallel workers")
            
            # Group symbol-timeframe combinations
            symbol_tasks = []
            for symbol in config.symbols:
                for timeframe in config.timeframes:
                    symbol_tasks.append((symbol, timeframe))
            
            # Process with ThreadPoolExecutor for I/O bound tasks
            with ThreadPoolExecutor(max_workers=config.parallel_symbols) as executor:
                # Submit all tasks
                future_to_task = {}
                for symbol, timeframe in symbol_tasks:
                    future = executor.submit(self._process_symbol, batch_id, symbol, timeframe)
                    future_to_task[future] = (symbol, timeframe)
                
                # Collect results as they complete
                for future in as_completed(future_to_task):
                    symbol, timeframe = future_to_task[future]
                    try:
                        result = future.result(timeout=config.timeout_per_symbol)
                        print(f"✅ Completed {symbol} {timeframe}m: {result.get('pnl', 0):.2f} PnL")
                        batch.completed_symbols += 1
                    except Exception as e:
                        print(f"❌ Failed {symbol} {timeframe}m: {e}")
                        batch.failed_symbols += 1
                        self._mark_symbol_error(batch_id, symbol, timeframe, str(e))
            
            # Finalize batch
            batch.end_time = datetime.now()
            batch.summary_stats = self._generate_batch_summary(batch_id)
            
            # Generate reports if requested
            if config.generate_reports:
                self._generate_batch_report(batch_id)
            
            # Update global stats
            self.stats['total_batches'] += 1
            self.stats['total_symbols_processed'] += batch.completed_symbols
            
            elapsed = (batch.end_time - batch.start_time).total_seconds()
            print(f"🎯 Batch {batch_id} completed: {batch.completed_symbols}/{batch.total_symbols} successful in {elapsed:.1f}s")
            
        except Exception as e:
            print(f"❌ Batch {batch_id} failed: {e}")
            traceback.print_exc()
            with self.batch_lock:
                if batch_id in self.active_batches:
                    self.active_batches[batch_id].end_time = datetime.now()
    
    def _process_symbol(self, batch_id: str, symbol: str, timeframe: str) -> Dict:
        """Process single symbol-timeframe combination"""
        
        progress = self._get_symbol_progress(batch_id, symbol, timeframe)
        if not progress:
            raise ValueError(f"Progress tracker not found for {symbol} {timeframe}")
        
        try:
            # Mark as running
            progress.status = "running"
            progress.start_time = datetime.now()
            
            # Load candle data
            candle_data = self.data_manager.load_candle_data(symbol, timeframe)
            if candle_data is None or candle_data.empty:
                raise ValueError(f"No candle data for {symbol} {timeframe}m")
            
            # Load tradelist data
            tradelist_files = self.data_manager._discover_tradelist_files(symbol)
            if not tradelist_files:
                raise ValueError(f"No tradelist files for {symbol}")
            
            trade_data = self.tradelist_manager.load_tradelist(tradelist_files[0])
            if trade_data is None or trade_data.empty:
                raise ValueError(f"No trade data for {symbol}")
            
            # Get trade pairs
            trade_pairs, trade_log = self.tradelist_manager.get_trade_pairs(trade_data)
            if not trade_pairs:
                raise ValueError(f"No valid trade pairs for {symbol}")
            
            print(f"🔄 Optimizing {symbol} {timeframe}m: {len(trade_pairs)} trades, {len(candle_data)} candles")
            
            # Run optimization
            batch = self.active_batches[batch_id]
            config = batch.config
            
            if config.optimization_method == "optuna":
                best_result = self._run_optuna_optimization(
                    progress, trade_pairs, candle_data, config
                )
            else:
                best_result = self._run_grid_optimization(
                    progress, trade_pairs, candle_data, config
                )
            
            if not best_result:
                raise ValueError("Optimization returned no results")
            
            # Store results
            if config.save_results:
                result_id = self.results_manager.store_result(
                    symbol=symbol,
                    timeframe=str(timeframe),
                    strategy="SL_BE_TS_V3_BATCH",
                    parameters=best_result.get('params', {}),
                    metrics=best_result,
                    metadata={
                        'batch_id': batch_id,
                        'optimization_method': config.optimization_method,
                        'trials': progress.trials_completed,
                        'processing_time': (datetime.now() - progress.start_time).total_seconds()
                    },
                    user_id=config.user_id,
                    project_name=config.project_name
                )
                best_result['result_id'] = result_id
            
            # Update progress
            progress.status = "completed"
            progress.end_time = datetime.now()
            progress.best_result = best_result
            progress.progress = 100.0
            
            return best_result
            
        except Exception as e:
            progress.status = "error"
            progress.end_time = datetime.now()
            progress.error_message = str(e)
            progress.progress = 0.0
            raise e
    
    def _run_optuna_optimization(self, progress: SymbolProgress, trade_pairs: List, 
                                candle_data: pd.DataFrame, config: BatchConfig) -> Dict:
        """Run Optuna optimization with progress tracking"""
        
        if not ADVANCED_MODE:
            raise ValueError("Advanced optimization not available")
        
        def objective(trial):
            # Update progress
            progress.trials_completed = len(trial.study.trials)
            progress.progress = (progress.trials_completed / config.n_trials) * 100
            
            # Sample parameters
            sl = trial.suggest_float('sl', config.sl_range[0], config.sl_range[1])
            be = trial.suggest_float('be', config.be_range[0], config.be_range[1])
            ts_trig = trial.suggest_float('ts_trig', config.ts_trig_range[0], config.ts_trig_range[1])
            ts_step = trial.suggest_float('ts_step', config.ts_step_range[0], config.ts_step_range[1])
            
            # Run simulation
            performance, log = simulate_trade(
                trade_pairs, candle_data, sl, be, ts_trig, ts_step, "pnl"
            )
            
            if performance is None:
                return -10000  # Heavy penalty for failed simulation
            
            return performance.get('pnl', -10000)
        
        # Create study with progress callback
        study = optuna.create_study(direction='maximize')
        
        # Optimize with timeout
        try:
            study.optimize(
                objective, 
                n_trials=config.n_trials,
                timeout=config.timeout_per_symbol - 30  # Leave 30s buffer
            )
        except Exception as e:
            print(f"⚠️ Optuna optimization interrupted: {e}")
        
        # Get best result
        if not study.trials:
            return None
        
        best_trial = study.best_trial
        best_params = best_trial.params
        
        # Run final simulation with best parameters
        final_performance, final_log = simulate_trade(
            trade_pairs, candle_data,
            best_params['sl'], best_params['be'],
            best_params['ts_trig'], best_params['ts_step'],
            "pnl"
        )
        
        if final_performance:
            final_performance['params'] = best_params
            final_performance['optuna_trials'] = len(study.trials)
            final_performance['best_value'] = best_trial.value
            return final_performance
        
        return None
    
    def _run_grid_optimization(self, progress: SymbolProgress, trade_pairs: List,
                              candle_data: pd.DataFrame, config: BatchConfig) -> Dict:
        """Run grid search optimization with progress tracking"""
        
        if not ADVANCED_MODE:
            raise ValueError("Advanced optimization not available")
        
        # Generate parameter lists
        sl_list = list(np.arange(config.sl_range[0], config.sl_range[1] + config.sl_range[2], config.sl_range[2]))
        be_list = list(np.arange(config.be_range[0], config.be_range[1] + config.be_range[2], config.be_range[2]))
        ts_trig_list = list(np.arange(config.ts_trig_range[0], config.ts_trig_range[1] + config.ts_trig_range[2], config.ts_trig_range[2]))
        ts_step_list = list(np.arange(config.ts_step_range[0], config.ts_step_range[1] + config.ts_step_range[2], config.ts_step_range[2]))
        
        total_combinations = len(sl_list) * len(be_list) * len(ts_trig_list) * len(ts_step_list)
        progress.total_trials = total_combinations
        
        print(f"🔢 Grid search: {total_combinations} combinations")
        
        # Run grid search
        results = grid_search_parallel(
            trade_pairs, candle_data, sl_list, be_list, ts_trig_list, ts_step_list, "pnl"
        )
        
        # Update progress
        progress.trials_completed = total_combinations
        progress.progress = 100.0
        
        if not results:
            return None
        
        # Find best result
        best_result = max(results, key=lambda x: x.get('pnl', -10000))
        best_result['grid_combinations'] = total_combinations
        
        return best_result
    
    def _calculate_grid_size(self, config: BatchConfig) -> int:
        """Calculate total grid search combinations"""
        sl_count = int((config.sl_range[1] - config.sl_range[0]) / config.sl_range[2]) + 1
        be_count = int((config.be_range[1] - config.be_range[0]) / config.be_range[2]) + 1
        ts_trig_count = int((config.ts_trig_range[1] - config.ts_trig_range[0]) / config.ts_trig_range[2]) + 1
        ts_step_count = int((config.ts_step_range[1] - config.ts_step_range[0]) / config.ts_step_range[2]) + 1
        
        return sl_count * be_count * ts_trig_count * ts_step_count
    
    def _get_symbol_progress(self, batch_id: str, symbol: str, timeframe: str) -> Optional[SymbolProgress]:
        """Get progress tracker for specific symbol-timeframe"""
        batch = self.active_batches.get(batch_id)
        if not batch:
            return None
        
        for progress in batch.symbol_results:
            if progress.symbol == symbol and progress.timeframe == timeframe:
                return progress
        
        return None
    
    def _mark_symbol_error(self, batch_id: str, symbol: str, timeframe: str, error_msg: str):
        """Mark symbol as failed with error message"""
        progress = self._get_symbol_progress(batch_id, symbol, timeframe)
        if progress:
            progress.status = "error"
            progress.end_time = datetime.now()
            progress.error_message = error_msg
            progress.progress = 0.0
    
    def _generate_batch_summary(self, batch_id: str) -> Dict:
        """Generate summary statistics for completed batch"""
        batch = self.active_batches.get(batch_id)
        if not batch:
            return {}
        
        successful_results = [p.best_result for p in batch.symbol_results 
                            if p.status == "completed" and p.best_result]
        
        if not successful_results:
            return {'status': 'no_successful_results'}
        
        # Calculate summary statistics
        pnls = [r.get('pnl', 0) for r in successful_results]
        winrates = [r.get('winrate', 0) for r in successful_results]
        profit_factors = [r.get('pf', 0) for r in successful_results]
        
        summary = {
            'total_symbols_attempted': batch.total_symbols,
            'successful_optimizations': len(successful_results),
            'failed_optimizations': batch.failed_symbols,
            'success_rate': len(successful_results) / batch.total_symbols * 100,
            'best_pnl': max(pnls) if pnls else 0,
            'avg_pnl': np.mean(pnls) if pnls else 0,
            'worst_pnl': min(pnls) if pnls else 0,
            'best_winrate': max(winrates) if winrates else 0,
            'avg_winrate': np.mean(winrates) if winrates else 0,
            'best_profit_factor': max(profit_factors) if profit_factors else 0,
            'avg_profit_factor': np.mean(profit_factors) if profit_factors else 0,
            'processing_time': (batch.end_time - batch.start_time).total_seconds(),
            'avg_time_per_symbol': (batch.end_time - batch.start_time).total_seconds() / batch.total_symbols
        }
        
        # Find overall best result
        best_result = max(successful_results, key=lambda x: x.get('pnl', -10000))
        batch.best_overall = best_result
        
        return summary
    
    def _generate_batch_report(self, batch_id: str):
        """Generate detailed batch report"""
        try:
            batch = self.active_batches[batch_id]
            
            # Create reports directory
            reports_dir = Path("reports") / f"batch_{batch_id}"
            reports_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate summary report
            summary_data = {
                'batch_info': {
                    'batch_id': batch_id,
                    'start_time': batch.start_time.isoformat(),
                    'end_time': batch.end_time.isoformat() if batch.end_time else None,
                    'configuration': asdict(batch.config)
                },
                'results_summary': batch.summary_stats,
                'symbol_results': []
            }
            
            # Add detailed symbol results
            for progress in batch.symbol_results:
                symbol_data = {
                    'symbol': progress.symbol,
                    'timeframe': progress.timeframe,
                    'status': progress.status,
                    'progress': progress.progress,
                    'trials_completed': progress.trials_completed,
                    'processing_time': (progress.end_time - progress.start_time).total_seconds() if progress.start_time and progress.end_time else None,
                    'best_result': progress.best_result,
                    'error_message': progress.error_message
                }
                summary_data['symbol_results'].append(symbol_data)
            
            # Save JSON report
            with open(reports_dir / "batch_summary.json", 'w', encoding='utf-8') as f:
                json.dump(summary_data, f, indent=2, ensure_ascii=False, default=str)
            
            # Generate CSV export for successful results
            successful_results = []
            for progress in batch.symbol_results:
                if progress.status == "completed" and progress.best_result:
                    row = {
                        'symbol': progress.symbol,
                        'timeframe': progress.timeframe,
                        'pnl': progress.best_result.get('pnl', 0),
                        'winrate': progress.best_result.get('winrate', 0),
                        'profit_factor': progress.best_result.get('pf', 0),
                        'total_trades': progress.best_result.get('num', 0),
                        'sl': progress.best_result.get('params', {}).get('sl', 0),
                        'be': progress.best_result.get('params', {}).get('be', 0),
                        'ts_trig': progress.best_result.get('params', {}).get('ts_trig', 0),
                        'ts_step': progress.best_result.get('params', {}).get('ts_step', 0),
                        'trials': progress.trials_completed,
                        'processing_time': (progress.end_time - progress.start_time).total_seconds() if progress.start_time and progress.end_time else None
                    }
                    successful_results.append(row)
            
            if successful_results:
                df_results = pd.DataFrame(successful_results)
                df_results.to_csv(reports_dir / "batch_results.csv", index=False)
            
            print(f"📋 Generated batch report: {reports_dir}")
            
        except Exception as e:
            print(f"⚠️ Failed to generate batch report: {e}")
    
    def get_all_batches(self) -> List[BatchResult]:
        """Get list of all batches"""
        with self.batch_lock:
            return list(self.active_batches.values())
    
    def cleanup_completed_batches(self, hours_old: int = 24):
        """Clean up old completed batches to free memory"""
        cutoff_time = datetime.now() - timedelta(hours=hours_old)
        
        with self.batch_lock:
            to_remove = []
            for batch_id, batch in self.active_batches.items():
                if (batch.end_time and batch.end_time < cutoff_time and
                    all(p.status in ["completed", "error", "cancelled"] for p in batch.symbol_results)):
                    to_remove.append(batch_id)
            
            for batch_id in to_remove:
                del self.active_batches[batch_id]
        
        if to_remove:
            print(f"🧹 Cleaned up {len(to_remove)} old batches")
    
    def get_performance_stats(self) -> Dict:
        """Get overall processor performance statistics"""
        return {
            **self.stats,
            'active_batches': len(self.active_batches),
            'total_memory_batches': len(self.active_batches)
        }

# Global processor instance
_processor_instance = None

def get_multi_symbol_processor() -> MultiSymbolProcessor:
    """Get global multi-symbol processor instance"""
    global _processor_instance
    if _processor_instance is None:
        _processor_instance = MultiSymbolProcessor()
    return _processor_instance

# Convenience functions for easy integration
def start_batch_optimization(symbols: List[str], timeframes: List[str], 
                           sl_range: Tuple[float, float, float] = (1.0, 5.0, 0.5),
                           be_range: Tuple[float, float, float] = (0.5, 3.0, 0.5),
                           ts_trig_range: Tuple[float, float, float] = (1.0, 4.0, 0.5),
                           ts_step_range: Tuple[float, float, float] = (0.1, 1.0, 0.1),
                           optimization_method: str = "optuna",
                           n_trials: int = 500,
                           parallel_symbols: int = 2) -> str:
    """
    Start batch optimization with simplified interface
    
    Returns:
        batch_id: Unique identifier for tracking progress
    """
    
    config = BatchConfig(
        symbols=symbols,
        timeframes=timeframes,
        sl_range=sl_range,
        be_range=be_range,
        ts_trig_range=ts_trig_range,
        ts_step_range=ts_step_range,
        optimization_method=optimization_method,
        n_trials=n_trials,
        parallel_symbols=parallel_symbols
    )
    
    processor = get_multi_symbol_processor()
    return processor.start_batch(config)

def get_batch_progress(batch_id: str) -> Optional[Dict]:
    """Get batch progress in simple dictionary format"""
    processor = get_multi_symbol_processor()
    batch = processor.get_batch_status(batch_id)
    
    if not batch:
        return None
    
    # Calculate overall progress
    total_progress = sum(p.progress for p in batch.symbol_results)
    avg_progress = total_progress / len(batch.symbol_results) if batch.symbol_results else 0
    
    # Get status summary
    status_counts = {}
    for progress in batch.symbol_results:
        status_counts[progress.status] = status_counts.get(progress.status, 0) + 1
    
    return {
        'batch_id': batch_id,
        'overall_progress': avg_progress,
        'total_symbols': batch.total_symbols,
        'completed': status_counts.get('completed', 0),
        'running': status_counts.get('running', 0),
        'pending': status_counts.get('pending', 0),
        'errors': status_counts.get('error', 0),
        'status_counts': status_counts,
        'start_time': batch.start_time.isoformat(),
        'end_time': batch.end_time.isoformat() if batch.end_time else None,
        'is_completed': batch.end_time is not None,
        'summary_stats': batch.summary_stats,
        'best_overall': batch.best_overall
    }

if __name__ == "__main__":
    # Test the multi-symbol processor
    print("\n=== Multi-Symbol Processor Test ===")
    
    processor = get_multi_symbol_processor()
    
    # Test configuration
    test_symbols = ["BTCUSDT", "ETHUSDT"]  # Adjust based on available data
    test_timeframes = ["60", "240"]
    
    print(f"🧪 Testing with symbols: {test_symbols}")
    print(f"🧪 Testing with timeframes: {test_timeframes}")
    
    # Start test batch
    batch_id = start_batch_optimization(
        symbols=test_symbols,
        timeframes=test_timeframes,
        n_trials=10,  # Small test
        parallel_symbols=1  # Sequential for testing
    )
    
    print(f"📝 Started test batch: {batch_id}")
    
    # Monitor progress
    for i in range(30):  # Check for 5 minutes max
        progress = get_batch_progress(batch_id)
        if progress:
            print(f"Progress: {progress['overall_progress']:.1f}% - {progress['completed']}/{progress['total_symbols']} completed")
            if progress['is_completed']:
                print(f"✅ Test batch completed!")
                if progress['best_overall']:
                    print(f"Best result: {progress['best_overall'].get('pnl', 0):.2f} PnL")
                break
        time.sleep(10)
    
    # Print performance stats
    stats = processor.get_performance_stats()
    print(f"📊 Performance stats: {stats}")
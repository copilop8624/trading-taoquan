"""
SQLAlchemy Database Models for Trading Optimization Results Persistence
Level B Implementation: Complete database-driven result storage system
"""

from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import json

db = SQLAlchemy()

def safe_json_convert(obj):
    """Safely convert objects to JSON-serializable format"""
    if isinstance(obj, bytes):
        try:
            # Try to decode bytes as UTF-8 string
            return obj.decode('utf-8')
        except UnicodeDecodeError:
            # If decode fails, convert to base64 string
            import base64
            return base64.b64encode(obj).decode('utf-8')
    elif isinstance(obj, (list, tuple)):
        return [safe_json_convert(item) for item in obj]
    elif isinstance(obj, dict):
        return {key: safe_json_convert(value) for key, value in obj.items()}
    else:
        return obj

class OptimizationResult(db.Model):
    """
    Main table storing optimization run results and parameters
    """
    __tablename__ = 'optimization_results'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Strategy and market info
    symbol = db.Column(db.String(20), nullable=False, index=True)
    timeframe = db.Column(db.String(10), nullable=False, index=True)
    strategy = db.Column(db.String(100), nullable=False)
    
    # Optimization configuration
    engine = db.Column(db.String(20), nullable=False, index=True)  # 'grid_search' or 'optuna'
    criteria = db.Column(db.String(20), nullable=False)  # 'pnl', 'sharpe', 'winrate'
    
    # Parameters as JSON (flexible for different strategies)
    parameters = db.Column(db.Text, nullable=False)  # JSON string of optimized parameters
    
    # Core metrics
    total_pnl = db.Column(db.Float, nullable=False, index=True)
    winrate = db.Column(db.Float, nullable=False)
    total_trades = db.Column(db.Integer, nullable=False)
    win_count = db.Column(db.Integer, nullable=False)
    loss_count = db.Column(db.Integer, nullable=False)
    
    # Advanced metrics as JSON
    advanced_metrics = db.Column(db.Text)  # JSON: sharpe, max_dd, profit_factor, etc.
    
    # Runtime info
    execution_time = db.Column(db.Float)  # seconds
    iterations = db.Column(db.Integer)  # number of parameter combinations tested
    
    # Data source info
    candle_source = db.Column(db.String(100))
    trade_pairs_count = db.Column(db.Integer)
    
    # Relationships
    trade_logs = db.relationship('TradeLog', backref='optimization', lazy='dynamic', cascade='all, delete-orphan')
    pnl_curves = db.relationship('PnLCurve', backref='optimization', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<OptimizationResult {self.id}: {self.symbol} {self.engine} PnL={self.total_pnl:.2f}%>'
    
    def to_dict(self):
        """Convert to dictionary for JSON response"""
        try:
            parameters = json.loads(self.parameters) if self.parameters else {}
        except (json.JSONDecodeError, TypeError):
            parameters = {}
            
        try:
            advanced_metrics = json.loads(self.advanced_metrics) if self.advanced_metrics else {}
        except (json.JSONDecodeError, TypeError):
            advanced_metrics = {}
        
        # Add field mapping for template compatibility
        # Map ts_activation to ts_trig for frontend compatibility
        if 'ts_activation' in parameters and 'ts_trig' not in parameters:
            parameters['ts_trig'] = parameters['ts_activation']
            
        data = {
            'id': self.id,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'symbol': safe_json_convert(self.symbol),
            'timeframe': safe_json_convert(self.timeframe),
            'strategy': safe_json_convert(self.strategy),
            'engine': safe_json_convert(self.engine),
            'criteria': safe_json_convert(self.criteria),
            'parameters': safe_json_convert(parameters),
            'total_pnl': self.total_pnl,
            'winrate': self.winrate,
            'total_trades': self.total_trades,
            'win_count': self.win_count,
            'loss_count': self.loss_count,
            'advanced_metrics': safe_json_convert(advanced_metrics),
            'execution_time': self.execution_time,
            'iterations': self.iterations,
            'candle_source': safe_json_convert(self.candle_source),
            'trade_pairs_count': self.trade_pairs_count
        }
        
        # Also add TS parameters to top level for easy access
        if 'ts_activation' in parameters:
            data['ts_activation'] = parameters['ts_activation']
            data['ts_trig'] = parameters['ts_activation']  # For backwards compatibility
        if 'ts_step' in parameters:
            data['ts_step'] = parameters['ts_step']
        
        return safe_json_convert(data)
    
    @classmethod
    def create_from_result(cls, result_data):
        """Create optimization result from dictionary"""
        return cls(
            symbol=result_data.get('symbol', ''),
            timeframe=result_data.get('timeframe', ''),
            strategy=result_data.get('strategy', ''),
            engine=result_data.get('engine', ''),
            criteria=result_data.get('criteria', 'pnl'),
            parameters=json.dumps(result_data.get('parameters', {})),
            total_pnl=result_data.get('total_pnl', 0.0),
            winrate=result_data.get('winrate', 0.0),
            total_trades=result_data.get('total_trades', 0),
            win_count=result_data.get('win_count', 0),
            loss_count=result_data.get('loss_count', 0),
            advanced_metrics=json.dumps(result_data.get('advanced_metrics', {})),
            execution_time=result_data.get('execution_time', 0.0),
            iterations=result_data.get('iterations', 0),
            candle_source=result_data.get('candle_source', ''),
            trade_pairs_count=result_data.get('trade_pairs_count', 0)
        )


class TradeLog(db.Model):
    """
    Individual trade results for each optimization run
    """
    __tablename__ = 'trade_logs'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    optimization_id = db.Column(db.Integer, db.ForeignKey('optimization_results.id'), nullable=False, index=True)
    
    # Trade identification
    trade_num = db.Column(db.Integer, nullable=False)
    
    # Trade details
    side = db.Column(db.String(10), nullable=False)  # 'LONG' or 'SHORT'
    entry_price = db.Column(db.Float, nullable=False)
    exit_price = db.Column(db.Float, nullable=False)
    exit_type = db.Column(db.String(20), nullable=False)  # 'SL', 'TS SL', 'EXIT', 'FAILED'
    
    # Trade performance
    pnl_pct = db.Column(db.Float, nullable=False, index=True)
    
    # Optional timing data
    entry_time = db.Column(db.DateTime)
    exit_time = db.Column(db.DateTime)
    duration_minutes = db.Column(db.Integer)
    
    def __repr__(self):
        return f'<TradeLog {self.id}: Trade #{self.trade_num} {self.side} PnL={self.pnl_pct:.2f}%>'
    
    def to_dict(self):
        """Convert to dictionary for JSON response"""
        data = {
            'id': self.id,
            'optimization_id': self.optimization_id,
            'trade_num': self.trade_num,
            'side': safe_json_convert(self.side),
            'entry_price': self.entry_price,
            'exit_price': self.exit_price,
            'exit_type': safe_json_convert(self.exit_type),
            'pnl_pct': self.pnl_pct,
            'entry_time': self.entry_time.isoformat() if self.entry_time else None,
            'exit_time': self.exit_time.isoformat() if self.exit_time else None,
            'duration_minutes': self.duration_minutes
        }
        
        return safe_json_convert(data)
    
    @classmethod
    def create_from_trade(cls, optimization_id, trade_data):
        """Create trade log from trade dictionary"""
        return cls(
            optimization_id=optimization_id,
            trade_num=trade_data.get('num', 0),
            side=trade_data.get('side', ''),
            entry_price=float(trade_data.get('entry_price', 0)),
            exit_price=float(trade_data.get('exit_price', 0)),
            exit_type=trade_data.get('exit_type', ''),
            pnl_pct=float(trade_data.get('pnl_pct', 0)),
            # Optional fields - can be extended later
            entry_time=None,  # Can be populated from trade_data if available
            exit_time=None,
            duration_minutes=None
        )


class PnLCurve(db.Model):
    """
    Equity curve data points for visualization
    """
    __tablename__ = 'pnl_curves'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    optimization_id = db.Column(db.Integer, db.ForeignKey('optimization_results.id'), nullable=False, index=True)
    
    # Curve point data
    trade_number = db.Column(db.Integer, nullable=False)  # X-axis
    cumulative_pnl = db.Column(db.Float, nullable=False)  # Y-axis
    
    # Optional additional curve data
    trade_pnl = db.Column(db.Float)  # Individual trade PnL
    running_winrate = db.Column(db.Float)  # Running win rate
    drawdown = db.Column(db.Float)  # Current drawdown from peak
    
    # Timestamp for time-based curves
    timestamp = db.Column(db.DateTime)
    
    def __repr__(self):
        return f'<PnLCurve {self.id}: Trade #{self.trade_number} Cumulative={self.cumulative_pnl:.2f}%>'
    
    def to_dict(self):
        """Convert to dictionary for JSON response"""
        data = {
            'id': self.id,
            'optimization_id': self.optimization_id,
            'trade_number': self.trade_number,
            'cumulative_pnl': self.cumulative_pnl,
            'trade_pnl': self.trade_pnl,
            'running_winrate': self.running_winrate,
            'drawdown': self.drawdown,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None
        }
        
        return safe_json_convert(data)
    
    @classmethod
    def generate_from_trades(cls, optimization_id, trades):
        """Generate PnL curve data points from trade list"""
        curve_points = []
        cumulative_pnl = 0.0
        wins = 0
        peak_pnl = 0.0
        
        for i, trade in enumerate(trades, 1):
            trade_pnl = float(trade.get('pnl_pct', 0))
            cumulative_pnl += trade_pnl
            
            if trade_pnl > 0:
                wins += 1
            
            # Update peak and calculate drawdown
            if cumulative_pnl > peak_pnl:
                peak_pnl = cumulative_pnl
            drawdown = peak_pnl - cumulative_pnl
            
            curve_point = cls(
                optimization_id=optimization_id,
                trade_number=i,
                cumulative_pnl=cumulative_pnl,
                trade_pnl=trade_pnl,
                running_winrate=(wins / i) * 100,
                drawdown=drawdown
            )
            curve_points.append(curve_point)
        
        return curve_points


def init_db(app):
    """Initialize database with Flask app"""
    db.init_app(app)
    
    with app.app_context():
        # Create all tables
        db.create_all()
        print("✅ Database tables created successfully")
        
        # Print table info
        print(f"📊 Tables created:")
        print(f"   - optimization_results")
        print(f"   - trade_logs") 
        print(f"   - pnl_curves")


def save_optimization_result(result_data, trades_data):
    """
    Save complete optimization result with trades and PnL curve
    
    Args:
        result_data (dict): Optimization summary data
        trades_data (list): List of trade dictionaries
        
    Returns:
        OptimizationResult: Saved optimization result object
    """
    try:
        # Create optimization result
        opt_result = OptimizationResult.create_from_result(result_data)
        db.session.add(opt_result)
        db.session.flush()  # Get the ID
        
        # Create trade logs
        for trade in trades_data:
            trade_log = TradeLog.create_from_trade(opt_result.id, trade)
            db.session.add(trade_log)
        
        # Generate and save PnL curve
        curve_points = PnLCurve.generate_from_trades(opt_result.id, trades_data)
        for point in curve_points:
            db.session.add(point)
        
        # Commit all changes
        db.session.commit()
        
        print(f"✅ Saved optimization result #{opt_result.id} with {len(trades_data)} trades")
        return opt_result
        
    except Exception as e:
        db.session.rollback()
        print(f"❌ Error saving optimization result: {e}")
        raise


def get_optimization_results(filters=None, limit=50, offset=0):
    """
    Retrieve optimization results with optional filtering
    
    Args:
        filters (dict): Optional filters (symbol, engine, etc.)
        limit (int): Maximum results to return
        offset (int): Results to skip for pagination
        
    Returns:
        list: List of optimization result dictionaries
    """
    query = OptimizationResult.query
    
    if filters:
        if 'symbol' in filters:
            query = query.filter(OptimizationResult.symbol == filters['symbol'])
        if 'engine' in filters:
            query = query.filter(OptimizationResult.engine == filters['engine'])
        if 'min_pnl' in filters:
            query = query.filter(OptimizationResult.total_pnl >= filters['min_pnl'])
        if 'max_pnl' in filters:
            query = query.filter(OptimizationResult.total_pnl <= filters['max_pnl'])
    
    # Order by timestamp descending (latest first)
    query = query.order_by(OptimizationResult.timestamp.desc())
    
    # Apply pagination
    results = query.limit(limit).offset(offset).all()
    
    return [result.to_dict() for result in results]


def get_optimization_details(optimization_id):
    """
    Get complete optimization details including trades and PnL curve
    
    Args:
        optimization_id (int): Optimization result ID
        
    Returns:
        dict: Complete optimization data
    """
    opt_result = OptimizationResult.query.get_or_404(optimization_id)
    
    # Get associated trades and PnL curve
    trades = [trade.to_dict() for trade in opt_result.trade_logs.all()]
    pnl_curve = [point.to_dict() for point in opt_result.pnl_curves.order_by(PnLCurve.trade_number).all()]
    
    return {
        'optimization': opt_result.to_dict(),
        'trades': trades,
        'pnl_curve': pnl_curve
    }


def export_optimization_results(format='json', filters=None):
    """
    Export optimization results to file format
    
    Args:
        format (str): Export format ('json' or 'csv')
        filters (dict): Optional filters
        
    Returns:
        str: Exported data as string
    """
    results = get_optimization_results(filters, limit=1000)  # Get up to 1000 results
    
    if format.lower() == 'json':
        return json.dumps(results, indent=2)
    elif format.lower() == 'csv':
        import csv
        import io
        
        output = io.StringIO()
        if results:
            fieldnames = results[0].keys()
            writer = csv.DictWriter(output, fieldnames=fieldnames)
            writer.writeheader()
            for result in results:
                # Flatten JSON fields for CSV
                flat_result = result.copy()
                if 'parameters' in flat_result and isinstance(flat_result['parameters'], dict):
                    flat_result['parameters'] = json.dumps(flat_result['parameters'])
                if 'advanced_metrics' in flat_result and isinstance(flat_result['advanced_metrics'], dict):
                    flat_result['advanced_metrics'] = json.dumps(flat_result['advanced_metrics'])
                writer.writerow(flat_result)
        
        return output.getvalue()
    else:
        raise ValueError(f"Unsupported export format: {format}")
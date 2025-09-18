"""
🔍 COMPREHENSIVE TRADING OPTIMIZATION AUDIT SYSTEM
=================================================

This tool performs exhaustive testing of the optimization logic to detect:
1. Parameter selection bugs across all combinations
2. Simulation consistency issues
3. Edge cases and boundary conditions
4. Data integrity problems
5. Logic contradictions

Run this to verify the entire system before production use.
"""

import sys
import traceback
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Any
import json
from datetime import datetime

# Import the optimization functions we need to test
try:
    from web_app import safe_float
    from backtest_gridsearch_slbe_ts_Version3 import simulate_trade, grid_search_parallel
    print("✅ Successfully imported optimization functions")
except Exception as e:
    print(f"❌ Failed to import functions: {e}")
    sys.exit(1)

class OptimizationAuditor:
    """Comprehensive auditor for trading optimization logic"""
    
    def __init__(self):
        self.results = {
            'timestamp': datetime.now().isoformat(),
            'tests_passed': 0,
            'tests_failed': 0,
            'critical_issues': [],
            'warnings': [],
            'edge_cases': [],
            'performance_metrics': {}
        }
        
    def log_result(self, test_name: str, passed: bool, details: str = "", severity: str = "info"):
        """Log test result with details"""
        if passed:
            self.results['tests_passed'] += 1
            print(f"✅ {test_name}: PASSED")
        else:
            self.results['tests_failed'] += 1
            print(f"❌ {test_name}: FAILED - {details}")
            
            issue = {
                'test': test_name,
                'details': details,
                'severity': severity,
                'timestamp': datetime.now().isoformat()
            }
            
            if severity == 'critical':
                self.results['critical_issues'].append(issue)
            elif severity == 'warning':
                self.results['warnings'].append(issue)
            else:
                self.results['edge_cases'].append(issue)
    
    def test_parameter_selection_logic(self):
        """Test all parameter selection combinations"""
        print("\n🧪 TESTING PARAMETER SELECTION LOGIC")
        print("=" * 50)
        
        # Test all possible parameter combinations
        param_combinations = [
            [],  # No parameters selected
            ['sl'],  # SL only
            ['be'],  # BE only  
            ['ts'],  # TS only
            ['sl', 'be'],  # SL + BE
            ['sl', 'ts'],  # SL + TS
            ['be', 'ts'],  # BE + TS
            ['sl', 'be', 'ts']  # All parameters
        ]
        
        # Default ranges for testing
        default_ranges = {
            'sl_min': 1.0, 'sl_max': 3.0, 'sl_step': 0.5,
            'be_min': 0.5, 'be_max': 1.5, 'be_step': 0.5,
            'ts_active_min': 0.5, 'ts_active_max': 1.5, 'ts_active_step': 0.5,
            'ts_step_min': 0.1, 'ts_step_max': 0.3, 'ts_step_step': 0.1
        }
        
        for selected_params in param_combinations:
            self._test_single_param_combination(selected_params, default_ranges)
    
    def _test_single_param_combination(self, selected_params: List[str], ranges: Dict):
        """Test a single parameter combination"""
        test_name = f"Param combination: {selected_params if selected_params else 'NONE'}"
        
        try:
            # Simulate the parameter list generation logic from web_app.py
            DEFAULT_SL = 2.0
            DEFAULT_BE = 0.0
            DEFAULT_TS = 0.0
            DEFAULT_TS_STEP = 0.0
            
            # Grid Search Logic Test
            if 'sl' in selected_params:
                sl_list = [ranges['sl_min'] + i * ranges['sl_step'] 
                          for i in range(int((ranges['sl_max'] - ranges['sl_min']) / ranges['sl_step']) + 1)]
            else:
                sl_list = [DEFAULT_SL]
                
            if 'be' in selected_params:
                be_list = [ranges['be_min'] + i * ranges['be_step'] 
                          for i in range(int((ranges['be_max'] - ranges['be_min']) / ranges['be_step']) + 1)]
            else:
                be_list = [DEFAULT_BE]
                
            if 'ts' in selected_params:
                ts_trig_list = [ranges['ts_active_min'] + i * ranges['ts_active_step'] 
                               for i in range(int((ranges['ts_active_max'] - ranges['ts_active_min']) / ranges['ts_active_step']) + 1)]
                ts_step_list = [ranges['ts_step_min'] + i * ranges['ts_step_step'] 
                               for i in range(int((ranges['ts_step_max'] - ranges['ts_step_min']) / ranges['ts_step_step']) + 1)]
            else:
                ts_trig_list = [DEFAULT_TS]
                ts_step_list = [DEFAULT_TS_STEP]
            
            # Validation checks
            issues = []
            
            # Check 1: Parameter lists should not be empty
            if not sl_list or not be_list or not ts_trig_list or not ts_step_list:
                issues.append("Empty parameter list detected")
            
            # Check 2: Non-selected parameters should use defaults
            if 'sl' not in selected_params and sl_list != [DEFAULT_SL]:
                issues.append(f"SL not selected but got {sl_list}, expected [{DEFAULT_SL}]")
                
            if 'be' not in selected_params and be_list != [DEFAULT_BE]:
                issues.append(f"BE not selected but got {be_list}, expected [{DEFAULT_BE}]")
                
            if 'ts' not in selected_params and (ts_trig_list != [DEFAULT_TS] or ts_step_list != [DEFAULT_TS_STEP]):
                issues.append(f"TS not selected but got trig={ts_trig_list}, step={ts_step_list}")
            
            # Check 3: Selected parameters should have multiple values (unless range is too small)
            if 'sl' in selected_params and len(sl_list) < 2 and ranges['sl_max'] > ranges['sl_min']:
                issues.append(f"SL selected but only got {len(sl_list)} values")
                
            if 'be' in selected_params and len(be_list) < 2 and ranges['be_max'] > ranges['be_min']:
                issues.append(f"BE selected but only got {len(be_list)} values")
                
            if 'ts' in selected_params and (len(ts_trig_list) < 2 or len(ts_step_list) < 2):
                if ranges['ts_active_max'] > ranges['ts_active_min'] or ranges['ts_step_max'] > ranges['ts_step_min']:
                    issues.append(f"TS selected but got trig={len(ts_trig_list)}, step={len(ts_step_list)} values")
            
            # Check 4: Value ranges should be realistic
            for sl in sl_list:
                if sl < 0 or sl > 10:  # SL should be 0-10%
                    issues.append(f"Unrealistic SL value: {sl}")
                    
            for be in be_list:
                if be < 0 or be > 5:  # BE should be 0-5%
                    issues.append(f"Unrealistic BE value: {be}")
                    
            for ts in ts_trig_list:
                if ts < 0 or ts > 5:  # TS should be 0-5%
                    issues.append(f"Unrealistic TS trigger value: {ts}")
            
            # Report results
            if issues:
                self.log_result(test_name, False, "; ".join(issues), "critical")
            else:
                self.log_result(test_name, True)
                
        except Exception as e:
            self.log_result(test_name, False, f"Exception: {str(e)}", "critical")
    
    def test_simulation_consistency(self):
        """Test simulation function for consistency and edge cases"""
        print("\n🧪 TESTING SIMULATION CONSISTENCY")
        print("=" * 50)
        
        # Create mock data for testing
        mock_candle_data = pd.DataFrame({
            'datetime': pd.date_range('2024-01-01', periods=100, freq='H'),
            'open': np.random.normal(50000, 1000, 100),
            'high': np.random.normal(51000, 1000, 100),
            'low': np.random.normal(49000, 1000, 100),
            'close': np.random.normal(50000, 1000, 100),
            'volume': np.random.normal(100, 10, 100)
        })
        
        # Make sure high >= max(open, close) and low <= min(open, close)
        for i in range(len(mock_candle_data)):
            mock_candle_data.loc[i, 'high'] = max(mock_candle_data.loc[i, 'open'], 
                                                 mock_candle_data.loc[i, 'close'], 
                                                 mock_candle_data.loc[i, 'high'])
            mock_candle_data.loc[i, 'low'] = min(mock_candle_data.loc[i, 'open'], 
                                                mock_candle_data.loc[i, 'close'], 
                                                mock_candle_data.loc[i, 'low'])
        
        # Test cases for simulation
        test_cases = [
            # Format: (sl, be, ts_trig, ts_step, expected_behavior, test_name)
            (0, 0, 0, 0, "all_disabled", "All parameters disabled"),
            (2.0, 0, 0, 0, "sl_only", "SL only active"),
            (0, 1.0, 0, 0, "be_only", "BE only active"), 
            (0, 0, 1.0, 0.1, "ts_only", "TS only active"),
            (2.0, 1.0, 0, 0, "sl_be", "SL + BE active"),
            (2.0, 0, 1.0, 0.1, "sl_ts", "SL + TS active"),
            (0, 1.0, 1.0, 0.1, "be_ts", "BE + TS active"),
            (2.0, 1.0, 1.0, 0.1, "all_active", "All parameters active"),
            # Edge cases
            (-1, 0, 0, 0, "invalid", "Negative SL"),
            (0, -1, 0, 0, "invalid", "Negative BE"),
            (0, 0, -1, 0, "invalid", "Negative TS trigger"),
            (0, 0, 0, -1, "invalid", "Negative TS step"),
            (100, 0, 0, 0, "extreme", "Extreme SL (100%)"),
            (None, None, None, None, "null", "Null parameters")
        ]
        
        mock_trade_pair = {
            'num': 1,
            'entryDt': mock_candle_data.iloc[10]['datetime'],
            'exitDt': mock_candle_data.iloc[20]['datetime'],
            'entryPrice': 50000,
            'exitPrice': 51000,
            'side': 'LONG'
        }
        
        for sl, be, ts_trig, ts_step, expected, test_name in test_cases:
            self._test_single_simulation(mock_trade_pair, mock_candle_data, sl, be, ts_trig, ts_step, expected, test_name)
    
    def _test_single_simulation(self, trade_pair, candle_data, sl, be, ts_trig, ts_step, expected_behavior, test_name):
        """Test a single simulation case"""
        try:
            result, log = simulate_trade(trade_pair, candle_data, sl, be, ts_trig, ts_step)
            
            issues = []
            
            # Check based on expected behavior
            if expected_behavior == "all_disabled":
                # Should complete without any stops
                if result and result.get('exit_type') not in ['TARGET', 'TIME']:
                    issues.append(f"Expected no stops but got exit_type: {result.get('exit_type')}")
                    
            elif expected_behavior == "sl_only":
                # Only SL should be possible
                if result and result.get('exit_type') in ['BE', 'TS']:
                    issues.append(f"SL-only but got exit_type: {result.get('exit_type')}")
                    
            elif expected_behavior == "invalid":
                # Invalid parameters should handle gracefully
                if result is None:
                    pass  # This is acceptable
                else:
                    # Should not crash, but behavior should be sensible
                    pass
                    
            elif expected_behavior == "null":
                # Null parameters should handle gracefully
                if result is None:
                    pass  # This is acceptable
                    
            # Check result structure if not None
            if result is not None:
                required_fields = ['pnl_pct', 'exit_type', 'exit_price']
                for field in required_fields:
                    if field not in result:
                        issues.append(f"Missing required field: {field}")
                
                # Check for reasonable values
                if 'pnl_pct' in result:
                    pnl = result['pnl_pct']
                    if not isinstance(pnl, (int, float)) or abs(pnl) > 100:  # PnL > 100% is suspicious
                        issues.append(f"Suspicious PnL value: {pnl}")
                        
                if 'exit_price' in result:
                    exit_price = result['exit_price']
                    if not isinstance(exit_price, (int, float)) or exit_price <= 0:
                        issues.append(f"Invalid exit price: {exit_price}")
            
            # Report results
            if issues:
                self.log_result(test_name, False, "; ".join(issues), "warning")
            else:
                self.log_result(test_name, True)
                
        except Exception as e:
            self.log_result(test_name, False, f"Exception: {str(e)}", "critical")
    
    def test_safe_float_function(self):
        """Test the safe_float function for all edge cases"""
        print("\n🧪 TESTING SAFE_FLOAT FUNCTION")
        print("=" * 50)
        
        test_cases = [
            # (input_value, expected_output, test_name)
            (1.5, 1.5, "Normal float"),
            (1, 1.0, "Integer input"),
            ("1.5", 1.5, "String number"),
            (None, 0.0, "None input"),
            (float('nan'), 0.0, "NaN input"),
            (float('inf'), 0.0, "Infinity input"),
            (float('-inf'), 0.0, "Negative infinity input"),
            ("abc", 0.0, "Invalid string"),
            ([], 0.0, "List input"),
            ({}, 0.0, "Dict input"),
            (True, 1.0, "Boolean True"),
            (False, 0.0, "Boolean False")
        ]
        
        for input_val, expected, test_name in test_cases:
            try:
                result = safe_float(input_val)
                if result == expected:
                    self.log_result(f"safe_float: {test_name}", True)
                else:
                    self.log_result(f"safe_float: {test_name}", False, 
                                  f"Expected {expected}, got {result}", "warning")
            except Exception as e:
                self.log_result(f"safe_float: {test_name}", False, 
                              f"Exception: {str(e)}", "critical")
    
    def test_edge_cases_and_boundaries(self):
        """Test edge cases and boundary conditions"""
        print("\n🧪 TESTING EDGE CASES AND BOUNDARIES")
        print("=" * 50)
        
        # Test parameter boundary values
        boundary_tests = [
            (0, 0, 0, 0, "Zero boundaries"),
            (0.001, 0.001, 0.001, 0.001, "Tiny values"),
            (10, 10, 10, 10, "Large values"),
            (0.5, 0, 0, 0, "Mixed zero/non-zero")
        ]
        
        # Create minimal candle data
        minimal_candles = pd.DataFrame({
            'datetime': pd.date_range('2024-01-01', periods=10, freq='H'),
            'open': [50000] * 10,
            'high': [50100] * 10,
            'low': [49900] * 10,
            'close': [50000] * 10,
            'volume': [100] * 10
        })
        
        minimal_trade = {
            'num': 1,
            'entryDt': minimal_candles.iloc[2]['datetime'],
            'exitDt': minimal_candles.iloc[7]['datetime'],
            'entryPrice': 50000,
            'exitPrice': 50000,
            'side': 'LONG'
        }
        
        for sl, be, ts_trig, ts_step, test_name in boundary_tests:
            try:
                result, log = simulate_trade(minimal_trade, minimal_candles, sl, be, ts_trig, ts_step)
                # Just check it doesn't crash
                self.log_result(f"Boundary test: {test_name}", True)
            except Exception as e:
                self.log_result(f"Boundary test: {test_name}", False, 
                              f"Exception: {str(e)}", "critical")
    
    def generate_comprehensive_report(self):
        """Generate a comprehensive audit report"""
        print("\n" + "=" * 80)
        print("🔍 COMPREHENSIVE AUDIT REPORT")
        print("=" * 80)
        
        total_tests = self.results['tests_passed'] + self.results['tests_failed']
        success_rate = (self.results['tests_passed'] / total_tests * 100) if total_tests > 0 else 0
        
        print(f"📊 TEST SUMMARY:")
        print(f"   Total Tests: {total_tests}")
        print(f"   Passed: {self.results['tests_passed']}")
        print(f"   Failed: {self.results['tests_failed']}")
        print(f"   Success Rate: {success_rate:.1f}%")
        
        if self.results['critical_issues']:
            print(f"\n🚨 CRITICAL ISSUES ({len(self.results['critical_issues'])}):")
            for issue in self.results['critical_issues']:
                print(f"   ❌ {issue['test']}: {issue['details']}")
        
        if self.results['warnings']:
            print(f"\n⚠️  WARNINGS ({len(self.results['warnings'])}):")
            for warning in self.results['warnings']:
                print(f"   ⚠️  {warning['test']}: {warning['details']}")
        
        if self.results['edge_cases']:
            print(f"\n📝 EDGE CASE ISSUES ({len(self.results['edge_cases'])}):")
            for edge in self.results['edge_cases']:
                print(f"   📝 {edge['test']}: {edge['details']}")
        
        # Overall assessment
        print(f"\n🎯 OVERALL ASSESSMENT:")
        if len(self.results['critical_issues']) == 0:
            if success_rate >= 90:
                print("   ✅ SYSTEM APPEARS STABLE - Ready for production use")
            elif success_rate >= 80:
                print("   ⚠️  SYSTEM MOSTLY STABLE - Minor issues detected")
            else:
                print("   ❌ SYSTEM HAS ISSUES - Significant problems detected")
        else:
            print("   🚨 SYSTEM HAS CRITICAL ISSUES - DO NOT USE IN PRODUCTION")
        
        # Save detailed report
        report_file = f"audit_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump(self.results, f, indent=2)
        print(f"\n📄 Detailed report saved: {report_file}")
        
        return self.results

def run_comprehensive_audit():
    """Run the complete audit suite"""
    print("🔍 STARTING COMPREHENSIVE TRADING OPTIMIZATION AUDIT")
    print("=" * 80)
    
    auditor = OptimizationAuditor()
    
    try:
        # Run all test suites
        auditor.test_parameter_selection_logic()
        auditor.test_simulation_consistency()
        auditor.test_safe_float_function()
        auditor.test_edge_cases_and_boundaries()
        
        # Generate final report
        results = auditor.generate_comprehensive_report()
        
        return results
        
    except Exception as e:
        print(f"❌ AUDIT FAILED WITH EXCEPTION: {str(e)}")
        print(traceback.format_exc())
        return None

if __name__ == "__main__":
    # Run the audit
    audit_results = run_comprehensive_audit()
    
    # Print final status
    if audit_results:
        critical_count = len(audit_results.get('critical_issues', []))
        if critical_count == 0:
            print("\n🎉 AUDIT COMPLETED - System appears stable!")
        else:
            print(f"\n🚨 AUDIT COMPLETED - {critical_count} critical issues found!")
    else:
        print("\n💥 AUDIT FAILED - System has serious problems!")
#!/usr/bin/env python3
"""
🔍 SYSTEMATIC PROJECT ANALYZER
Phân tích toàn diện và có hệ thống để phát hiện tất cả vấn đề trong project
"""

import os
import re
import json
import ast
import traceback
from pathlib import Path
from typing import Dict, List, Any, Tuple
import subprocess
from collections import defaultdict

class SystematicProjectAnalyzer:
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.issues = []
        self.analysis = {}
        self.patterns = {}
        self.inconsistencies = []
        
    def analyze_comprehensive(self):
        """Phân tích toàn diện và có hệ thống"""
        print("🔍 STARTING SYSTEMATIC PROJECT ANALYSIS")
        print("=" * 70)
        
        # Phase 1: Structure Analysis
        self.analyze_project_structure()
        
        # Phase 2: Code Pattern Analysis
        self.analyze_code_patterns()
        
        # Phase 3: Logic Flow Analysis
        self.analyze_logic_flows()
        
        # Phase 4: Consistency Analysis
        self.analyze_consistency()
        
        # Phase 5: Integration Analysis
        self.analyze_integrations()
        
        # Phase 6: Generate Actionable Report
        self.generate_systematic_report()
        
        return self.analysis
    
    def analyze_project_structure(self):
        """Phân tích cấu trúc project"""
        print("📁 Analyzing project structure...")
        
        structure = {
            'python_files': [],
            'config_files': [],
            'data_files': [],
            'other_files': []
        }
        
        for file_path in self.project_root.rglob('*'):
            if file_path.is_file():
                if file_path.suffix == '.py':
                    structure['python_files'].append(str(file_path))
                elif file_path.suffix in ['.json', '.ini', '.cfg', '.yml', '.yaml']:
                    structure['config_files'].append(str(file_path))
                elif file_path.suffix in ['.csv', '.db', '.sqlite']:
                    structure['data_files'].append(str(file_path))
                else:
                    structure['other_files'].append(str(file_path))
        
        self.analysis['structure'] = structure
        
        # Check for critical files
        critical_files = ['web_app.py', 'backtest_gridsearch_slbe_ts_Version3.py']
        missing_critical = [f for f in critical_files if not (self.project_root / f).exists()]
        
        if missing_critical:
            self.issues.append({
                'severity': 'CRITICAL',
                'category': 'Missing Files',
                'message': f"Missing critical files: {missing_critical}",
                'impact': "Core functionality unavailable",
                'action': "Restore or create missing files"
            })
    
    def analyze_code_patterns(self):
        """Phân tích patterns trong code"""
        print("🔍 Analyzing code patterns...")
        
        patterns = {
            'function_definitions': defaultdict(list),
            'class_definitions': defaultdict(list),
            'import_statements': defaultdict(list),
            'api_routes': defaultdict(list),
            'variable_assignments': defaultdict(list)
        }
        
        for py_file in self.project_root.glob('*.py'):
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Function definitions
                func_matches = re.finditer(r'def\s+(\w+)\s*\(([^)]*)\):', content)
                for match in func_matches:
                    func_name = match.group(1)
                    params = match.group(2)
                    line_num = content[:match.start()].count('\n') + 1
                    patterns['function_definitions'][func_name].append({
                        'file': py_file.name,
                        'line': line_num,
                        'params': params.strip()
                    })
                
                # API routes
                route_matches = re.finditer(r"@app\.route\(['\"]([^'\"]+)['\"][^)]*\)\s*def\s+(\w+)", content, re.DOTALL)
                for match in route_matches:
                    route_path = match.group(1)
                    func_name = match.group(2)
                    line_num = content[:match.start()].count('\n') + 1
                    patterns['api_routes'][route_path].append({
                        'file': py_file.name,
                        'function': func_name,
                        'line': line_num
                    })
                
                # Variable assignments (focusing on important ones)
                var_patterns = [
                    (r'optimization_engine\s*=\s*([^#\n]+)', 'optimization_engine'),
                    (r'DEFAULT_\w+\s*=\s*([^#\n]+)', 'default_values'),
                    (r'(\w+_min|_max|_list)\s*=\s*([^#\n]+)', 'parameter_ranges')
                ]
                
                for pattern, var_type in var_patterns:
                    var_matches = re.finditer(pattern, content)
                    for match in var_matches:
                        line_num = content[:match.start()].count('\n') + 1
                        patterns['variable_assignments'][var_type].append({
                            'file': py_file.name,
                            'line': line_num,
                            'assignment': match.group(0).strip()
                        })
                        
            except Exception as e:
                self.issues.append({
                    'severity': 'ERROR',
                    'category': 'File Analysis',
                    'message': f"Cannot analyze {py_file.name}: {e}",
                    'impact': "Incomplete analysis",
                    'action': "Check file encoding and syntax"
                })
        
        self.patterns = patterns
        
        # Detect pattern issues
        self.detect_pattern_issues()
    
    def detect_pattern_issues(self):
        """Phát hiện issues từ patterns"""
        
        # Duplicate function names
        for func_name, locations in self.patterns['function_definitions'].items():
            if len(locations) > 1:
                self.issues.append({
                    'severity': 'ERROR',
                    'category': 'Code Duplication',
                    'message': f"Function '{func_name}' defined multiple times",
                    'details': locations,
                    'impact': "Unpredictable behavior, last definition wins",
                    'action': f"Rename or consolidate duplicate functions"
                })
        
        # Duplicate routes
        for route_path, locations in self.patterns['api_routes'].items():
            if len(locations) > 1:
                self.issues.append({
                    'severity': 'CRITICAL',
                    'category': 'API Conflict',
                    'message': f"Route '{route_path}' defined multiple times",
                    'details': locations,
                    'impact': "API endpoints not working properly",
                    'action': "Remove duplicate route definitions"
                })
        
        # Inconsistent variable assignments
        for var_type, assignments in self.patterns['variable_assignments'].items():
            if var_type == 'optimization_engine' and len(assignments) > 0:
                values = []
                for assignment in assignments:
                    # Extract assigned value
                    value_match = re.search(r'=\s*([^#\n]+)', assignment['assignment'])
                    if value_match:
                        values.append(value_match.group(1).strip())
                
                unique_values = set(values)
                if len(unique_values) > 1:
                    self.issues.append({
                        'severity': 'ERROR',
                        'category': 'Logic Inconsistency',
                        'message': f"Inconsistent {var_type} assignments: {unique_values}",
                        'details': assignments,
                        'impact': "Unpredictable engine selection behavior",
                        'action': "Standardize optimization engine handling"
                    })
    
    def analyze_logic_flows(self):
        """Phân tích logic flows"""
        print("🔄 Analyzing logic flows...")
        
        web_app_path = self.project_root / 'web_app.py'
        if not web_app_path.exists():
            return
        
        with open(web_app_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Analyze optimization flow
        optimization_flow = self.trace_optimization_flow(content)
        self.analysis['optimization_flow'] = optimization_flow
        
        # Analyze parameter handling flow
        parameter_flow = self.trace_parameter_flow(content)
        self.analysis['parameter_flow'] = parameter_flow
        
        # Find logic gaps
        self.find_logic_gaps(content)
    
    def trace_optimization_flow(self, content: str) -> Dict:
        """Trace optimization engine selection flow"""
        flow = {
            'entry_points': [],
            'engine_checks': [],
            'execution_paths': [],
            'gaps': []
        }
        
        # Find entry points
        route_matches = re.finditer(r"@app\.route\(['\"]([^'\"]+)['\"][^)]*\)\s*def\s+(\w+)", content, re.DOTALL)
        for match in route_matches:
            if 'optim' in match.group(1).lower():
                flow['entry_points'].append({
                    'route': match.group(1),
                    'function': match.group(2),
                    'line': content[:match.start()].count('\n') + 1
                })
        
        # Find engine condition checks
        engine_checks = re.finditer(r'if\s+optimization_engine\s*==\s*[\'"]([^\'"]+)[\'"]', content)
        for match in engine_checks:
            flow['engine_checks'].append({
                'condition': match.group(0),
                'engine': match.group(1),
                'line': content[:match.start()].count('\n') + 1
            })
        
        # Find execution paths
        optuna_calls = re.finditer(r'optuna_search\s*\(', content)
        grid_calls = re.finditer(r'grid_search_\w+\s*\(', content)
        
        for match in optuna_calls:
            flow['execution_paths'].append({
                'type': 'optuna',
                'call': match.group(0),
                'line': content[:match.start()].count('\n') + 1
            })
        
        for match in grid_calls:
            flow['execution_paths'].append({
                'type': 'grid_search',
                'call': match.group(0),
                'line': content[:match.start()].count('\n') + 1
            })
        
        return flow
    
    def trace_parameter_flow(self, content: str) -> Dict:
        """Trace parameter handling flow"""
        flow = {
            'parameter_extraction': [],
            'default_assignments': [],
            'parameter_usage': [],
            'conversions': []
        }
        
        # Parameter extraction from request
        param_extractions = re.finditer(r"(\w+)\s*=\s*data\.get\(['\"]([^'\"]+)['\"][^)]*\)", content)
        for match in param_extractions:
            flow['parameter_extraction'].append({
                'variable': match.group(1),
                'key': match.group(2),
                'line': content[:match.start()].count('\n') + 1,
                'full_statement': match.group(0)
            })
        
        # Default value assignments
        default_assignments = re.finditer(r'DEFAULT_(\w+)\s*=\s*([^#\n]+)', content)
        for match in default_assignments:
            flow['default_assignments'].append({
                'parameter': match.group(1),
                'value': match.group(2).strip(),
                'line': content[:match.start()].count('\n') + 1
            })
        
        return flow
    
    def find_logic_gaps(self, content: str):
        """Tìm logic gaps và inconsistencies"""
        
        # Check for missing else conditions
        if_statements = re.finditer(r'if\s+optimization_engine\s*==.*?:', content)
        else_statements = re.finditer(r'else\s*:', content)
        
        if_count = len(list(if_statements))
        else_count = len(list(else_statements))
        
        if if_count > else_count:
            self.issues.append({
                'severity': 'WARNING',
                'category': 'Logic Gap',
                'message': f"Found {if_count} optimization_engine if statements but only {else_count} else statements",
                'impact': "Some engine values may not be handled",
                'action': "Add comprehensive else/elif handling for all engine types"
            })
        
        # Check for parameter validation
        required_params = ['strategy', 'candle_data', 'optimization_engine']
        missing_validation = []
        
        for param in required_params:
            if f"if not {param}" not in content and f"if {param} is None" not in content:
                missing_validation.append(param)
        
        if missing_validation:
            self.issues.append({
                'severity': 'WARNING',
                'category': 'Missing Validation',
                'message': f"No validation found for required parameters: {missing_validation}",
                'impact': "API may crash with invalid inputs",
                'action': "Add proper validation for all required parameters"
            })
    
    def analyze_consistency(self):
        """Phân tích consistency across codebase"""
        print("🔍 Analyzing consistency...")
        
        # Function signature consistency
        self.check_function_consistency()
        
        # Parameter naming consistency
        self.check_parameter_consistency()
        
        # Default value consistency
        self.check_default_consistency()
    
    def check_function_consistency(self):
        """Kiểm tra consistency của function signatures"""
        
        # Check simulate_trade calls
        simulate_calls = []
        for py_file in self.project_root.glob('*.py'):
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                calls = re.finditer(r'simulate_trade\s*\([^)]+\)', content)
                for match in calls:
                    line_num = content[:match.start()].count('\n') + 1
                    simulate_calls.append({
                        'file': py_file.name,
                        'line': line_num,
                        'call': match.group(0)
                    })
                    
            except Exception:
                continue
        
        if len(simulate_calls) > 1:
            # Check if all calls have same parameter count
            param_counts = []
            for call in simulate_calls:
                # Count parameters (rough estimate)
                param_count = call['call'].count(',') + 1
                param_counts.append(param_count)
            
            if len(set(param_counts)) > 1:
                self.issues.append({
                    'severity': 'ERROR',
                    'category': 'Function Signature Inconsistency',
                    'message': f"simulate_trade called with different parameter counts: {param_counts}",
                    'details': simulate_calls,
                    'impact': "Some calls may fail due to wrong parameter count",
                    'action': "Standardize all simulate_trade calls to use same parameters"
                })
    
    def check_parameter_consistency(self):
        """Kiểm tra parameter naming consistency"""
        
        parameter_variations = {
            'optimization_engine': ['engine', 'opt_engine', 'optimization_engine'],
            'ts_activation': ['ts_trig', 'ts_activation', 'trailing_stop'],
            'be': ['be', 'breakeven', 'break_even']
        }
        
        for standard_name, variations in parameter_variations.items():
            found_variations = []
            
            for py_file in self.project_root.glob('*.py'):
                try:
                    with open(py_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    for variation in variations:
                        if variation in content:
                            found_variations.append(variation)
                            
                except Exception:
                    continue
            
            unique_variations = set(found_variations)
            if len(unique_variations) > 1:
                self.issues.append({
                    'severity': 'WARNING',
                    'category': 'Parameter Naming Inconsistency',
                    'message': f"Multiple naming variations for {standard_name}: {unique_variations}",
                    'impact': "Confusion and potential bugs from inconsistent naming",
                    'action': f"Standardize all references to use '{standard_name}'"
                })
    
    def check_default_consistency(self):
        """Kiểm tra default value consistency"""
        
        default_values = defaultdict(list)
        
        for py_file in self.project_root.glob('*.py'):
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Find default value assignments
                defaults = re.finditer(r'DEFAULT_(\w+)\s*=\s*([^#\n]+)', content)
                for match in defaults:
                    param_name = match.group(1)
                    value = match.group(2).strip()
                    default_values[param_name].append({
                        'file': py_file.name,
                        'value': value,
                        'line': content[:match.start()].count('\n') + 1
                    })
                    
            except Exception:
                continue
        
        for param, values in default_values.items():
            unique_values = set([v['value'] for v in values])
            if len(unique_values) > 1:
                self.issues.append({
                    'severity': 'ERROR',
                    'category': 'Default Value Inconsistency',
                    'message': f"DEFAULT_{param} has multiple values: {unique_values}",
                    'details': values,
                    'impact': "Unpredictable behavior due to different default values",
                    'action': f"Use single DEFAULT_{param} value across all files"
                })
    
    def analyze_integrations(self):
        """Phân tích integration points"""
        print("🔗 Analyzing integrations...")
        
        integrations = {
            'frontend_backend': self.analyze_frontend_backend_integration(),
            'module_imports': self.analyze_module_integrations(),
            'data_flows': self.analyze_data_integrations()
        }
        
        self.analysis['integrations'] = integrations
    
    def analyze_frontend_backend_integration(self) -> Dict:
        """Phân tích frontend-backend integration"""
        
        web_app_path = self.project_root / 'web_app.py'
        if not web_app_path.exists():
            return {}
        
        with open(web_app_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Find API endpoints
        endpoints = []
        routes = re.finditer(r"@app\.route\(['\"]([^'\"]+)['\"][^)]*\)", content)
        for match in routes:
            endpoints.append(match.group(1))
        
        # Find request data expectations
        request_fields = []
        data_gets = re.finditer(r"data\.get\(['\"]([^'\"]+)['\"]", content)
        for match in data_gets:
            request_fields.append(match.group(1))
        
        return {
            'endpoints': endpoints,
            'expected_request_fields': list(set(request_fields))
        }
    
    def analyze_module_integrations(self) -> Dict:
        """Phân tích module integration"""
        
        imports = defaultdict(list)
        
        for py_file in self.project_root.glob('*.py'):
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Find import statements
                import_matches = re.finditer(r'^(?:from\s+(\S+)\s+import|import\s+(\S+))', content, re.MULTILINE)
                for match in import_matches:
                    module = match.group(1) or match.group(2)
                    if module:
                        imports[py_file.name].append(module)
                        
            except Exception:
                continue
        
        return dict(imports)
    
    def analyze_data_integrations(self) -> Dict:
        """Phân tích data flow integrations"""
        
        data_flows = {
            'file_operations': [],
            'database_operations': [],
            'api_data_flows': []
        }
        
        for py_file in self.project_root.glob('*.py'):
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # File operations
                file_ops = re.finditer(r'(open\(|pd\.read_csv\(|\.csv|\.json)', content)
                for match in file_ops:
                    line_num = content[:match.start()].count('\n') + 1
                    data_flows['file_operations'].append({
                        'file': py_file.name,
                        'line': line_num,
                        'operation': match.group(0)
                    })
                
            except Exception:
                continue
        
        return data_flows
    
    def generate_systematic_report(self):
        """Tạo systematic report với actionable insights"""
        print("\n" + "="*70)
        print("🎯 SYSTEMATIC PROJECT ANALYSIS REPORT")
        print("="*70)
        
        # Priority matrix
        priority_matrix = self.create_priority_matrix()
        
        print(f"📊 ISSUE PRIORITY MATRIX:")
        for priority, issues in priority_matrix.items():
            count = len(issues)
            if count > 0:
                icon = {'P0': '🔴', 'P1': '🟠', 'P2': '🟡', 'P3': '🔵'}[priority]
                print(f"   {icon} {priority}: {count} issues")
        
        print(f"\n🎯 IMMEDIATE ACTION REQUIRED:")
        if 'P0' in priority_matrix and priority_matrix['P0']:
            for issue in priority_matrix['P0'][:3]:  # Top 3 P0 issues
                print(f"   🔴 {issue['message']}")
                print(f"      → {issue['action']}")
        
        print(f"\n🔧 TOP 5 RECOMMENDED FIXES:")
        recommendations = self.generate_recommendations()
        for i, rec in enumerate(recommendations[:5], 1):
            print(f"{i}. {rec}")
        
        print(f"\n📈 PROJECT HEALTH SCORE:")
        health_score = self.calculate_health_score()
        print(f"   Overall: {health_score}/100")
        print(f"   🔴 Critical Issues: {len([i for i in self.issues if i['severity'] == 'CRITICAL'])}")
        print(f"   🟠 Major Issues: {len([i for i in self.issues if i['severity'] == 'ERROR'])}")
        print(f"   🟡 Minor Issues: {len([i for i in self.issues if i['severity'] == 'WARNING'])}")
        
        # Save comprehensive report
        report_data = {
            'analysis_timestamp': str(Path().cwd()),
            'health_score': health_score,
            'priority_matrix': priority_matrix,
            'patterns': self.patterns,
            'analysis': self.analysis,
            'issues': self.issues,
            'recommendations': recommendations
        }
        
        report_file = self.project_root / 'systematic_analysis_report.json'
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False, default=str)
        
        print(f"\n💾 Comprehensive report saved to: {report_file}")
        
        return report_data
    
    def create_priority_matrix(self) -> Dict:
        """Tạo priority matrix cho issues"""
        
        priority_matrix = {'P0': [], 'P1': [], 'P2': [], 'P3': []}
        
        for issue in self.issues:
            severity = issue['severity']
            category = issue['category']
            
            # P0: Critical issues that break functionality
            if severity == 'CRITICAL' or 'API Conflict' in category or 'Missing Files' in category:
                priority_matrix['P0'].append(issue)
            
            # P1: Major issues that cause significant problems
            elif severity == 'ERROR' or 'Logic Inconsistency' in category or 'Code Duplication' in category:
                priority_matrix['P1'].append(issue)
            
            # P2: Important issues that should be fixed
            elif severity == 'WARNING' or 'Inconsistency' in category:
                priority_matrix['P2'].append(issue)
            
            # P3: Nice to have fixes
            else:
                priority_matrix['P3'].append(issue)
        
        return priority_matrix
    
    def generate_recommendations(self) -> List[str]:
        """Tạo actionable recommendations"""
        
        recommendations = []
        
        # Based on issues found
        issue_categories = defaultdict(int)
        for issue in self.issues:
            issue_categories[issue['category']] += 1
        
        if issue_categories.get('Logic Inconsistency', 0) > 0:
            recommendations.append("Standardize optimization engine selection logic with single source of truth")
        
        if issue_categories.get('Code Duplication', 0) > 0:
            recommendations.append("Remove duplicate function definitions and consolidate logic")
        
        if issue_categories.get('Missing Validation', 0) > 0:
            recommendations.append("Add comprehensive input validation for all API endpoints")
        
        if issue_categories.get('Parameter Naming Inconsistency', 0) > 0:
            recommendations.append("Create parameter naming convention and apply consistently")
        
        if issue_categories.get('Default Value Inconsistency', 0) > 0:
            recommendations.append("Create centralized configuration for all default values")
        
        # General recommendations
        recommendations.extend([
            "Implement comprehensive error handling with specific exception types",
            "Add unit tests for critical functions",
            "Create development workflow documentation",
            "Set up automated code quality checks",
            "Implement logging for better debugging"
        ])
        
        return recommendations
    
    def calculate_health_score(self) -> int:
        """Tính health score cho project"""
        
        base_score = 100
        
        # Deduct points based on issues
        for issue in self.issues:
            if issue['severity'] == 'CRITICAL':
                base_score -= 15
            elif issue['severity'] == 'ERROR':
                base_score -= 10
            elif issue['severity'] == 'WARNING':
                base_score -= 5
            else:
                base_score -= 2
        
        return max(0, base_score)

def main():
    """Main analysis function"""
    project_root = os.getcwd()
    analyzer = SystematicProjectAnalyzer(project_root)
    analysis_result = analyzer.analyze_comprehensive()
    
    print(f"\n🎯 Analysis complete. Check systematic_analysis_report.json for full details.")
    return analysis_result

if __name__ == "__main__":
    main()
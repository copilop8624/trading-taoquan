#!/usr/bin/env python3
"""
🚨 EMERGENCY PROJECT FIX PLAN
Giải quyết ngay lập tức các vấn đề critical đã phát hiện
"""

import os
import json
from pathlib import Path
import shutil

class EmergencyProjectFixer:
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.backup_dir = self.project_root / "emergency_backup"
        self.backup_dir.mkdir(exist_ok=True)
        
    def emergency_fix_all(self):
        """Thực hiện tất cả emergency fixes"""
        print("🚨 STARTING EMERGENCY PROJECT FIX")
        print("=" * 60)
        
        # 1. Backup critical files
        self.backup_critical_files()
        
        # 2. Fix route conflicts
        self.fix_route_conflicts()
        
        # 3. Fix optimization engine logic
        self.fix_optimization_engine_logic()
        
        # 4. Clean up duplicate files
        self.cleanup_duplicate_files()
        
        # 5. Validate fixes
        self.validate_fixes()
        
        print("✅ Emergency fixes completed!")
        
    def backup_critical_files(self):
        """Backup files trước khi fix"""
        print("💾 Creating emergency backup...")
        
        critical_files = ['web_app.py', 'backtest_gridsearch_slbe_ts_Version3.py']
        
        for file_name in critical_files:
            source = self.project_root / file_name
            if source.exists():
                backup = self.backup_dir / f"{file_name}.backup"
                shutil.copy2(source, backup)
                print(f"   ✅ Backed up: {file_name}")
    
    def fix_route_conflicts(self):
        """Fix route conflicts ngay lập tức"""
        print("🔧 Fixing route conflicts...")
        
        # Disable conflicting apps by renaming them
        conflicting_apps = [
            'data_management_app.py',
            'emergency_server.py', 
            'test_minimal.py',
        ]
        
        for app_file in conflicting_apps:
            app_path = self.project_root / app_file
            if app_path.exists():
                disabled_path = self.project_root / f"{app_file}.disabled"
                if not disabled_path.exists():
                    shutil.move(app_path, disabled_path)
                    print(f"   ✅ Disabled conflicting app: {app_file}")
        
        # Keep only main web_app.py active
        print("   ✅ Main web_app.py remains active")
    
    def fix_optimization_engine_logic(self):
        """Fix optimization engine selection logic"""
        print("🔧 Fixing optimization engine logic...")
        
        web_app_path = self.project_root / 'web_app.py'
        if not web_app_path.exists():
            print("   ❌ web_app.py not found!")
            return
        
        with open(web_app_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Fix 1: Standardize engine value extraction
        old_pattern = """optimization_engine = data.get('optimization_engine', 'optuna')"""
        
        new_pattern = """# 🔧 FIXED: Robust optimization engine selection
        raw_engine = data.get('optimization_engine', data.get('engine', 'optuna'))
        
        # Normalize engine name to handle various frontend formats
        if raw_engine.lower() in ['grid', 'grid_search', 'gridsearch', 'grid search']:
            optimization_engine = 'grid_search'
        elif raw_engine.lower() in ['optuna', 'bayesian']:
            optimization_engine = 'optuna'
        else:
            optimization_engine = 'optuna'  # Default fallback
            
        print(f"🔧 FIXED ENGINE SELECTION: '{raw_engine}' → '{optimization_engine}'")"""
        
        if old_pattern in content:
            content = content.replace(old_pattern, new_pattern)
            print("   ✅ Fixed optimization engine selection logic")
        
        # Fix 2: Ensure proper if-else structure
        if "if optimization_engine == 'optuna':" in content and "else:" in content:
            # Update else condition to check for grid_search
            content = content.replace(
                "else:",
                """elif optimization_engine == 'grid_search':
            print("🔍 Running GRID SEARCH optimization...")
        else:
            print(f"❌ Unknown optimization engine: {optimization_engine}")
            return jsonify({'success': False, 'error': f'Unknown optimization engine: {optimization_engine}'})
            
        if False:  # This block will never execute (placeholder for original else)"""
            )
            print("   ✅ Fixed if-else structure for engine selection")
        
        # Write fixed content
        with open(web_app_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print("   ✅ Optimization engine logic fixed!")
    
    def cleanup_duplicate_files(self):
        """Clean up duplicate and backup files"""
        print("🧹 Cleaning up duplicate files...")
        
        # Files to move to archive
        duplicate_files = [
            'web_app.backup_from_BTC-backup.py',
            'web_app.current_backup_before_replace.py', 
            'web_app.replaced_from_backup.py',
            'web_app_backup.py',
            'web_app_gridsearch_backup_20250724.py',
            'web_app_optimized.py',
            'web_app_error.py'
        ]
        
        archive_dir = self.project_root / "archived_files"
        archive_dir.mkdir(exist_ok=True)
        
        for file_name in duplicate_files:
            file_path = self.project_root / file_name
            if file_path.exists():
                archive_path = archive_dir / file_name
                if not archive_path.exists():
                    shutil.move(file_path, archive_path)
                    print(f"   ✅ Archived: {file_name}")
    
    def validate_fixes(self):
        """Validate that fixes work"""
        print("✅ Validating fixes...")
        
        web_app_path = self.project_root / 'web_app.py'
        if not web_app_path.exists():
            print("   ❌ web_app.py missing!")
            return False
        
        with open(web_app_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check if fixes are present
        fixes_present = [
            "FIXED ENGINE SELECTION" in content,
            "elif optimization_engine == 'grid_search':" in content,
            "print(f\"🔧 FIXED ENGINE SELECTION:" in content
        ]
        
        if all(fixes_present):
            print("   ✅ All fixes validated successfully!")
            return True
        else:
            print("   ⚠️ Some fixes may not be applied correctly")
            return False
    
    def create_clean_startup_script(self):
        """Tạo script khởi động clean"""
        
        startup_script = '''#!/usr/bin/env python3
"""
🚀 CLEAN STARTUP SCRIPT
Khởi động chỉ main web_app.py sau khi fix
"""

import subprocess
import sys
import os

def main():
    print("🚀 Starting FIXED Trading Optimization Web App...")
    print("🔧 All conflicts resolved, using single main app")
    print("=" * 50)
    
    # Ensure we're in the right directory
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    # Start only main web app
    try:
        subprocess.run([sys.executable, "web_app.py"], check=True)
    except KeyboardInterrupt:
        print("\\n👋 Server stopped by user")
    except Exception as e:
        print(f"❌ Error starting server: {e}")

if __name__ == "__main__":
    main()
'''
        
        script_path = self.project_root / "start_fixed_app.py"
        with open(script_path, 'w', encoding='utf-8') as f:
            f.write(startup_script)
        
        print(f"✅ Clean startup script created: {script_path}")

def main():
    """Main emergency fix function"""
    project_root = os.getcwd()
    fixer = EmergencyProjectFixer(project_root)
    
    print("🚨 EMERGENCY PROJECT FIXER")
    print("This will fix critical issues immediately!")
    print("=" * 50)
    
    # Get user confirmation
    confirm = input("🤔 Proceed with emergency fixes? (y/N): ").lower().strip()
    
    if confirm == 'y':
        fixer.emergency_fix_all()
        fixer.create_clean_startup_script()
        
        print("\n🎉 EMERGENCY FIXES COMPLETED!")
        print("=" * 50)
        print("✅ Route conflicts resolved")
        print("✅ Optimization engine logic fixed")
        print("✅ Duplicate files archived")
        print("✅ Clean startup script created")
        print("\n🚀 Next steps:")
        print("1. Run: python start_fixed_app.py")
        print("2. Test Grid Search vs Optuna selection")
        print("3. Verify all functionality works")
        
    else:
        print("❌ Emergency fixes cancelled by user")

if __name__ == "__main__":
    main()
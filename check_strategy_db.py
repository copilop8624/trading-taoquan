#!/usr/bin/env python3
"""
Check strategy database structure
"""
import sqlite3

def check_strategy_db():
    try:
        conn = sqlite3.connect('strategy_management.db')
        cursor = conn.cursor()
        
        # Check tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        print("📊 Tables:", tables)
        
        if tables:
            for table in tables:
                table_name = table[0]
                print(f"\n📋 Table: {table_name}")
                
                # Get table schema
                cursor.execute(f"PRAGMA table_info({table_name});")
                schema = cursor.fetchall()
                print(f"🏗️ Schema: {schema}")
                
                # Get sample data
                cursor.execute(f"SELECT * FROM {table_name} LIMIT 3;")
                data = cursor.fetchall()
                print(f"📄 Sample data: {data}")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    check_strategy_db()
import sqlite3
import os

DB_NAME = 'investimentos.db'

def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def migrate_table(cursor, table_name, schema_definition, columns):
    """
    Creates the table if it doesn't exist, or adds missing columns if it does.
    'columns' is a list of tuples: (column_name, definition)
    """
    # Create table if it doesn't exist
    cursor.execute(f"CREATE TABLE IF NOT EXISTS {table_name} {schema_definition}")
    
    # Check for missing columns
    cursor.execute(f"PRAGMA table_info({table_name})")
    existing_columns = [row['name'] for row in cursor.fetchall()]
    
    for col_name, col_def in columns:
        if col_name not in existing_columns:
            print(f"Migrating: Adding column '{col_name}' to table '{table_name}'")
            cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {col_name} {col_def}")

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Investments Table
    migrate_table(cursor, 'investments', 
        "(id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)",
        [('institution', 'TEXT')]
    )
    
    # 2. Investment History Table
    migrate_table(cursor, 'investment_history',
        "(id INTEGER PRIMARY KEY AUTOINCREMENT, investment_id INTEGER NOT NULL, value DECIMAL(10, 2) NOT NULL, date DATE NOT NULL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY (investment_id) REFERENCES investments(id) ON DELETE CASCADE)",
        [] # Add new history columns here in the future
    )
    
    # 3. Monthly Contributions Table
    migrate_table(cursor, 'monthly_contributions',
        "(id INTEGER PRIMARY KEY AUTOINCREMENT, amount DECIMAL(10, 2) NOT NULL, month_year TEXT NOT NULL, date DATE NOT NULL, description TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)",
        [] # Add new contribution columns here in the future
    )
    
    # 4. Settings Table
    migrate_table(cursor, 'settings',
        "(id INTEGER PRIMARY KEY CHECK (id = 1), annual_interest_rate DECIMAL(5, 2) NOT NULL DEFAULT 14.0, target_goal DECIMAL(15, 2) NOT NULL DEFAULT 100000.0, target_months INTEGER NOT NULL DEFAULT 60)",
        [('initial_wealth', 'DECIMAL(15, 2) NOT NULL DEFAULT 0.0')]
    )
    
    # Initialize default settings
    cursor.execute('INSERT OR IGNORE INTO settings (id, annual_interest_rate, target_goal, target_months) VALUES (1, 14.0, 100000.0, 60)')
    
    # NEW MIGRATION: Seed monthly_contributions from existing investment history if empty
    cursor.execute('SELECT COUNT(*) FROM monthly_contributions')
    if cursor.fetchone()[0] == 0:
        print("Migrating initial history entries to monthly_contributions...")
        cursor.execute('''
            SELECT h.value, h.date, i.name 
            FROM investment_history h
            JOIN (
                SELECT investment_id, MIN(id) as first_id 
                FROM investment_history 
                GROUP BY investment_id
            ) first_entries ON h.id = first_entries.first_id
            JOIN investments i ON h.investment_id = i.id
        ''')
        for row in cursor.fetchall():
            month_year = row['date'][:7] # YYYY-MM
            cursor.execute('''
                INSERT INTO monthly_contributions (amount, month_year, date, description)
                VALUES (?, ?, ?, ?)
            ''', (row['value'], month_year, row['date'], f"Saldo inicial: {row['name']}"))
    
    conn.commit()
    conn.close()
    print("Database synced successfully.")

if __name__ == '__main__':
    init_db()

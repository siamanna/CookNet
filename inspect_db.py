import sqlite3

def get_table_info(db_path, table_name):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = cursor.fetchall()
    conn.close()
    return columns

if __name__ == "__main__":
    db_path = 'recipes.db'
    table_name = 'recipes'
    columns = get_table_info(db_path, table_name)
    print(f"Schema for '{table_name}' table:")
    for col in columns:
        print(col)

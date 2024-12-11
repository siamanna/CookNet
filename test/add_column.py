import sqlite3

def add_ingredients_column(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute("ALTER TABLE recipes ADD COLUMN ingredients TEXT;")
        conn.commit()
        print("Column 'ingredients' added successfully.")
    except sqlite3.OperationalError as e:
        print(f"Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    add_ingredients_column('recipes.db')

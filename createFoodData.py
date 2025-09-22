import sqlite3
import csv
import os
from settings import *
from utils import parse_ingredients, insert_ingredients

def create_tables(conn):
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS Food (
            fdc_id INTEGER PRIMARY KEY,
            description TEXT,
            category TEXT
        );
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS Ingredient (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fdc_id INTEGER,
            ingredient TEXT
        );
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS SubIngredient (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ingredient_id INTEGER,
            sub_ingredient TEXT
        );
    ''')
    conn.commit()


def safe_int(val):
    try:
        return int(val)
    except (TypeError, ValueError):
        return None


def import_food_and_ingredients(conn):
    c = conn.cursor()

    # Load food_category.csv into a dict: id -> description
    food_cat_map = {}
    with open(FOOD_CATEGORY_CSV, 'r', encoding='utf-8') as fcat:
        reader = csv.DictReader(fcat)
        for row in reader:
            food_cat_map[row['id']] = row['description']

    conn.execute('PRAGMA synchronous = OFF')
    conn.execute('PRAGMA journal_mode = MEMORY')
    conn.execute('BEGIN TRANSACTION')

    # --- Import foods from food.csv ---
    food_rows = []
    with open(FOOD_CSV, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            fdc = safe_int(row.get('fdc_id'))
            desc = row.get('description') or row.get('description'.upper())
            food_cat_id = row.get('food_category_id')
            category = food_cat_map.get(food_cat_id) if food_cat_id else None
            if fdc is not None and desc:
                food_rows.append((fdc, desc.strip(), category))
            if len(food_rows) >= BATCH_SIZE:
                c.executemany(
                    'INSERT OR IGNORE INTO Food(fdc_id, description, category) VALUES (?, ?, ?)', food_rows)
                food_rows = []
        if food_rows:
            c.executemany(
                'INSERT OR IGNORE INTO Food(fdc_id, description, category) VALUES (?, ?, ?)', food_rows)

    # --- Import branded_food.csv with ingredients ---
    ingredient_batch = []
    subingredient_batch = []

    with open(BRANDED_CSV, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            fdc = safe_int(row.get('fdc_id'))
            if fdc is None:
                continue
            desc = row.get('description')
            category = row.get('branded_food_category')
            if desc or category:
                c.execute('''
                    INSERT INTO Food(fdc_id, description, category)
                    VALUES (?, ?, ?)
                    ON CONFLICT(fdc_id) DO UPDATE SET
                        description=COALESCE(excluded.description, Food.description),
                        category=COALESCE(excluded.category, Food.category)
                ''', (fdc, desc.strip() if desc else None, category))
            parsed_ings = parse_ingredients(row.get('ingredients'))
            for ing, subs in parsed_ings:
                ingredient_batch.append((fdc, ing, subs))
            if len(ingredient_batch) >= BATCH_SIZE:
                insert_ingredients(c, ingredient_batch, subingredient_batch)
                ingredient_batch = []

        if ingredient_batch:
            insert_ingredients(c, ingredient_batch, subingredient_batch)

    conn.commit()

    c.execute(
        "CREATE INDEX IF NOT EXISTS idx_ingredient_fdc_id ON Ingredient(fdc_id);")
    c.execute(
        "CREATE INDEX IF NOT EXISTS idx_ingredient_name ON Ingredient(ingredient);")
    c.execute(
        "CREATE INDEX IF NOT EXISTS idx_subingredient_ingredient_id ON SubIngredient(ingredient_id);")
    conn.commit()



def build_database():
    if os.path.exists(DB_PATH):
        print(f"Removing existing database '{DB_PATH}'")
        os.remove(DB_PATH)
    conn = sqlite3.connect(DB_PATH)
    print("Creating tables")
    create_tables(conn)
    print("Importing food and ingredients... (Estimated time: 3-5 minutes)")
    import_food_and_ingredients(conn)
    conn.close()
    print(f"Database '{DB_PATH}' created and data imported.")


if __name__ == "__main__":
    build_database()
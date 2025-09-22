import sqlite3
import re
import pandas as pd
from settings import *


def parse_ingredients(ingredient_str):
    if not ingredient_str:
        return []

    s = ingredient_str.upper()

    # Remove unimportant disclaimers and silly prefixes
    disclaimers = [
        r'EXCEPT FOR .*',
        r'FOR COLOR',
        r'CONTAINS TRACES OF .*',
        r'MAY CONTAIN .*',
        r'CANADA GRADE .*',
        r'SEASONING INGREDIENTS?:',
        r'SOLUTION INGREDIENTS?:',
        r'CONTAINS:',
        r'MADE WITH SMILES',
        r'MADE WITH:',
        r'LESS OF:',
        r'BASTED WITH UP TO 16% ADDED SOLUTION OF',
        r'BASTED NTE 16% ADDED SOLUTION OF',
        r'5% OR LESS OF THE FOLLOWING:',
        r'CONTAINS 2%',
        r'BASTED WITH UP TO 16% SOLUTION OF',
        r'BREADED WITH',
        r'NOT MORE THAN 2% SILICON DIOXIDE ADDED TO PREVENT CAKING',
        r'CONTAINING UP TO 15% OF A SOLUTION OF WATER',
        r'PREBROWNED IN',
        r'CONTAINING UP TO 12% OF A SOLUTION OF WATER',
        r'IINGREDIENTS:',
        r'CONTAIN UP TO 18% SOLUTION OF WATER',
        r'COATING INGREDIENTS:',
        r'ADDED AS A PRESERVATIVE',
        r'CONTAINS UP TO 7%',
        r'MECHANICALLY SEPARATED',
        r'ADDS A DIETARILY INSIGNIFICANT AMOUNT OF SATURATED FAT',
        r'OF EACH OF THE FOLLOWING:',
        r'ADDED TO PROTECT FLAVOR',
    ]
    for d in disclaimers:
        s = re.sub(d, '', s, flags=re.IGNORECASE | re.DOTALL)

    # Remove "contains less than" / "2% or less of" prefixes
    s = re.sub(r'CONTAINS LESS THAN [\d% ]*OF:', '', s, flags=re.IGNORECASE)
    s = re.sub(r'CONTAINS 2% OR LESS OF:', '', s, flags=re.IGNORECASE)

    # Remove other prefixes
    prefixes = [r'^INGREDIENTS?:', r'^MADE FROM:']
    for p in prefixes:
        s = re.sub(p, '', s, flags=re.IGNORECASE).strip()

    s = s.replace('*', '').replace('.', ',')  # normalize punctuation

    # Support both () and [] for sub-ingredients
    def split_top_level(text):
        tokens = []
        buf = ''
        level = 0
        for char in text:
            if char in '([':
                level += 1
                buf += char
            elif char in ')]':
                level -= 1
                buf += char
            elif char == ',' and level == 0:
                if buf.strip():
                    tokens.append(buf.strip())
                buf = ''
            else:
                buf += char
        if buf.strip():
            tokens.append(buf.strip())
        return tokens

    def parse_token(token):
        # Check for parentheses or brackets
        m = re.match(r'^(.*?)\((.*)\)$',
                     token) or re.match(r'^(.*?)\[(.*)\]$', token)
        if m:
            parent = m.group(1).strip()
            inside = m.group(2).strip()
            sub_tokens = split_top_level(inside)
            subs = []
            for t in sub_tokens:
                subs += re.split(r'\s+AND/OR\s+|\s+AND\s+|\s+OR\s+', t)
            subs = [s.strip() for s in subs if s.strip()]
            return [(parent, subs)]
        else:
            # Split AND/OR at top level
            parts = re.split(r'\s+AND/OR\s+|\s+AND\s+|\s+OR\s+', token)
            return [(p.strip(), []) for p in parts if p.strip()]

    # Main parsing
    top_tokens = split_top_level(s)
    result = []
    for tok in top_tokens:
        result += parse_token(tok)

    # Final clean-up
    cleaned = []
    for ing, subs in result:
        ing = ing.strip()
        subs = [s.strip() for s in subs if s.strip()]
        if ing:
            cleaned.append((ing, subs))

    return cleaned


def insert_ingredients(c, ingredient_batch, subingredient_batch):
    ing_values = [(fdc, ing) for fdc, ing, _ in ingredient_batch]
    c.executemany(
        'INSERT INTO Ingredient(fdc_id, ingredient) VALUES (?, ?)', ing_values)
    c.execute('SELECT id, fdc_id, ingredient FROM Ingredient WHERE rowid >= last_insert_rowid() - ?',
              (len(ingredient_batch)-1,))
    rows = c.fetchall()
    ing_map = {(fdc, ing): ing_id for ing_id, fdc, ing in rows}
    for fdc, ing, subs in ingredient_batch:
        ing_id = ing_map.get((fdc, ing))
        if ing_id and subs:
            subingredient_batch.extend([(ing_id, sub) for sub in subs])
    if subingredient_batch:
        c.executemany(
            'INSERT INTO SubIngredient(ingredient_id, sub_ingredient) VALUES (?, ?)', subingredient_batch)
        subingredient_batch.clear()


def search_foods_by_description(query, db_path=DB_PATH, limit=None):
    conn = sqlite3.connect(db_path)
    sql = """
        SELECT fdc_id, description, category
        FROM Food
        WHERE description LIKE ?
        ORDER BY description
    """
    param = f"%{query}%"
    if limit is not None:
        sql += " LIMIT ?"
        df = pd.read_sql_query(sql, conn, params=(param, limit))
    else:
        df = pd.read_sql_query(sql, conn, params=(param,))
    conn.close()
    return df


def print_food_search(query, db_path=DB_PATH, limit=None):
    df = search_foods_by_description(query, db_path, limit)
    if df.empty:
        print(f"No foods found for query: '{query}'")
    else:
        print(df)


def get_ingredients_by_fdc_id(fdc_id, db_path=DB_PATH):
    conn = sqlite3.connect(db_path)
    sql = '''
        SELECT i.ingredient, s.sub_ingredient
        FROM Ingredient i
        LEFT JOIN SubIngredient s ON i.id = s.ingredient_id
        WHERE i.fdc_id = ?
        ORDER BY i.id, s.id
    '''
    df = pd.read_sql_query(sql, conn, params=(fdc_id,))
    conn.close()
    # Group by ingredient, collect sub-ingredients
    grouped = {}
    for _, row in df.iterrows():
        ing = row['ingredient']
        sub = row['sub_ingredient']
        if ing not in grouped:
            grouped[ing] = []
        if pd.notnull(sub):
            grouped[ing].append(sub)
    # Build formatted ingredient strings
    result = []
    for ing, subs in grouped.items():
        if subs:
            result.append(f"{ing} (" + ", ".join(subs) + ")")
        else:
            result.append(ing)
    return result


def print_ingredients_by_fdc_id(fdc_id, db_path=DB_PATH):
    ingredients = get_ingredients_by_fdc_id(fdc_id, db_path)
    if not ingredients:
        # Try to get the description from the Food table
        conn = sqlite3.connect(db_path)
        desc = conn.execute(
            'SELECT description FROM Food WHERE fdc_id = ?', (fdc_id,)).fetchone()
        conn.close()
        if desc and desc[0]:
            print(f"No ingredients found for: {desc[0]}, with ID: {fdc_id}")
        else:
            print(f"No ingredients found for fdc_id: {fdc_id}")
    else:
        print(", ".join(ingredients))


def create_food_item(description, ingredients_str, db_path=DB_PATH, category=None):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    # Check if food already exists
    c.execute('SELECT fdc_id FROM Food WHERE description = ?',
              (description.strip(),))
    row = c.fetchone()
    if row:
        fdc_id = row[0]
        print(f"Food item already exists: {description} (fdc_id={fdc_id})")
        conn.close()
        return fdc_id
    # Insert new food item
    c.execute('INSERT INTO Food(description, category) VALUES (?, ?)',
              (description.strip(), category))
    fdc_id = c.lastrowid
    # Parse and insert ingredients
    parsed_ings = parse_ingredients(ingredients_str)
    for ing, subs in parsed_ings:
        c.execute(
            'INSERT INTO Ingredient(fdc_id, ingredient) VALUES (?, ?)', (fdc_id, ing.strip()))
        ingredient_id = c.lastrowid
        for sub in subs:
            c.execute('INSERT INTO SubIngredient(ingredient_id, sub_ingredient) VALUES (?, ?)',
                      (ingredient_id, sub.strip()))
    conn.commit()
    conn.close()
    print(f"Created food item: {description} (fdc_id={fdc_id})")
    return fdc_id


def remove_food_item(fdc_id, db_path=DB_PATH):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    # Find all ingredient ids for this food item
    c.execute('SELECT id FROM Ingredient WHERE fdc_id = ?', (fdc_id,))
    ingredient_ids = [row[0] for row in c.fetchall()]
    # Remove sub-ingredients
    if ingredient_ids:
        c.executemany('DELETE FROM SubIngredient WHERE ingredient_id = ?', [
                      (ing_id,) for ing_id in ingredient_ids])
    # Remove ingredients
    c.execute('DELETE FROM Ingredient WHERE fdc_id = ?', (fdc_id,))
    # Remove food item
    c.execute('DELETE FROM Food WHERE fdc_id = ?', (fdc_id,))
    conn.commit()
    conn.close()
    print(f"Removed food item and all related ingredients for fdc_id={fdc_id}")

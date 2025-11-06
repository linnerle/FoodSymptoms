import sqlite3
from settings import DB_PATH


def clean_duplicates():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    print("Finding duplicate descriptions...")
    # Get descriptions with duplicates (case insensitive)
    c.execute('''
        SELECT LOWER(description) as desc_lower, COUNT(*) as cnt
        FROM Food
        GROUP BY desc_lower
        HAVING cnt > 1
        ORDER BY cnt DESC
    ''')
    groups = c.fetchall()
    print(f"Found {len(groups)} groups of duplicates.")

    total_duplicates = 0
    total_merged = 0

    for desc_lower, cnt in groups:
        print(f"Processing group: '{desc_lower}' ({cnt} duplicates)")
        # Get all foods with this description
        c.execute(
            'SELECT fdc_id, description, category FROM Food WHERE LOWER(description) = ?', (desc_lower,))
        foods = c.fetchall()

        # Separate foods with and without ingredients
        foods_with_ing = []
        foods_without = []

        for fdc_id, desc, cat in foods:
            has_ing = c.execute(
                'SELECT 1 FROM Ingredient WHERE fdc_id = ? LIMIT 1', (fdc_id,)).fetchone()
            if has_ing:
                foods_with_ing.append((fdc_id, desc, cat))
            else:
                foods_without.append((fdc_id, desc, cat))

        if len(foods_with_ing) == 0:
            print(
                f"  All {len(foods)} entries have no ingredients. Keeping first one.")
            # All without ingredients, keep the first one
            keep_fdc = foods_without[0][0]
            to_delete = foods_without[1:]
        elif len(foods_with_ing) == 1:
            print(
                f"  One entry has ingredients, {len(foods_without)} don't. Keeping the one with ingredients.")
            # One with ingredients, keep it
            keep_fdc = foods_with_ing[0][0]
            to_delete = foods_without + foods_with_ing[1:]
        else:
            print(
                f"  {len(foods_with_ing)} entries have ingredients. Merging them.")
            # Multiple with ingredients, merge them
            keep_fdc = foods_with_ing[0][0]
            to_delete = foods_without + foods_with_ing[1:]

            # Collect all unique ingredients and subingredients
            all_ingredients = {}  # ingredient -> set of sub_ingredients

            for fdc_id, _, _ in foods_with_ing:
                c.execute('''
                    SELECT i.ingredient, s.sub_ingredient
                    FROM Ingredient i
                    LEFT JOIN SubIngredient s ON i.id = s.ingredient_id
                    WHERE i.fdc_id = ?
                ''', (fdc_id,))
                rows = c.fetchall()
                print(f"    Food {fdc_id} has {len(rows)} ingredient entries.")
                for ing, sub in rows:
                    if ing not in all_ingredients:
                        all_ingredients[ing] = set()
                    if sub:
                        all_ingredients[ing].add(sub)

            print(
                f"    Merged into {len(all_ingredients)} unique ingredients.")

            # Remove old ingredients for the kept food
            c.execute('SELECT id FROM Ingredient WHERE fdc_id = ?', (keep_fdc,))
            ing_ids = [row[0] for row in c.fetchall()]
            if ing_ids:
                c.executemany('DELETE FROM SubIngredient WHERE ingredient_id = ?', [
                              (id,) for id in ing_ids])
                c.execute('DELETE FROM Ingredient WHERE fdc_id = ?', (keep_fdc,))
                print(f"    Removed old ingredients for kept food {keep_fdc}.")

            # Insert merged ingredients
            for ing, subs in all_ingredients.items():
                c.execute(
                    'INSERT INTO Ingredient(fdc_id, ingredient) VALUES (?, ?)', (keep_fdc, ing))
                ing_id = c.lastrowid
                for sub in subs:
                    c.execute(
                        'INSERT INTO SubIngredient(ingredient_id, sub_ingredient) VALUES (?, ?)', (ing_id, sub))

            total_merged += 1

        # Delete the duplicate foods
        for fdc_id, _, _ in to_delete:
            c.execute('DELETE FROM Food WHERE fdc_id = ?', (fdc_id,))
            print(f"    Deleted duplicate food {fdc_id}.")
            total_duplicates += 1

    conn.commit()
    conn.close()

    print(f"\nCleanup complete!")
    print(f"Deleted {total_duplicates} duplicate entries.")
    print(f"Merged ingredients for {total_merged} groups.")


if __name__ == "__main__":
    clean_duplicates()

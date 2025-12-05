"""
User data caching system for FoodSymptoms app.
Caches user logs, entries, and food data to improve performance.
"""
import pandas as pd
from datetime import datetime, timedelta
from backend.utils import get_db_connection

# Global cache dictionary: {user_id: {data_type: data, 'last_updated': timestamp}}
_user_cache = {}
CACHE_DURATION = timedelta(minutes=5)  # Cache data for 5 minutes


def invalidate_user_cache(user_id):
    """Invalidate (clear) cache for a specific user"""
    if user_id in _user_cache:
        del _user_cache[user_id]


def invalidate_all_cache():
    """Clear all cached data"""
    global _user_cache
    _user_cache = {}


def _is_cache_valid(user_id):
    """Check if cache exists and is still valid"""
    if user_id not in _user_cache:
        return False
    
    last_updated = _user_cache[user_id].get('last_updated')
    if not last_updated:
        return False
    
    return (datetime.now() - last_updated) < CACHE_DURATION


def get_user_data(user_id, force_refresh=False):
    """
    Get all user data (logs, entries, foods, ingredients).
    Returns cached data if available and valid, otherwise queries database.
    
    Returns dict with:
    - daily_logs: DataFrame of all daily logs
    - food_log_entries: DataFrame of all food log entries
    - symptom_log_entries: DataFrame of all symptom log entries
    - foods: DataFrame of all foods consumed by user
    - ingredients: DataFrame of all ingredients in user's foods
    - subingredients: DataFrame of all subingredients
    """
    # Return cached data if valid and not forcing refresh
    if not force_refresh and _is_cache_valid(user_id):
        return _user_cache[user_id]
    
    # Query all user data at once
    conn = get_db_connection()
    
    try:
        # Get all daily logs for user
        daily_logs = pd.read_sql_query('''
            SELECT id, date, user_id
            FROM "dailylog"
            WHERE user_id = %s
        ''', conn, params=(user_id,))
        
        # Get all food log entries for user
        food_log_entries = pd.read_sql_query('''
            SELECT fle.id, fle.daily_log_id, fle.meal_id, fle.fdc_id, 
                   fle.time, fle.notes, dl.date
            FROM "foodlogentry" fle
            JOIN "dailylog" dl ON fle.daily_log_id = dl.id
            WHERE dl.user_id = %s
        ''', conn, params=(user_id,))
        
        # Get all symptom log entries for user
        symptom_log_entries = pd.read_sql_query('''
            SELECT sle.id, sle.daily_log_id, sle.symptom_id, sle.time, 
                   sle.severity, sle.notes, dl.date, s.name as symptom_name
            FROM "symptomlogentry" sle
            JOIN "dailylog" dl ON sle.daily_log_id = dl.id
            JOIN "symptom" s ON sle.symptom_id = s.id
            WHERE dl.user_id = %s
        ''', conn, params=(user_id,))
        
        # Get all unique foods consumed by user
        foods = pd.read_sql_query('''
            SELECT DISTINCT f.fdc_id, f.description, f.category
            FROM "food" f
            JOIN "foodlogentry" fle ON f.fdc_id = fle.fdc_id
            JOIN "dailylog" dl ON fle.daily_log_id = dl.id
            WHERE dl.user_id = %s
        ''', conn, params=(user_id,))
        
        # Get all ingredients for foods consumed by user
        ingredients = pd.read_sql_query('''
            SELECT DISTINCT i.id, i.fdc_id, i.ingredient
            FROM "ingredient" i
            JOIN "foodlogentry" fle ON i.fdc_id = fle.fdc_id
            JOIN "dailylog" dl ON fle.daily_log_id = dl.id
            WHERE dl.user_id = %s
        ''', conn, params=(user_id,))
        
        # Get all subingredients for foods consumed by user
        subingredients = pd.read_sql_query('''
            SELECT DISTINCT si.id, si.ingredient_id, si.sub_ingredient
            FROM "subingredient" si
            JOIN "ingredient" i ON si.ingredient_id = i.id
            JOIN "foodlogentry" fle ON i.fdc_id = fle.fdc_id
            JOIN "dailylog" dl ON fle.daily_log_id = dl.id
            WHERE dl.user_id = %s
        ''', conn, params=(user_id,))
        
        conn.close()
        
        # Store in cache
        user_data = {
            'daily_logs': daily_logs,
            'food_log_entries': food_log_entries,
            'symptom_log_entries': symptom_log_entries,
            'foods': foods,
            'ingredients': ingredients,
            'subingredients': subingredients,
            'last_updated': datetime.now()
        }
        
        _user_cache[user_id] = user_data
        return user_data
        
    except Exception as e:
        conn.close()
        raise e

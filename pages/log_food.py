import dash
from dash import html, dcc, Input, Output, State, callback, ALL
import sqlite3
import pandas as pd
from datetime import datetime
from backend.utils import get_db_connection

dash.register_page(__name__, path='/log-food', order=2)


layout = html.Div([
    html.Div([
        html.H2("Log Food Consumption"),
        html.Label("Search Foods:"),
        dcc.Input(id='food-search-input', type='text',
                  placeholder='Enter food name...'),
        html.Button('Search', id='food-search-btn', n_clicks=0),
        html.Div(id='food-search-results'),
        html.H3("Selected Foods for this Meal:"),
        html.Ul(id='selected-foods-list'),
        html.Label("Meal Time:"),
        dcc.DatePickerSingle(
            id='meal-date', date=datetime.now().date()),
        dcc.Input(id='meal-time', type='text', placeholder='HH:MM',
                  value=datetime.now().strftime('%H:%M')),
        html.Label("Meal Name:"),
        dcc.Input(id='meal-name', type='text',
                  placeholder='Optional meal name...'),
        html.Label("Notes:"),
        dcc.Textarea(id='meal-notes',
                     placeholder='Optional notes for the meal...'),
        html.Button('Save Meal', id='save-meal-btn', n_clicks=0),
        html.Div(id='meal-status')
    ]),

    dcc.Store(id='selected-foods', data=[]),
    dcc.Store(id='search-results', data=[]),
    dcc.Store(id='current-page', data=1),
    dcc.Store(id='total-pages', data=1),
    dcc.Store(id='viewed-ingredients', data=None),
])


def create_paginated_table(results, current_page, total_pages, viewed_ingredients=None):
    start_idx = (current_page - 1) * 10
    end_idx = start_idx + 10
    page_results = results[start_idx:end_idx]

    # Create table with add and view ingredients buttons
    table_rows = []
    for row in page_results:
        # Check if food has ingredients
        try:
            conn = get_db_connection()
            has_ingredients = conn.execute(
                'SELECT COUNT(*) FROM Ingredient WHERE fdc_id = ?', (row['fdc_id'],)).fetchone()[0] > 0
            conn.close()
        except sqlite3.OperationalError:
            has_ingredients = False

        buttons = [html.Button('Add to Meal', id={
                               'type': 'add-to-meal', 'fdc_id': row['fdc_id']}, n_clicks=0)]
        if has_ingredients:
            button_text = 'Hide Ingredients' if viewed_ingredients == row[
                'fdc_id'] else 'View Ingredients'
            buttons.append(html.Button(button_text, id={
                           'type': 'view-ingredients', 'fdc_id': row['fdc_id']}, n_clicks=0, style={'marginLeft': '10px'}))

        table_rows.append(html.Tr([
            html.Td(row['description']),
            html.Td(row['category']),
            html.Td(buttons)
        ]))

    table = html.Table([
        html.Thead(
            html.Tr([html.Th('Description'), html.Th('Category'), html.Th('Action')])),
        html.Tbody(table_rows)
    ], style={'width': '100%', 'border': '1px solid black', 'borderCollapse': 'collapse'})

    # Pagination controls
    pagination_controls = []
    if total_pages > 1:
        prev_disabled = current_page <= 1
        next_disabled = current_page >= total_pages

        pagination_controls.append(html.Button(
            'Previous', id='prev-page-btn', n_clicks=0, disabled=prev_disabled))
        pagination_controls.append(
            html.Span(f"Page {current_page} of {total_pages}", style={'margin': '0 10px'}))
        pagination_controls.append(html.Button(
            'Next', id='next-page-btn', n_clicks=0, disabled=next_disabled))

    content = [
        html.Div(f"Showing {len(page_results)} of {len(results)} results", style={
                 'marginBottom': '10px'}),
        table,
        html.Div(pagination_controls, style={
                 'marginTop': '10px', 'textAlign': 'center'}) if pagination_controls else None
    ]

    # Add ingredients if viewing them
    if viewed_ingredients:
        try:
            conn = get_db_connection()
            food_desc = conn.execute(
                'SELECT description FROM Food WHERE fdc_id = ?', (viewed_ingredients,)).fetchone()
            if food_desc:
                food_desc = food_desc[0]

                ingredients_df = pd.read_sql_query('''
                    SELECT i.ingredient
                    FROM Ingredient i
                    WHERE i.fdc_id = ?
                    ORDER BY i.ingredient
                ''', conn, params=(viewed_ingredients,))

                if not ingredients_df.empty:
                    ingredients_list = []
                    for _, row in ingredients_df.iterrows():
                        ingredients_list.append(html.Li(row['ingredient']))

                    content.extend([
                        html.H4(f"Ingredients for: {food_desc}"),
                        html.Ul(ingredients_list)
                    ])

            conn.close()
        except sqlite3.OperationalError as e:
            if "locked" in str(e).lower():
                content.append(
                    html.Div("Database busy - cannot load ingredients"))
            else:
                content.append(html.Div(f"Database error: {e}"))

    return html.Div(content)


@callback(
    Output('search-results', 'data'),
    Output('current-page', 'data'),
    Output('total-pages', 'data'),
    Output('food-search-results', 'children'),
    Input('food-search-btn', 'n_clicks'),
    State('food-search-input', 'value'),
    prevent_initial_call=True
)
def search_foods_for_log(n_clicks, query):
    if not query:
        return [], 1, 1, "Enter a search term and click Search."

    try:
        conn = get_db_connection()
        sql = """
            SELECT fdc_id, description, category
            FROM Food
            WHERE description LIKE ?
            ORDER BY description
        """
        df = pd.read_sql_query(sql, conn, params=(f'%{query}%',))
        conn.close()

        if df.empty:
            return [], 1, 1, "No foods found."

        results = df.to_dict('records')
        total_pages = (len(results) + 9) // 10

        return results, 1, total_pages, create_paginated_table(results, 1, total_pages, viewed_ingredients=None)
    except sqlite3.OperationalError as e:
        if "locked" in str(e).lower():
            return [], 1, 1, "Database is busy. Please try again."
        else:
            return [], 1, 1, f"Database error: {e}"


@callback(
    Output('current-page', 'data', allow_duplicate=True),
    Output('food-search-results', 'children', allow_duplicate=True),
    Input('prev-page-btn', 'n_clicks'),
    Input('next-page-btn', 'n_clicks'),
    State('current-page', 'data'),
    State('total-pages', 'data'),
    State('search-results', 'data'),
    State('viewed-ingredients', 'data'),
    prevent_initial_call=True
)
def handle_pagination(prev_clicks, next_clicks, current_page, total_pages, results, viewed_ingredients):
    ctx = dash.callback_context
    if not ctx.triggered or not results:
        return current_page, create_paginated_table(results, current_page, total_pages, viewed_ingredients)

    triggered_id = ctx.triggered[0]['prop_id'].split('.')[0]

    if triggered_id == 'prev-page-btn' and current_page > 1:
        new_page = current_page - 1
    elif triggered_id == 'next-page-btn' and current_page < total_pages:
        new_page = current_page + 1
    else:
        new_page = current_page

    return new_page, create_paginated_table(results, new_page, total_pages, viewed_ingredients)


@callback(
    Output('selected-foods', 'data', allow_duplicate=True),
    Output('selected-foods-list', 'children', allow_duplicate=True),
    Output('viewed-ingredients', 'data', allow_duplicate=True),
    Output('food-search-results', 'children', allow_duplicate=True),
    Input({'type': 'add-to-meal', 'fdc_id': ALL}, 'n_clicks'),
    Input({'type': 'view-ingredients', 'fdc_id': ALL}, 'n_clicks'),
    State({'type': 'add-to-meal', 'fdc_id': ALL}, 'id'),
    State({'type': 'view-ingredients', 'fdc_id': ALL}, 'id'),
    State('selected-foods', 'data'),
    State('viewed-ingredients', 'data'),
    State('search-results', 'data'),
    State('current-page', 'data'),
    State('total-pages', 'data'),
    prevent_initial_call=True
)
def handle_food_actions(add_clicks, view_clicks, add_ids, view_ids, selected, viewed_ingredients, results, current_page, total_pages):
    ctx = dash.callback_context
    if not ctx.triggered:
        return dash.no_update, dash.no_update, dash.no_update, dash.no_update

    triggered_prop = ctx.triggered[0]['prop_id']
    if not triggered_prop or triggered_prop == '.':
        return dash.no_update, dash.no_update, dash.no_update, dash.no_update

    import ast
    try:
        triggered_id_dict = ast.literal_eval(triggered_prop.split('.')[0])
        button_type = triggered_id_dict.get('type')
        fdc_id = triggered_id_dict.get('fdc_id')
    except Exception:
        return dash.no_update, dash.no_update, dash.no_update, dash.no_update

    if selected is None:
        selected = []

    selected_changed = False
    viewed_changed = False

    if button_type == 'add-to-meal':
        idx = None
        for i, id_dict in enumerate(add_ids):
            if id_dict.get('type') == button_type and id_dict.get('fdc_id') == fdc_id:
                idx = i
                break
        if fdc_id is not None and idx is not None and add_clicks[idx] > 0:
            if not any(item.get('fdc_id') == fdc_id for item in selected if isinstance(item, dict)):
                try:
                    conn = get_db_connection()
                    desc = conn.execute(
                        'SELECT description FROM Food WHERE fdc_id = ?', (fdc_id,)).fetchone()
                    conn.close()
                    if desc:
                        description = desc[0]
                    else:
                        description = f"Food {fdc_id}"
                except sqlite3.OperationalError:
                    description = f"Food {fdc_id}"

                item = {'fdc_id': fdc_id, 'description': description}
                selected = selected + [item]
                selected_changed = True
    elif button_type == 'view-ingredients':
        old_viewed = viewed_ingredients
        if viewed_ingredients == fdc_id:
            viewed_ingredients = None
        else:
            viewed_ingredients = fdc_id
        viewed_changed = (old_viewed != viewed_ingredients)

    if not selected_changed and not viewed_changed:
        return dash.no_update, dash.no_update, dash.no_update, dash.no_update

    foods_list = []
    for item in selected:
        if isinstance(item, dict) and 'description' in item and 'fdc_id' in item:
            buttons = [
                html.Button('Remove', id={
                    'type': 'remove-from-meal', 'fdc_id': item['fdc_id']}, n_clicks=0, style={'marginLeft': '10px'})
            ]
            try:
                conn = get_db_connection()
                has_ingredients = conn.execute(
                    'SELECT COUNT(*) FROM Ingredient WHERE fdc_id = ?', (item['fdc_id'],)).fetchone()[0] > 0
                conn.close()
            except sqlite3.OperationalError:
                has_ingredients = False
            if has_ingredients:
                button_text = 'View Ingredients'
                buttons.append(html.Button(button_text, id={
                    'type': 'view-ingredients-meal', 'fdc_id': item['fdc_id']}, n_clicks=0, style={'marginLeft': '10px'}))
            foods_list.append(html.Li([
                item['description'],
                *buttons
            ]))

    if viewed_changed:
        table = create_paginated_table(
            results, current_page, total_pages, viewed_ingredients)
    else:
        table = dash.no_update

    return selected, foods_list, viewed_ingredients, table


@callback(
    Output('selected-foods', 'data', allow_duplicate=True),
    Output('selected-foods-list', 'children', allow_duplicate=True),
    Input({'type': 'remove-from-meal', 'fdc_id': ALL}, 'n_clicks'),
    State({'type': 'remove-from-meal', 'fdc_id': ALL}, 'id'),
    State('selected-foods', 'data'),
    prevent_initial_call=True
)
def remove_from_meal(n_clicks_list, ids, selected):
    ctx = dash.callback_context
    if not ctx.triggered or not selected:
        return selected, []

    triggered_prop = ctx.triggered[0]['prop_id']
    import ast
    try:
        triggered_id_dict = ast.literal_eval(triggered_prop.split('.')[0])
        button_type = triggered_id_dict.get('type')
        fdc_id = triggered_id_dict.get('fdc_id')
        idx = None
        for i, id_dict in enumerate(ids):
            if id_dict.get('type') == button_type and id_dict.get('fdc_id') == fdc_id:
                idx = i
                break
    except Exception:
        return selected, []

    if button_type == 'remove-from-meal' and idx is not None and n_clicks_list[idx] > 0:
        selected = [item for item in selected if not (
            isinstance(item, dict) and item.get('fdc_id') == fdc_id)]

    foods_list = []
    for item in selected:
        if isinstance(item, dict) and 'description' in item and 'fdc_id' in item:
            foods_list.append(html.Li([
                item['description'],
                html.Button('Remove', id={
                            'type': 'remove-from-meal', 'fdc_id': item['fdc_id']}, n_clicks=0, style={'marginLeft': '10px'})
            ]))

    return selected, foods_list


@callback(
    Output('meal-status', 'children'),
    Output('selected-foods', 'data', allow_duplicate=True),
    Output('selected-foods-list', 'children', allow_duplicate=True),
    Input('save-meal-btn', 'n_clicks'),
    State('selected-foods', 'data'),
    State('current-user-id', 'data'),
    State('meal-date', 'date'),
    State('meal-time', 'value'),
    State('meal-name', 'value'),
    State('meal-notes', 'value'),
    prevent_initial_call=True
)
def save_meal(n_clicks, selected_foods, user_id, meal_date, meal_time, meal_name, meal_notes):
    if not user_id:
        return "Please log in to save meals.", [], []
    if n_clicks > 0 and selected_foods:
        try:
            try:
                datetime_str = f"{meal_date} {meal_time}"
                logged_time = datetime.strptime(datetime_str, '%Y-%m-%d %H:%M')
            except:
                logged_time = datetime.now()

            date = logged_time.date()
            time = logged_time.strftime('%H:%M')

            conn = get_db_connection()
            c = conn.cursor()
            c.execute(
                'INSERT OR IGNORE INTO DailyLog (user_id, date) VALUES (?, ?)', (user_id, date))
            c.execute(
                'SELECT id FROM DailyLog WHERE user_id = ? AND date = ?', (user_id, date))
            daily_log_id = c.fetchone()[0]

            meal_name = meal_name.strip() if meal_name else None

            # Always assign a meal_id, whether named or not
            c.execute(
                'SELECT MAX(meal_id) FROM FoodLogEntry WHERE meal_id IS NOT NULL')
            max_meal_id = c.fetchone()[0]
            meal_id = (max_meal_id + 1) if max_meal_id is not None else 1

            if meal_name:
                ingredients = set()
                for item in selected_foods:
                    if isinstance(item, dict) and 'fdc_id' in item:
                        ing_df = pd.read_sql_query(
                            'SELECT ingredient FROM Ingredient WHERE fdc_id = ?', conn, params=(item['fdc_id'],))
                        ingredients.update(ing_df['ingredient'].tolist())

                c.execute(
                    'INSERT INTO Food (description, category) VALUES (?, ?)', (meal_name, 'Meal'))
                meal_fdc_id = c.lastrowid

                for ing in ingredients:
                    c.execute(
                        'INSERT INTO Ingredient (fdc_id, ingredient) VALUES (?, ?)', (meal_fdc_id, ing))

                # Insert the named meal as a single FoodLogEntry with a meal_id
                c.execute('INSERT INTO FoodLogEntry (daily_log_id, fdc_id, time, notes, meal_id) VALUES (?, ?, ?, ?, ?)',
                          (daily_log_id, meal_fdc_id, time, meal_notes, meal_id))
            else:
                for item in selected_foods:
                    if isinstance(item, dict) and 'fdc_id' in item:
                        c.execute('INSERT INTO FoodLogEntry (daily_log_id, fdc_id, time, notes, meal_id) VALUES (?, ?, ?, ?, ?)',
                                  (daily_log_id, item['fdc_id'], time, meal_notes, meal_id))
            conn.commit()
            conn.close()
            return f"Meal saved with {len(selected_foods)} foods!", [], []
        except sqlite3.OperationalError as e:
            if "locked" in str(e).lower():
                return "Database is busy. Please try again.", selected_foods, []
            else:
                return f"Database error: {e}", selected_foods, []
    return "", selected_foods, []


@callback(
    Output('viewed-ingredients', 'data', allow_duplicate=True),
    Input({'type': 'view-ingredients-meal', 'fdc_id': ALL}, 'n_clicks'),
    State({'type': 'view-ingredients-meal', 'fdc_id': ALL}, 'id'),
    State('viewed-ingredients', 'data'),
    prevent_initial_call=True
)
def handle_view_ingredients_meal(view_clicks, view_ids, viewed_ingredients):
    import ast
    ctx = dash.callback_context
    if not ctx.triggered:
        return viewed_ingredients
    triggered_prop = ctx.triggered[0]['prop_id']
    try:
        triggered_id_dict = ast.literal_eval(triggered_prop.split('.')[0])
        button_type = triggered_id_dict.get('type')
        fdc_id = triggered_id_dict.get('fdc_id')
        idx = None
        for i, id_dict in enumerate(view_ids):
            if id_dict.get('type') == button_type and id_dict.get('fdc_id') == fdc_id:
                idx = i
                break
    except Exception:
        idx = None
        fdc_id = None
    if button_type == 'view-ingredients-meal' and idx is not None and view_clicks[idx] > 0:
        if viewed_ingredients == fdc_id:
            return None
        else:
            return fdc_id
    return viewed_ingredients

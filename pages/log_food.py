import dash
from dash import html, dcc, Input, Output, State, callback, ALL
import psycopg2
import pandas as pd
from datetime import datetime
from backend.utils import get_db_connection

dash.register_page(__name__, path='/log-food', order=2)


layout = html.Div([
    html.Div([
        html.Div([
            html.H3("Search & Select Foods"),
            html.Div([
                dcc.Input(id='food-search-input', type='text',
                          placeholder='Search for foods...', style={'width': 'calc(100% - 120px)', 'marginRight': '8px'}),
                html.Button('Search', id='food-search-btn', n_clicks=0, style={'width': '100px'})
            ], style={'display': 'flex', 'alignItems': 'center', 'marginBottom': '16px'}),
            html.Div(id='food-search-results', style={'marginBottom': '16px'}),
            html.Label("Selected Foods:"),
            html.Ul(id='selected-foods-list', style={'minHeight': '60px', 'padding': '12px', 'backgroundColor': '#f0f0f0', 'borderRadius': '4px', 'border': '1px solid #e0e0e0'}),
        ], style={'marginBottom': '24px', 'padding': '24px', 'backgroundColor': 'white', 'borderRadius': '8px', 'boxShadow': '0 2px 4px rgba(0,0,0,0.1)'}),
        
        html.Div([
            html.H3("Meal Details"),
            html.Div([
                html.Div([
                    html.Label("Date:"),
                    dcc.DatePickerSingle(
                        id='meal-date', date=datetime.now().date()),
                ], style={'display': 'inline-block', 'marginRight': '16px'}),
                html.Div([
                    html.Label("Time:"),
                    dcc.Input(id='meal-time', type='text', placeholder='HH:MM',
                              value=datetime.now().strftime('%H:%M'), style={'width': '120px'}),
                ], style={'display': 'inline-block', 'verticalAlign': 'top'}),
            ]),
            html.Label("Save This Combination as a New Food Item (Optional):"),
            html.Div([
                dcc.Input(id='meal-name', type='text',
                          placeholder='Enter a name for this food combination...', 
                          style={'width': 'calc(100% - 140px)', 'marginRight': '8px'}),
                html.Button('+ Save to DB', id='save-to-db-btn', n_clicks=0, 
                           style={'width': '130px', 'height': '38px'})
            ], style={'display': 'flex', 'alignItems': 'center', 'marginBottom': '8px'}),
            html.Div(id='save-to-db-status', style={'fontSize': '13px', 'color': '#666', 'marginBottom': '8px'}),
            html.Label("Notes (Optional):", style={'marginTop': '16px', 'fontSize': '14px', 'fontWeight': '500'}),
            dcc.Textarea(id='meal-notes',
                         placeholder='Add any additional details about this meal...', 
                         style={'minHeight': '100px'}),
        ], style={'marginBottom': '24px', 'padding': '24px', 'backgroundColor': 'white', 'borderRadius': '8px', 'boxShadow': '0 2px 4px rgba(0,0,0,0.1)'}),
        
        html.Button('Save Meal', id='save-meal-btn', n_clicks=0, 
                   style={'width': '100%', 'padding': '12px', 'fontSize': '16px'}),
        html.Div(id='meal-status', style={'marginTop': '16px', 'textAlign': 'center', 'fontWeight': 'bold'})
    ], style={'maxWidth': '1000px', 'margin': '0 auto', 'padding': '24px'}),

    dcc.Store(id='selected-foods', data=[]),
    dcc.Store(id='search-results', data=[]),
    dcc.Store(id='current-page', data=1),
    dcc.Store(id='total-pages', data=1),
    dcc.Store(id='viewed-ingredients', data=None),
    dcc.Store(id='saved-meal-fdc', data=None),
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
            with conn.cursor() as cur:
                cur.execute(
                    'SELECT COUNT(*) FROM "ingredient" WHERE fdc_id = %s', (row['fdc_id'],))
                has_ingredients = cur.fetchone()[0] > 0
            conn.close()
        except psycopg2.Error:
            has_ingredients = False

        buttons = [html.Button('Add to Meal', id={
                               'type': 'add-to-meal', 'fdc_id': row['fdc_id']}, n_clicks=0, 
                               className='btn-primary', 
                               style={'padding': '6px 12px', 'fontSize': '13px'})]
        if has_ingredients:
            button_text = 'Hide Ingredients' if viewed_ingredients == row[
                'fdc_id'] else 'View Ingredients'
            buttons.append(html.Button(button_text, id={
                           'type': 'view-ingredients', 'fdc_id': row['fdc_id']}, n_clicks=0, 
                           style={'marginLeft': '8px', 'padding': '6px 12px', 'fontSize': '13px'}))

        table_rows.append(html.Tr([
            html.Td(row['description'], style={'padding': '8px'}),
            html.Td(row['category'], style={'padding': '8px'}),
            html.Td(buttons, style={'padding': '8px', 'whiteSpace': 'nowrap'})
        ]))

    table = html.Div([
        html.Table([
        html.Thead(
            html.Tr([html.Th('Food', style={'padding': '10px', 'textAlign': 'left', 'backgroundColor': '#f8f9fa', 'borderBottom': '2px solid #1976d2', 'color': '#1976d2', 'fontWeight': '600'}), 
                     html.Th('Category', style={'padding': '10px', 'textAlign': 'left', 'backgroundColor': '#f8f9fa', 'borderBottom': '2px solid #1976d2', 'color': '#1976d2', 'fontWeight': '600'}), 
                     html.Th('Actions', style={'padding': '10px', 'textAlign': 'left', 'backgroundColor': '#f8f9fa', 'borderBottom': '2px solid #1976d2', 'color': '#1976d2', 'fontWeight': '600'})])),
        html.Tbody(table_rows)
        ], style={'width': '100%', 'maxWidth': '900px', 'border': '1px solid #e0e0e0', 'borderCollapse': 'collapse', 'borderRadius': '4px', 'overflow': 'hidden'})
    ], style={'display': 'flex', 'justifyContent': 'center'})

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
            with conn.cursor() as cur:
                cur.execute(
                    'SELECT description FROM "food" WHERE fdc_id = %s', (viewed_ingredients,))
                food_desc = cur.fetchone()
                if food_desc:
                    food_desc = food_desc[0]
                    cur.execute(
                        'SELECT ingredient FROM "ingredient" WHERE fdc_id = %s ORDER BY ingredient', (viewed_ingredients,))
                    ingredients = cur.fetchall()
                    if ingredients:
                        ingredients_list = [html.Li(row[0])
                                            for row in ingredients]
                        content.extend([
                            html.H4(f"Ingredients for: {food_desc}"),
                            html.Ul(ingredients_list)
                        ])
            conn.close()
        except psycopg2.Error as e:
            content.append(html.Div(f"Database error: {e}"))

    return html.Div(content)


@callback(
    Output('save-to-db-status', 'children'),
    Output('saved-meal-fdc', 'data'),
    Output('meal-name', 'value'),
    Input('save-to-db-btn', 'n_clicks'),
    State('meal-name', 'value'),
    State('selected-foods', 'data'),
    prevent_initial_call=True
)
def save_combination_to_database(n_clicks, meal_name, selected_foods):
    if n_clicks > 0:
        if not meal_name or not meal_name.strip():
            return "⚠️ Please enter a name for this food combination.", dash.no_update, dash.no_update
        
        if not selected_foods or len(selected_foods) == 0:
            return "⚠️ Please select at least one food item.", dash.no_update, dash.no_update
        
        meal_name = meal_name.strip()
        
        try:
            conn = get_db_connection()
            with conn.cursor() as cur:
                # Check if a food with this name already exists
                cur.execute('SELECT fdc_id FROM "food" WHERE description = %s', (meal_name,))
                existing = cur.fetchone()
                
                if existing:
                    return f"⚠️ A food item named '{meal_name}' already exists in the database.", dash.no_update, dash.no_update
                
                # Collect all ingredients from selected foods
                ingredients = set()
                for item in selected_foods:
                    if isinstance(item, dict) and 'fdc_id' in item:
                        cur.execute(
                            'SELECT ingredient FROM "ingredient" WHERE fdc_id = %s', (item['fdc_id'],))
                        ingredients.update([row[0] for row in cur.fetchall()])
                
                # Create new food entry
                cur.execute(
                    'INSERT INTO "food" (description, category) VALUES (%s, %s) RETURNING fdc_id', 
                    (meal_name, 'Meal'))
                meal_fdc_id = cur.fetchone()[0]
                
                # Add ingredients to the new food
                for ing in ingredients:
                    cur.execute(
                        'INSERT INTO "ingredient" (fdc_id, ingredient) VALUES (%s, %s)', 
                        (meal_fdc_id, ing))
                
                conn.commit()
            conn.close()
            
            return f"✓ '{meal_name}' saved to database successfully!", meal_fdc_id, ""
            
        except psycopg2.Error as e:
            return f"⚠️ Database error: {e}", dash.no_update, dash.no_update
    
    return "", dash.no_update, dash.no_update


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
        sql = '''
            SELECT fdc_id, description, category
            FROM "food"
            WHERE description ILIKE %s
            ORDER BY description
        '''
        df = pd.read_sql_query(sql, conn, params=(f'%{query}%',))
        conn.close()

        if df.empty:
            return [], 1, 1, "No foods found."

        results = df.to_dict('records')
        total_pages = (len(results) + 9) // 10

        return results, 1, total_pages, create_paginated_table(results, 1, total_pages, viewed_ingredients=None)
    except psycopg2.Error as e:
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
                    with conn.cursor() as cur:
                        cur.execute(
                            'SELECT description FROM "food" WHERE fdc_id = %s', (fdc_id,))
                        desc = cur.fetchone()
                    conn.close()
                    if desc:
                        description = desc[0]
                    else:
                        description = f"Food {fdc_id}"
                except psycopg2.Error:
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
                with conn.cursor() as cur:
                    cur.execute(
                        'SELECT COUNT(*) FROM "ingredient" WHERE fdc_id = %s', (item['fdc_id'],))
                    has_ingredients = cur.fetchone()[0] > 0
                conn.close()
            except psycopg2.Error:
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
    State('saved-meal-fdc', 'data'),
    State('meal-notes', 'value'),
    prevent_initial_call=True
)
def save_meal(n_clicks, selected_foods, user_id, meal_date, meal_time, saved_meal_fdc, meal_notes):
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
            with conn.cursor() as cur:
                cur.execute(
                    'INSERT INTO "dailylog" (user_id, date) VALUES (%s, %s) ON CONFLICT (user_id, date) DO NOTHING', (user_id, date))
                cur.execute(
                    'SELECT id FROM "dailylog" WHERE user_id = %s AND date = %s', (user_id, date))
                daily_log_id = cur.fetchone()[0]

                cur.execute(
                    'SELECT MAX(meal_id) FROM "foodlogentry" WHERE meal_id IS NOT NULL')
                max_meal_id = cur.fetchone()[0]
                meal_id = (max_meal_id + 1) if max_meal_id is not None else 1

                # If a saved meal fdc_id exists, log that instead of individual foods
                if saved_meal_fdc:
                    cur.execute('INSERT INTO "foodlogentry" (daily_log_id, fdc_id, time, notes, meal_id) VALUES (%s, %s, %s, %s, %s)',
                                (daily_log_id, saved_meal_fdc, time, meal_notes, meal_id))
                else:
                    # Log individual foods
                    for item in selected_foods:
                        if isinstance(item, dict) and 'fdc_id' in item:
                            cur.execute('INSERT INTO "foodlogentry" (daily_log_id, fdc_id, time, notes, meal_id) VALUES (%s, %s, %s, %s, %s)',
                                        (daily_log_id, item['fdc_id'], time, meal_notes, meal_id))
                conn.commit()
            conn.close()
            return f"Meal saved with {len(selected_foods)} foods!", [], []
        except psycopg2.Error as e:
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

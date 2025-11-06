import plotly.graph_objects as go
from datetime import datetime, timedelta
import dash
from dash import html, dcc, Input, Output, State, dash_table, ALL
import pandas as pd
import sqlite3
from settings import DB_PATH
from utils import create_food_item, remove_food_item

# Initialize the Dash app
app = dash.Dash(__name__, suppress_callback_exceptions=True)


def get_db_connection():
    """Get a database connection with timeout and proper error handling."""
    return sqlite3.connect(DB_PATH, timeout=30.0)


# Layout
app.layout = html.Div([
    dcc.Store(id='login-status', data=False),
    dcc.Store(id='current-user-id', data=None),
    html.Div(id='page-content')
])

# Main layout after login
main_layout = html.Div([
    html.H1("MealMap - Food & Symptom Tracker"),
    html.Div(id='user-info', style={'marginBottom': '20px'}),

    dcc.Tabs(id='main-tabs', value='dashboard', children=[
        dcc.Tab(label='Dashboard', value='dashboard', children=[
            html.Div([
                html.H2("Quick Actions"),
                html.Button('Log Food', id='log-food-btn', n_clicks=0),
                html.Button('Log Symptom', id='log-symptom-btn', n_clicks=0),
                html.Hr(),
                html.H3("Recent Activity"),
                html.Div(id='recent-activity'),
                html.Hr(),
                html.H3("Correlation Overview"),
                html.Div(id='correlation-overview')
            ])
        ]),
        dcc.Tab(label='Log Food', value='log-food', children=[
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
                html.Button('Save Meal', id='save-meal-btn', n_clicks=0),
                html.Div(id='meal-status')
            ])
        ]),
        dcc.Tab(label='Log Symptom', value='log-symptom', children=[
            html.Div([
                html.H2("Log Symptom"),
                html.Label("Symptom:"),
                dcc.Input(id='symptom-input', type='text',
                          placeholder='Enter symptom name...'),
                html.Label("Severity (1-10):"),
                dcc.Slider(id='symptom-severity', min=1, max=10,
                           value=5, marks={i: str(i) for i in range(1, 11)}),
                html.Label("Time of occurrence:"),
                dcc.DatePickerSingle(
                    id='symptom-date', date=datetime.now().date()),
                dcc.Input(id='symptom-time', type='text', placeholder='HH:MM',
                          value=datetime.now().strftime('%H:%M')),
                html.Label("Notes:"),
                dcc.Textarea(id='symptom-notes',
                             placeholder='Optional notes...'),
                html.Button('Save Symptom', id='save-symptom-btn', n_clicks=0),
                html.Div(id='symptom-status')
            ])
        ]),
        dcc.Tab(label='Analysis', value='analysis', children=[
            html.Div([
                html.H2("Correlation Analysis"),
                html.Label("Select Symptom:"),
                dcc.Dropdown(id='analysis-symptom',
                             placeholder='Choose symptom to analyze...'),
                html.Button('Analyze', id='analyze-btn', n_clicks=0),
                html.Div(id='analysis-results')
            ])
        ]),
        dcc.Tab(label='Settings', value='settings', children=[
            html.Div([
                html.H2("User Settings"),
                html.Label("Username:"),
                dcc.Input(id='username-input', type='text',
                          placeholder='Enter username'),
                html.Label("Email:"),
                dcc.Input(id='email-input', type='email',
                          placeholder='Enter email'),
                html.Button('Save Settings',
                            id='save-settings-btn', n_clicks=0),
                html.Div(id='settings-status'),
                html.Hr(),
                html.Button('Logout', id='logout-btn', n_clicks=0,
                            style={'backgroundColor': 'red', 'color': 'white'})
            ])
        ])
    ]),

    dcc.Store(id='selected-foods', data=[]),
    dcc.Store(id='current-meal', data=None),
    dcc.Store(id='search-results', data=[]),
    dcc.Store(id='current-page', data=1),
    dcc.Store(id='total-pages', data=1),
    dcc.Store(id='viewed-ingredients', data=None)
])

# Login layout
login_layout = html.Div([
    html.H1("MealMap - Login"),
    dcc.Tabs([
        dcc.Tab(label='Login', children=[
            html.Div([
                html.Label("Username:"),
                dcc.Input(id='login-username', type='text'),
                html.Label("Password:"),
                dcc.Input(id='login-password', type='password'),
                html.Button('Login', id='login-btn', n_clicks=0),
                html.Div(id='login-message')
            ])
        ]),
        dcc.Tab(label='Sign Up', children=[
            html.Div([
                html.Label("Username:"),
                dcc.Input(id='signup-username', type='text'),
                html.Label("Email:"),
                dcc.Input(id='signup-email', type='email'),
                html.Label("Password:"),
                dcc.Input(id='signup-password', type='password'),
                html.Button('Sign Up', id='signup-btn', n_clicks=0),
                html.Div(id='signup-status')
            ])
        ])
    ])
])

# Callback to switch between login and main layout


@app.callback(
    Output('page-content', 'children'),
    Input('login-status', 'data')
)
def display_page(login_status):
    if login_status:
        return main_layout
    else:
        return login_layout

# Callback for login


@app.callback(
    Output('login-status', 'data'),
    Output('current-user-id', 'data'),
    Output('login-message', 'children'),
    Input('login-btn', 'n_clicks'),
    State('login-username', 'value'),
    State('login-password', 'value'),
    prevent_initial_call=True
)
def login(n_clicks, username, password):
    if n_clicks > 0 and username and password:
        try:
            conn = get_db_connection()
            user = conn.execute(
                'SELECT id FROM User WHERE username = ? AND password = ?', (username, password)).fetchone()
            conn.close()
            if user:
                global current_user_id
                current_user_id = user[0]
                return True, user[0], "Login successful!"
            else:
                return False, None, "Invalid username or password"
        except sqlite3.OperationalError as e:
            if "locked" in str(e).lower():
                return False, None, "Database is busy. Please try again."
            else:
                return False, None, f"Database error: {e}"
    return False, None, ""

# Callback for signup


@app.callback(
    Output('signup-status', 'children'),
    Input('signup-btn', 'n_clicks'),
    State('signup-username', 'value'),
    State('signup-email', 'value'),
    State('signup-password', 'value'),
    prevent_initial_call=True
)
def signup(n_clicks, username, email, password):
    if n_clicks > 0 and username and email and password:
        try:
            conn = get_db_connection()
            c = conn.cursor()
            c.execute('INSERT INTO User (username, email, password) VALUES (?, ?, ?)',
                      (username, email, password))
            conn.commit()
            return "Account created successfully! Please login."
        except sqlite3.IntegrityError:
            return "Username already exists"
        except sqlite3.OperationalError as e:
            if "locked" in str(e).lower():
                return "Database is busy. Please try again."
            else:
                return f"Database error: {e}"
        finally:
            conn.close()
    return ""

# Callback for logout


@app.callback(
    Output('login-status', 'data', allow_duplicate=True),
    Output('current-user-id', 'data', allow_duplicate=True),
    Input('logout-btn', 'n_clicks'),
    prevent_initial_call=True
)
def logout(n_clicks):
    if n_clicks > 0:
        global current_user_id
        current_user_id = None
        return False, None
    return dash.no_update, dash.no_update

# Callback to show user info


@app.callback(
    Output('user-info', 'children'),
    Input('current-user-id', 'data')
)
def show_user_info(user_id):
    if not user_id:
        return ""
    conn = sqlite3.connect(DB_PATH)
    user = conn.execute(
        'SELECT username, email FROM User WHERE id = ?', (user_id,)).fetchone()
    conn.close()
    if user:
        return html.Div([
            html.P(f"Welcome, {user[0]}!"),
            html.P(f"Email: {user[1]}")
        ])
    return "User not found"

# Callback to populate user settings


@app.callback(
    Output('username-input', 'value'),
    Output('email-input', 'value'),
    Input('current-user-id', 'data')
)
def load_user_settings(user_id):
    if not user_id:
        return "", ""
    conn = sqlite3.connect(DB_PATH)
    user = conn.execute(
        'SELECT username, email FROM User WHERE id = ?', (user_id,)).fetchone()
    conn.close()
    if user:
        return user[0], user[1]
    return "", ""

# Callback to save user settings


@app.callback(
    Output('settings-status', 'children'),
    Input('save-settings-btn', 'n_clicks'),
    State('username-input', 'value'),
    State('email-input', 'value'),
    State('current-user-id', 'data'),
    prevent_initial_call=True
)
def save_user_settings(n_clicks, username, email, user_id):
    if not user_id:
        return "Please log in to save settings."
    if n_clicks > 0 and username:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('INSERT OR REPLACE INTO User (id, username, email) VALUES (?, ?, ?)',
                  (user_id, username, email))
        conn.commit()
        conn.close()
        return "Settings saved!"
    return ""

# Callback for recent activity


@app.callback(
    Output('recent-activity', 'children'),
    Input('current-user-id', 'data'),
    Input('save-meal-btn', 'n_clicks'),
    Input('save-symptom-btn', 'n_clicks')
)
def recent_activity(user_id, meal_clicks, symptom_clicks):
    if not user_id:
        return ""
    conn = sqlite3.connect(DB_PATH)
    # Recent meal logs: group by meal_id, show all foods in a meal together
    meal_logs = pd.read_sql_query('''
        SELECT fl.meal_id, fl.date_logged, GROUP_CONCAT(f.description, ', ') AS foods
        FROM FoodLog fl
        JOIN Food f ON fl.fdc_id = f.fdc_id
        WHERE fl.user_id = ?
        GROUP BY fl.meal_id
        ORDER BY fl.date_logged DESC
        LIMIT 5
    ''', conn, params=(user_id,))

    # Recent symptom logs
    symptom_logs = pd.read_sql_query('''
        SELECT sl.date_logged, s.name, sl.severity
        FROM SymptomLog sl
        JOIN Symptom s ON sl.symptom_id = s.id
        WHERE sl.user_id = ?
        ORDER BY sl.date_logged DESC
        LIMIT 5
    ''', conn, params=(user_id,))

    conn.close()

    activity = []
    if not meal_logs.empty:
        activity.append(html.H4("Recent Meals:"))
        for _, row in meal_logs.iterrows():
            activity.append(
                html.P(f"{row['date_logged']}: {row['foods']}"))

    if not symptom_logs.empty:
        activity.append(html.H4("Recent Symptoms:"))
        for _, row in symptom_logs.iterrows():
            activity.append(
                html.P(f"{row['date_logged']}: {row['name']} (Severity: {row['severity']})"))

    return activity if activity else "No recent activity"

# Callback for correlation overview


@app.callback(
    Output('correlation-overview', 'children'),
    Input('current-user-id', 'data'),
    Input('save-meal-btn', 'n_clicks'),
    Input('save-symptom-btn', 'n_clicks')
)
def correlation_overview(user_id, meal_clicks, symptom_clicks):
    if not user_id:
        return ""
    # Overview - count of unique meals and symptoms
    try:
        conn = get_db_connection()
        meal_count = conn.execute(
            'SELECT COUNT(DISTINCT meal_id) FROM FoodLog WHERE user_id = ?', (user_id,)).fetchone()[0]
        symptom_count = conn.execute(
            'SELECT COUNT(*) FROM SymptomLog WHERE user_id = ?', (user_id,)).fetchone()[0]
        conn.close()

        return html.Div([
            html.P(f"Total meals logged: {meal_count}"),
            html.P(f"Total symptoms logged: {symptom_count}")
        ])
    except sqlite3.OperationalError as e:
        if "locked" in str(e).lower():
            return "Database busy - please refresh"
        else:
            return f"Database error: {e}"

# Helper function to create paginated table


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
            has_ingredients = False  # Default to no ingredients if DB error

        buttons = [html.Button('Add to Meal', id={
                               'type': 'add-to-meal', 'fdc_id': row['fdc_id']}, n_clicks=0)]
        if has_ingredients:
            # Change button text based on whether ingredients are being viewed
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
            # Get food description
            food_desc = conn.execute(
                'SELECT description FROM Food WHERE fdc_id = ?', (viewed_ingredients,)).fetchone()
            if food_desc:
                food_desc = food_desc[0]

                # Get ingredients
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

# Callback for food search in log food tab


@app.callback(
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

        # Convert to list of dicts for storage
        results = df.to_dict('records')
        total_pages = (len(results) + 9) // 10  # Ceiling division

        # Display first page
        return results, 1, total_pages, create_paginated_table(results, 1, total_pages, viewed_ingredients=None)
    except sqlite3.OperationalError as e:
        if "locked" in str(e).lower():
            return [], 1, 1, "Database is busy. Please try again."
        else:
            return [], 1, 1, f"Database error: {e}"

# Callback for pagination


@app.callback(
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

# Callback to update display when viewed ingredients changes


@app.callback(
    Output('food-search-results', 'children', allow_duplicate=True),
    Input('viewed-ingredients', 'data'),
    State('search-results', 'data'),
    State('current-page', 'data'),
    State('total-pages', 'data'),
    prevent_initial_call=True
)
def update_ingredients_display(viewed_ingredients, results, current_page, total_pages):
    if not results:
        return ""
    return create_paginated_table(results, current_page, total_pages, viewed_ingredients)

# Callback for quick action buttons to switch tabs


@app.callback(
    Output('main-tabs', 'value'),
    Input('log-food-btn', 'n_clicks'),
    Input('log-symptom-btn', 'n_clicks'),
    prevent_initial_call=True
)
def switch_to_tab(log_food_clicks, log_symptom_clicks):
    ctx = dash.callback_context
    if not ctx.triggered:
        return 'dashboard'

    triggered_id = ctx.triggered[0]['prop_id'].split('.')[0]
    if triggered_id == 'log-food-btn':
        return 'log-food'
    elif triggered_id == 'log-symptom-btn':
        return 'log-symptom'

    return 'dashboard'

# Callback to handle food search actions (add to meal and view ingredients)


@app.callback(
    Output('selected-foods', 'data', allow_duplicate=True),
    Output('selected-foods-list', 'children', allow_duplicate=True),
    Output('viewed-ingredients', 'data', allow_duplicate=True),
    Input({'type': 'add-to-meal', 'fdc_id': ALL}, 'n_clicks'),
    Input({'type': 'view-ingredients', 'fdc_id': ALL}, 'n_clicks'),
    State({'type': 'add-to-meal', 'fdc_id': ALL}, 'id'),
    State({'type': 'view-ingredients', 'fdc_id': ALL}, 'id'),
    State('selected-foods', 'data'),
    State('viewed-ingredients', 'data'),
    prevent_initial_call=True
)
def handle_food_actions(add_clicks, view_clicks, add_ids, view_ids, selected, viewed_ingredients):
    ctx = dash.callback_context
    if not ctx.triggered:
        return selected if selected else [], [], viewed_ingredients

    triggered_prop = ctx.triggered[0]['prop_id']
    if not triggered_prop or triggered_prop == '.':
        return selected if selected else [], [], viewed_ingredients

    # Parse the triggered component ID safely
    import ast
    try:
        triggered_id_dict = ast.literal_eval(triggered_prop.split('.')[0])
        button_type = triggered_id_dict.get('type')
        fdc_id = triggered_id_dict.get('fdc_id')
    except Exception:
        return selected if selected else [], [], viewed_ingredients

    # Handle add to meal
    if selected is None:
        selected = []

    selected_changed = False
    viewed_changed = False

    if button_type == 'add-to-meal':
        # Find index of triggered button
        idx = None
        for i, id_dict in enumerate(add_ids):
            if id_dict.get('type') == button_type and id_dict.get('fdc_id') == fdc_id:
                idx = i
                break
        # Only add if n_clicks for this button > 0
        if fdc_id is not None and idx is not None and add_clicks[idx] > 0:
            # Check if already selected
            if not any(item.get('fdc_id') == fdc_id for item in selected if isinstance(item, dict)):
                # Get description
                try:
                    conn = get_db_connection()
                    desc = conn.execute(
                        'SELECT description FROM Food WHERE fdc_id = ?', (fdc_id,)).fetchone()
                    conn.close()
                    if desc:
                        description = desc[0]
                    else:
                        description = f"Food {fdc_id}"  # fallback if not found
                except sqlite3.OperationalError:
                    description = f"Food {fdc_id}"  # fallback if database busy

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

    # Only update display if something changed
    if not selected_changed and not viewed_changed:
        return dash.no_update, dash.no_update, dash.no_update

    # Create list display with remove and view ingredients buttons
    foods_list = []
    for item in selected:
        if isinstance(item, dict) and 'description' in item and 'fdc_id' in item:
            buttons = [
                html.Button('Remove', id={
                    'type': 'remove-from-meal', 'fdc_id': item['fdc_id']}, n_clicks=0, style={'marginLeft': '10px'})
            ]
            # Check if food has ingredients
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
    return selected, foods_list, viewed_ingredients

# Callback to remove food from selected foods


@app.callback(
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
        # Find index of triggered button
        idx = None
        for i, id_dict in enumerate(ids):
            if id_dict.get('type') == button_type and id_dict.get('fdc_id') == fdc_id:
                idx = i
                break
    except Exception:
        return selected, []

    # Only remove if n_clicks for this button > 0
    if button_type == 'remove-from-meal' and idx is not None and n_clicks_list[idx] > 0:
        selected = [item for item in selected if not (
            isinstance(item, dict) and item.get('fdc_id') == fdc_id)]

    # Create list display with remove buttons
    foods_list = []
    for item in selected:
        if isinstance(item, dict) and 'description' in item and 'fdc_id' in item:
            foods_list.append(html.Li([
                item['description'],
                html.Button('Remove', id={
                            'type': 'remove-from-meal', 'fdc_id': item['fdc_id']}, n_clicks=0, style={'marginLeft': '10px'})
            ]))

    return selected, foods_list

# Callback to save meal


@app.callback(
    Output('meal-status', 'children'),
    Output('selected-foods', 'data', allow_duplicate=True),
    Output('selected-foods-list', 'children', allow_duplicate=True),
    Input('save-meal-btn', 'n_clicks'),
    State('selected-foods', 'data'),
    State('current-user-id', 'data'),
    State('meal-date', 'date'),
    State('meal-time', 'value'),
    prevent_initial_call=True
)
def save_meal(n_clicks, selected_foods, user_id, meal_date, meal_time):
    if not user_id:
        return "Please log in to save meals.", [], []
    if n_clicks > 0 and selected_foods:
        try:
            # Parse datetime
            try:
                datetime_str = f"{meal_date} {meal_time}"
                logged_time = datetime.strptime(datetime_str, '%Y-%m-%d %H:%M')
            except:
                logged_time = datetime.now()

            conn = get_db_connection()
            c = conn.cursor()
            # Generate a new meal_id (use max(meal_id)+1 or autoincrement)
            c.execute('SELECT MAX(meal_id) FROM FoodLog')
            max_meal_id = c.fetchone()[0]
            meal_id = (max_meal_id + 1) if max_meal_id is not None else 1
            for item in selected_foods:
                if isinstance(item, dict) and 'fdc_id' in item:
                    c.execute('INSERT INTO FoodLog (user_id, fdc_id, date_logged, meal_id) VALUES (?, ?, ?, ?)',
                              (user_id, item['fdc_id'], logged_time, meal_id))
            conn.commit()
            conn.close()
            return f"Meal saved with {len(selected_foods)} foods!", [], []
        except sqlite3.OperationalError as e:
            if "locked" in str(e).lower():
                return "Database is busy. Please try again.", selected_foods, []
            else:
                return f"Database error: {e}", selected_foods, []
    return "", selected_foods, []

# Callback to save symptom


@app.callback(
    Output('symptom-status', 'children'),
    Input('save-symptom-btn', 'n_clicks'),
    State('symptom-input', 'value'),
    State('symptom-severity', 'value'),
    State('symptom-date', 'date'),
    State('symptom-time', 'value'),
    State('symptom-notes', 'value'),
    State('current-user-id', 'data')
)
def save_symptom(n_clicks, symptom_name, severity, date, time, notes, user_id):
    if not user_id:
        return "Please log in to log symptoms."
    if n_clicks > 0 and symptom_name:
        try:
            # Add symptom if it doesn't exist
            conn = get_db_connection()
            c = conn.cursor()
            c.execute(
                'INSERT OR IGNORE INTO Symptom (name) VALUES (?)', (symptom_name,))
            symptom_id = c.execute(
                'SELECT id FROM Symptom WHERE name = ?', (symptom_name,)).fetchone()[0]

            # Parse datetime
            try:
                datetime_str = f"{date} {time}"
                logged_time = datetime.strptime(datetime_str, '%Y-%m-%d %H:%M')
            except:
                logged_time = datetime.now()

            c.execute('INSERT INTO SymptomLog (user_id, symptom_id, severity, notes, date_logged) VALUES (?, ?, ?, ?, ?)',
                      (user_id, symptom_id, severity, notes, logged_time))
            conn.commit()
            conn.close()
            return f"Symptom '{symptom_name}' logged!"
        except sqlite3.OperationalError as e:
            if "locked" in str(e).lower():
                return "Database is busy. Please try again."
            else:
                return f"Database error: {e}"
    return ""

# Callback to populate analysis symptom dropdown


@app.callback(
    Output('analysis-symptom', 'options'),
    Input('analyze-btn', 'n_clicks')
)
def populate_analysis_symptoms(_):
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT name FROM Symptom ORDER BY name", conn)
    conn.close()
    options = [{'label': sym, 'value': sym} for sym in df['name'].tolist()]
    return options

# Callback for analysis


@app.callback(
    Output('analysis-results', 'children'),
    Input('analyze-btn', 'n_clicks'),
    State('analysis-symptom', 'value'),
    State('current-user-id', 'data')
)
def analyze_correlations(n_clicks, symptom_name, user_id):
    if not user_id:
        return "Please log in to analyze correlations."
    if n_clicks == 0 or not symptom_name:
        return ""

    # Get symptom ID
    conn = sqlite3.connect(DB_PATH)
    symptom_id = conn.execute(
        'SELECT id FROM Symptom WHERE name = ?', (symptom_name,)).fetchone()
    if not symptom_id:
        return "Symptom not found"
    symptom_id = symptom_id[0]

    # Get all ingredients and their correlation with the symptom
    # Simple correlation: count co-occurrences within 24 hours
    correlations = {}

    # Get symptom logs
    symptom_logs = pd.read_sql_query('''
        SELECT date_logged FROM SymptomLog 
        WHERE user_id = ? AND symptom_id = ?
        ORDER BY date_logged
    ''', conn, params=(user_id, symptom_id))

    for _, sym_row in symptom_logs.iterrows():
        sym_time = datetime.fromisoformat(sym_row['date_logged'])

        # Get meals eaten in the 24 hours before symptom
        start_time = sym_time - timedelta(hours=24)
        meal_ids = pd.read_sql_query('''
            SELECT DISTINCT meal_id FROM FoodLog
            WHERE user_id = ? AND date_logged BETWEEN ? AND ?
        ''', conn, params=(user_id, start_time.isoformat(), sym_time.isoformat()))

        for _, meal_row in meal_ids.iterrows():
            meal_id = meal_row['meal_id']
            # Get all foods in this meal
            food_logs = pd.read_sql_query('''
                SELECT fdc_id FROM FoodLog WHERE user_id = ? AND meal_id = ?
            ''', conn, params=(user_id, meal_id))
            for _, food_row in food_logs.iterrows():
                fdc_id = food_row['fdc_id']
                # Get ingredients for this food
                ingredients = pd.read_sql_query('''
                    SELECT i.ingredient FROM Ingredient i WHERE i.fdc_id = ?
                ''', conn, params=(fdc_id,))
                for _, ing_row in ingredients.iterrows():
                    ing = ing_row['ingredient']
                    if ing not in correlations:
                        correlations[ing] = 0
                    correlations[ing] += 1

    conn.close()

    if not correlations:
        return "No correlations found"

    # Sort by correlation score
    sorted_correlations = sorted(
        correlations.items(), key=lambda x: x[1], reverse=True)

    # Create bar chart
    import plotly.graph_objects as go

    fig = go.Figure(data=[
        go.Bar(x=[ing for ing, score in sorted_correlations[:10]],
               y=[score for ing, score in sorted_correlations[:10]])
    ])
    fig.update_layout(title=f"Top 10 Ingredients Correlated with {symptom_name}",
                      xaxis_title="Ingredient", yaxis_title="Correlation Score")

    return html.Div([
        html.H3(f"Correlation Analysis for {symptom_name}"),
        dcc.Graph(figure=fig),
        html.H4("Ingredient Rankings:"),
        html.Ul([html.Li(f"{ing}: {score}")
                for ing, score in sorted_correlations[:10]])
    ])


@app.callback(
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
    # Toggle viewed_ingredients
    if button_type == 'view-ingredients-meal' and idx is not None and view_clicks[idx] > 0:
        if viewed_ingredients == fdc_id:
            return None
        else:
            return fdc_id
    return viewed_ingredients


if __name__ == '__main__':
    app.run_server(debug=True)

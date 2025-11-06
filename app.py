import plotly.graph_objects as go
from datetime import datetime, timedelta, date
import calendar
import json
import dash
from dash import html, dcc, Input, Output, State, ALL
import pandas as pd
import sqlite3
from settings import DB_PATH

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
                html.H3("Calendar View"),
                html.Div(id='calendar-view')
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
                html.Label("Meal Name:"),
                dcc.Input(id='meal-name', type='text',
                          placeholder='Optional meal name...'),
                html.Label("Notes:"),
                dcc.Textarea(id='meal-notes',
                             placeholder='Optional notes for the meal...'),
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
    dcc.Store(id='viewed-ingredients', data=None),
    dcc.Store(id='calendar-refresh', data=0),

    # Entry details modal
    html.Div(
        id='entry-modal',
        style={'display': 'none', 'position': 'fixed', 'zIndex': 1000, 'left': 0, 'top': 0,
               'width': '100%', 'height': '100%', 'backgroundColor': 'rgba(0,0,0,0.4)'},
        children=[
            html.Div(
                style={'backgroundColor': '#fefefe', 'margin': '15% auto', 'padding': '20px',
                       'border': '1px solid #888', 'width': '80%', 'maxWidth': '500px'},
                children=[
                    html.H3("Entry Details"),
                    html.Div(id='entry-details'),
                    html.Button('Close', id='close-modal-btn',
                                n_clicks=0, style={'marginTop': '10px'})
                ]
            )
        ]
    )
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
            html.P(f"Welcome, {user[0]}"),
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
        SELECT fle.meal_id, dl.date || ' ' || fle.time as date_logged, GROUP_CONCAT(f.description, ', ') AS foods
        FROM FoodLogEntry fle
        JOIN DailyLog dl ON fle.daily_log_id = dl.id
        JOIN Food f ON fle.fdc_id = f.fdc_id
        WHERE dl.user_id = ?
        GROUP BY fle.meal_id
        ORDER BY dl.date DESC, fle.time DESC
        LIMIT 5
    ''', conn, params=(user_id,))

    # Recent symptom logs
    symptom_logs = pd.read_sql_query('''
        SELECT dl.date || ' ' || sle.time as date_logged, s.name, sle.severity
        FROM SymptomLogEntry sle
        JOIN DailyLog dl ON sle.daily_log_id = dl.id
        JOIN Symptom s ON sle.symptom_id = s.id
        WHERE dl.user_id = ?
        ORDER BY dl.date DESC, sle.time DESC
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

# Callback for calendar view


@app.callback(
    Output('calendar-view', 'children'),
    Input('current-user-id', 'data'),
    Input('save-meal-btn', 'n_clicks'),
    Input('save-symptom-btn', 'n_clicks'),
    Input('calendar-refresh', 'data'),
    Input('main-tabs', 'value')  # refresh calendar when switching tabs
)
def calendar_view(user_id, meal_clicks, symptom_clicks, refresh_trigger, current_tab):
    if not user_id:
        return ""

    today = date.today()
    year = today.year
    month = today.month

    # Get first and last day of month
    first_day = date(year, month, 1)
    last_day = calendar.monthrange(year, month)[1]
    last_date = date(year, month, last_day)

    # Query individual entries for the month
    conn = get_db_connection()

    # Query food entries
    food_df = pd.read_sql_query('''
        SELECT dl.date, fle.id as entry_id, f.description as name, fle.time, fle.notes, fle.meal_id
        FROM DailyLog dl
        JOIN FoodLogEntry fle ON dl.id = fle.daily_log_id
        JOIN Food f ON fle.fdc_id = f.fdc_id
        WHERE dl.user_id = ? AND dl.date BETWEEN ? AND ?
        ORDER BY dl.date, fle.time
    ''', conn, params=(user_id, first_day.isoformat(), last_date.isoformat()))

    # Query symptom entries
    symptom_df = pd.read_sql_query('''
        SELECT dl.date, sle.id as entry_id, s.name, sle.time, sle.severity, sle.notes
        FROM DailyLog dl
        JOIN SymptomLogEntry sle ON dl.id = sle.daily_log_id
        JOIN Symptom s ON sle.symptom_id = s.id
        WHERE dl.user_id = ? AND dl.date BETWEEN ? AND ?
        ORDER BY dl.date, sle.time
    ''', conn, params=(user_id, first_day.isoformat(), last_date.isoformat()))

    conn.close()

    # Group by date
    entries = {}
    for _, row in food_df.iterrows():
        d = row['date']
        if d not in entries:
            entries[d] = {'meals': {}, 'symptoms': [], 'foods': []}
        meal_id = row['meal_id']
        if meal_id:
            if meal_id not in entries[d]['meals']:
                entries[d]['meals'][meal_id] = {
                    'time': row['time'],
                    'foods': []
                }
            entries[d]['meals'][meal_id]['foods'].append({
                'id': row['entry_id'],
                'name': row['name'],
                'notes': row['notes']
            })
        else:
            entries[d]['foods'].append({
                'id': row['entry_id'],
                'name': row['name'],
                'time': row['time'],
                'notes': row['notes']
            })

    for _, row in symptom_df.iterrows():
        d = row['date']
        if d not in entries:
            entries[d] = {'meals': {}, 'symptoms': [], 'foods': []}
        entries[d]['symptoms'].append({
            'id': row['entry_id'],
            'name': row['name'],
            'time': row['time'],
            'severity': row['severity'],
            'notes': row['notes']
        })    # Generate calendar
    cal = calendar.monthcalendar(year, month)

    def create_entry_cards(entry_list, entry_type):
        cards = []
        if entry_type == 'meal':
            for meal_id, meal_data in entry_list.items():
                food_names = [f"{f['name']}" for f in meal_data['foods']]
                card_text = f"{', '.join(food_names)} ({meal_data['time']})"
                card = html.Button(
                    card_text,
                    id={'type': 'entry', 'entry_type': 'meal', 'entry_id': meal_id},
                    style={'display': 'block', 'margin': '2px', 'padding': '5px', 'fontSize': '10px',
                           'backgroundColor': '#e0f0e0', 'border': '1px solid #ccc', 'cursor': 'pointer', 'textAlign': 'left'}
                )
                cards.append(card)
        elif entry_type == 'food':
            for entry in entry_list:
                card = html.Button(
                    f"{entry['name']} ({entry['time']})",
                    id={'type': 'entry', 'entry_type': 'food',
                        'entry_id': entry['id']},
                    style={'display': 'block', 'margin': '2px', 'padding': '5px', 'fontSize': '10px',
                           'backgroundColor': '#f0e0f0', 'border': '1px solid #ccc', 'cursor': 'pointer', 'textAlign': 'left'}
                )
                cards.append(card)
        elif entry_type == 'symptom':
            for entry in entry_list:
                card = html.Button(
                    f"{entry['name']} ({entry['time']})",
                    id={'type': 'entry', 'entry_type': 'symptom',
                        'entry_id': entry['id']},
                    style={'display': 'block', 'margin': '2px', 'padding': '5px', 'fontSize': '10px',
                           'backgroundColor': '#ffe0e0', 'border': '1px solid #ccc', 'cursor': 'pointer'}
                )
                cards.append(card)
        return cards

    calendar_html = html.Table([
        html.Thead(html.Tr([html.Th(day, style={'textAlign': 'center', 'width': '14.28%'}) for day in [
                   'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']])),
        html.Tbody([
            html.Tr([
                html.Td([
                    html.Div(str(day), style={
                             'fontWeight': 'bold', 'marginBottom': '5px'}) if day != 0 else "",
                    html.Div(
                        create_entry_cards(
                            entries.get(
                                f"{year}-{month:02d}-{day:02d}", {}).get('meals', {}),
                            'meal'
                        ) + create_entry_cards(
                            entries.get(
                                f"{year}-{month:02d}-{day:02d}", {}).get('foods', []),
                            'food'
                        ) + create_entry_cards(
                            entries.get(
                                f"{year}-{month:02d}-{day:02d}", {}).get('symptoms', []),
                            'symptom'
                        )
                    ) if day != 0 else ""
                ], style={'height': '120px', 'verticalAlign': 'top', 'padding': '5px', 'border': '1px solid #ddd', 'width': '14.28%'}) for day in week
            ]) for week in cal
        ])
    ], style={'width': '80%', 'borderCollapse': 'collapse', 'margin': '0 auto', 'tableLayout': 'fixed'})

    return calendar_html

# Callback for entry modal


@app.callback(
    Output('entry-modal', 'style'),
    Output('entry-details', 'children'),
    Input({'type': 'entry', 'entry_type': ALL, 'entry_id': ALL}, 'n_clicks'),
    Input('close-modal-btn', 'n_clicks'),
    State('entry-modal', 'style'),
    prevent_initial_call=True
)
def manage_entry_modal(entry_clicks, close_clicks, current_style):
    ctx = dash.callback_context
    if not ctx.triggered:
        return {'display': 'none'}, ""

    trigger_id = ctx.triggered[0]['prop_id']

    if 'close-modal-btn' in trigger_id and close_clicks > 0:
        return {'display': 'none'}, ""

    # Check if any entry button was clicked
    if not any(click > 0 for click in entry_clicks if click is not None):
        return current_style, ""

    # Find which entry was clicked
    if ctx.triggered and len(ctx.triggered) > 0:
        trigger_id = ctx.triggered[0]['prop_id']
        if trigger_id and trigger_id != '.' and not 'close-modal-btn' in trigger_id:
            import json
            try:
                id_str = trigger_id.split('.')[0]
                id_dict = json.loads(id_str)
                entry_type = id_dict['entry_type']
                entry_id = id_dict['entry_id']

                conn = get_db_connection()
                if entry_type == 'meal':
                    # For meals, show ingredients (food items) and subingredients (all ingredients from those foods)
                    # Get foods in the meal
                    foods_df = pd.read_sql_query('''
                        SELECT f.description, fle.time, fle.notes
                        FROM FoodLogEntry fle
                        JOIN Food f ON fle.fdc_id = f.fdc_id
                        WHERE fle.meal_id = ?
                        ORDER BY fle.time
                    ''', conn, params=(entry_id,))
                    if not foods_df.empty:
                        # Ingredients: the food items
                        ingredients_list = [html.Li(
                            f"{row['description']} - {row['time']}") for _, row in foods_df.iterrows()]

                        # Subingredients: all ingredients from those foods
                        fdc_df = pd.read_sql_query('''
                            SELECT DISTINCT fle.fdc_id
                            FROM FoodLogEntry fle
                            WHERE fle.meal_id = ?
                        ''', conn, params=(entry_id,))
                        if not fdc_df.empty:
                            fdc_ids = tuple(fdc_df['fdc_id'].tolist())
                            placeholders = ','.join('?' * len(fdc_ids))
                            subing_df = pd.read_sql_query(f'''
                                SELECT GROUP_CONCAT(i.ingredient) as all_ingredients
                                FROM Ingredient i
                                WHERE i.fdc_id IN ({placeholders})
                            ''', conn, params=fdc_ids)
                            all_subingredients = subing_df.iloc[0][
                                'all_ingredients'] if not subing_df.empty and subing_df.iloc[0]['all_ingredients'] else 'None'
                        else:
                            all_subingredients = 'None'

                        meal_notes = foods_df['notes'].iloc[0] if not foods_df['notes'].isna(
                        ).all() else None
                        food_names = ', '.join(
                            foods_df['description'].tolist())
                        details_list = [
                            html.H4(food_names),
                            html.H5("Ingredients:"),
                            html.Ul(ingredients_list),
                            html.H5("Subingredients:"),
                            html.P(all_subingredients)
                        ]
                        if meal_notes:
                            details_list.append(html.P(f"Notes: {meal_notes}"))
                        details_list.append(html.Button('Delete', id={'type': 'delete-entry', 'entry_type': 'meal', 'entry_id': entry_id}, n_clicks=0, style={
                                            'marginTop': '10px', 'backgroundColor': 'red', 'color': 'white'}))
                        details = html.Div(details_list)
                    else:
                        details = "Meal not found"
                elif entry_type == 'food':
                    df = pd.read_sql_query('''
                        SELECT f.description, fle.time, fle.notes, fle.meal_id,
                               GROUP_CONCAT(i.ingredient) as ingredients
                        FROM FoodLogEntry fle
                        JOIN Food f ON fle.fdc_id = f.fdc_id
                        LEFT JOIN Ingredient i ON f.fdc_id = i.fdc_id
                        WHERE fle.id = ?
                        GROUP BY fle.id
                    ''', conn, params=(entry_id,))
                    if not df.empty:
                        row = df.iloc[0]
                        details = html.Div([
                            html.H4("Food Entry Details"),
                            html.P(f"Food: {row['description']}"),
                            html.P(f"Time: {row['time']}"),
                            html.P(f"Notes: {row['notes'] or 'None'}"),
                            html.P(
                                f"Ingredients: {row['ingredients'] or 'None'}"),
                            html.Button('Delete', id={'type': 'delete-entry', 'entry_type': 'food', 'entry_id': entry_id}, n_clicks=0, style={
                                        'marginTop': '10px', 'backgroundColor': 'red', 'color': 'white'})
                        ])
                    else:
                        details = "Entry not found"
                elif entry_type == 'symptom':
                    df = pd.read_sql_query('''
                        SELECT s.name, sle.time, sle.severity, sle.notes
                        FROM SymptomLogEntry sle
                        JOIN Symptom s ON sle.symptom_id = s.id
                        WHERE sle.id = ?
                    ''', conn, params=(entry_id,))
                    if not df.empty:
                        row = df.iloc[0]
                        details = html.Div([
                            html.H4("Symptom Entry Details"),
                            html.P(f"Symptom: {row['name']}"),
                            html.P(f"Time: {row['time']}"),
                            html.P(f"Severity: {row['severity']}/10"),
                            html.P(f"Notes: {row['notes'] or 'None'}"),
                            html.Button('Delete', id={'type': 'delete-entry', 'entry_type': 'symptom', 'entry_id': entry_id},
                                        n_clicks=0, style={'marginTop': '10px', 'backgroundColor': 'red', 'color': 'white'})
                        ])
                    else:
                        details = "Entry not found"
                conn.close()
                return {'display': 'block', 'position': 'fixed', 'zIndex': 1000, 'left': 0, 'top': 0, 'width': '100%', 'height': '100%', 'backgroundColor': 'rgba(0,0,0,0.4)'}, details
            except Exception as e:
                return current_style, f"Error: {e}"

    return current_style, ""


@app.callback(
    Output('entry-modal', 'style', allow_duplicate=True),
    Output('calendar-refresh', 'data'),
    Input({'type': 'delete-entry', 'entry_type': ALL, 'entry_id': ALL}, 'n_clicks'),
    State('current-user-id', 'data'),
    State('calendar-refresh', 'data'),
    prevent_initial_call=True
)
def delete_entry(delete_clicks, user_id, current_refresh):
    ctx = dash.callback_context
    if not ctx.triggered:
        return dash.no_update

    # Check if any delete button was actually clicked
    if not any(click > 0 for click in delete_clicks if click is not None):
        return dash.no_update, dash.no_update

    trigger_id = ctx.triggered[0]['prop_id']
    import json
    id_str = trigger_id.split('.')[0]
    id_dict = json.loads(id_str)
    entry_type = id_dict['entry_type']
    entry_id = id_dict['entry_id']

    conn = get_db_connection()
    if entry_type == 'meal':
        conn.execute(
            'DELETE FROM FoodLogEntry WHERE meal_id = ? AND daily_log_id IN (SELECT id FROM DailyLog WHERE user_id = ?)', (entry_id, user_id))
    elif entry_type == 'food':
        conn.execute(
            'DELETE FROM FoodLogEntry WHERE id = ? AND daily_log_id IN (SELECT id FROM DailyLog WHERE user_id = ?)', (entry_id, user_id))
    elif entry_type == 'symptom':
        conn.execute(
            'DELETE FROM SymptomLogEntry WHERE id = ? AND daily_log_id IN (SELECT id FROM DailyLog WHERE user_id = ?)', (entry_id, user_id))
    conn.commit()
    conn.close()
    return {'display': 'none'}, current_refresh + 1

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
    State('meal-name', 'value'),
    State('meal-notes', 'value'),
    prevent_initial_call=True
)
def save_meal(n_clicks, selected_foods, user_id, meal_date, meal_time, meal_name, meal_notes):
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

            date = logged_time.date()
            time = logged_time.strftime('%H:%M')

            conn = get_db_connection()
            c = conn.cursor()
            # Get or create DailyLog
            c.execute(
                'INSERT OR IGNORE INTO DailyLog (user_id, date) VALUES (?, ?)', (user_id, date))
            c.execute(
                'SELECT id FROM DailyLog WHERE user_id = ? AND date = ?', (user_id, date))
            daily_log_id = c.fetchone()[0]

            meal_name = meal_name.strip() if meal_name else None

            if meal_name:
                # Get all ingredients from selected foods
                ingredients = set()
                for item in selected_foods:
                    if isinstance(item, dict) and 'fdc_id' in item:
                        ing_df = pd.read_sql_query(
                            'SELECT ingredient FROM Ingredient WHERE fdc_id = ?', conn, params=(item['fdc_id'],))
                        ingredients.update(ing_df['ingredient'].tolist())

                # Insert into Food
                c.execute(
                    'INSERT INTO Food (description, category) VALUES (?, ?)', (meal_name, 'Meal'))
                meal_fdc_id = c.lastrowid

                # Insert ingredients
                for ing in ingredients:
                    c.execute(
                        'INSERT INTO Ingredient (fdc_id, ingredient) VALUES (?, ?)', (meal_fdc_id, ing))

                # Insert FoodLogEntry
                c.execute('INSERT INTO FoodLogEntry (daily_log_id, fdc_id, time, notes) VALUES (?, ?, ?, ?)',
                          (daily_log_id, meal_fdc_id, time, meal_notes))
            else:
                # Generate meal_id
                c.execute(
                    'SELECT MAX(meal_id) FROM FoodLogEntry WHERE meal_id IS NOT NULL')
                max_meal_id = c.fetchone()[0]
                meal_id = (max_meal_id + 1) if max_meal_id is not None else 1
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

            symptom_date = logged_time.date()
            symptom_time = logged_time.strftime('%H:%M')

            # Get or create DailyLog
            c.execute(
                'INSERT OR IGNORE INTO DailyLog (user_id, date) VALUES (?, ?)', (user_id, symptom_date))
            c.execute(
                'SELECT id FROM DailyLog WHERE user_id = ? AND date = ?', (user_id, symptom_date))
            daily_log_id = c.fetchone()[0]

            c.execute('INSERT INTO SymptomLogEntry (daily_log_id, symptom_id, time, severity, notes) VALUES (?, ?, ?, ?, ?)',
                      (daily_log_id, symptom_id, symptom_time, severity, notes))
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
        SELECT dl.date || ' ' || sle.time as date_logged FROM SymptomLogEntry sle
        JOIN DailyLog dl ON sle.daily_log_id = dl.id
        WHERE dl.user_id = ? AND sle.symptom_id = ?
        ORDER BY dl.date, sle.time
    ''', conn, params=(user_id, symptom_id))

    for _, sym_row in symptom_logs.iterrows():
        sym_time = datetime.fromisoformat(sym_row['date_logged'])

        # Get meals eaten in the 24 hours before symptom
        start_time = sym_time - timedelta(hours=24)
        meal_ids = pd.read_sql_query('''
            SELECT DISTINCT fle.meal_id FROM FoodLogEntry fle
            JOIN DailyLog dl ON fle.daily_log_id = dl.id
            WHERE dl.user_id = ? AND (dl.date || ' ' || fle.time) BETWEEN ? AND ?
        ''', conn, params=(user_id, start_time.isoformat(), sym_time.isoformat()))

        for _, meal_row in meal_ids.iterrows():
            meal_id = meal_row['meal_id']
            # Get all foods in this meal
            food_logs = pd.read_sql_query('''
                SELECT fdc_id FROM FoodLogEntry WHERE daily_log_id IN (SELECT id FROM DailyLog WHERE user_id = ?) AND meal_id = ?
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

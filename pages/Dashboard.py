import dash
from dash import html, dcc, Input, Output, State, callback, ALL
import sqlite3
import pandas as pd
from datetime import datetime, date
import calendar
from backend.settings import DB_PATH
from backend.utils import get_db_connection

dash.register_page(__name__, path='/dashboard', order=1)


layout = html.Div([
    html.Div([
        html.H3("Calendar"),
        html.Div(id='calendar-view')
    ]),

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


@callback(
    Output('user-info', 'children'),
    Input('current-user-id', 'data')
)
@callback(
    Output('calendar-view', 'children'),
    Input('current-user-id', 'data'),
    Input('calendar-refresh', 'data'),
)
def calendar_view(user_id, refresh_trigger):
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
        })

    # Generate calendar
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


@callback(
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
                    foods_df = pd.read_sql_query('''
                        SELECT f.description, fle.time, fle.notes
                        FROM FoodLogEntry fle
                        JOIN Food f ON fle.fdc_id = f.fdc_id
                        WHERE fle.meal_id = ?
                        ORDER BY fle.time
                    ''', conn, params=(entry_id,))
                    if not foods_df.empty:
                        ingredients_list = [html.Li(
                            f"{row['description']} - {row['time']}") for _, row in foods_df.iterrows()]

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


@callback(
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
        return dash.no_update, dash.no_update

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

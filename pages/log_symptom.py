import dash
from dash import html, dcc, Input, Output, State
from dash import callback
import psycopg2
from datetime import datetime
from backend.utils import get_db_connection


@callback(
    Output('symptom-dropdown', 'options'),
    Input('symptom-dropdown', 'search_value'),
    prevent_initial_call=True
)
def update_symptom_options(search_value):
    conn = get_db_connection()
    with conn.cursor() as cur:
        if search_value:
            cur.execute(
                'SELECT name FROM "symptom" WHERE name ILIKE %s ORDER BY name', (f'%{search_value}%',))
        else:
            cur.execute('SELECT name FROM "symptom" ORDER BY name')
        symptoms = cur.fetchall()
    conn.close()
    return [{"label": s[0], "value": s[0]} for s in symptoms]


dash.register_page(__name__, path='/log-symptom', order=3)


layout = html.Div([
    html.Div([
        html.H2("Log Symptom"),
        html.Label("Symptom:"),
        dcc.Dropdown(id='symptom-dropdown',
                     placeholder='Select or search symptom...', options=[], searchable=True),
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
])


@callback(
    Output('symptom-status', 'children'),
    Input('save-symptom-btn', 'n_clicks'),
    State('symptom-dropdown', 'value'),
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
            conn = get_db_connection()
            with conn.cursor() as cur:
                cur.execute(
                    'INSERT INTO "symptom" (name) VALUES (%s) ON CONFLICT (name) DO NOTHING', (symptom_name,))
                cur.execute(
                    'SELECT id FROM "symptom" WHERE name = %s', (symptom_name,))
                symptom_id = cur.fetchone()[0]

                # Ensure date string always includes a year to avoid DeprecationWarning
                try:
                    if not date or len(date.split('-')) != 3:
                        raise ValueError('Date missing or malformed')
                    datetime_str = f"{date} {time}"
                    logged_time = datetime.strptime(
                        datetime_str, '%Y-%m-%d %H:%M')
                except Exception:
                    logged_time = datetime.now()

                symptom_date = logged_time.date()
                symptom_time = logged_time.strftime('%H:%M')

                cur.execute(
                    'INSERT INTO "dailylog" (user_id, date) VALUES (%s, %s) ON CONFLICT (user_id, date) DO NOTHING', (user_id, symptom_date))
                cur.execute(
                    'SELECT id FROM "dailylog" WHERE user_id = %s AND date = %s', (user_id, symptom_date))
                daily_log_id = cur.fetchone()[0]

                cur.execute('INSERT INTO "symptomlogentry" (daily_log_id, symptom_id, time, severity, notes) VALUES (%s, %s, %s, %s, %s)',
                            (daily_log_id, symptom_id, symptom_time, severity, notes))
                conn.commit()
            conn.close()
            return f"Symptom '{symptom_name}' logged!"
        except psycopg2.Error as e:
            return f"Database error: {e}"
    return ""

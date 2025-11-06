import dash
from dash import html, dcc, Input, Output, State, callback
import sqlite3
from datetime import datetime
from backend.utils import get_db_connection

dash.register_page(__name__, path='/log-symptom', order=3)


layout = html.Div([
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
])


@callback(
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
            conn = get_db_connection()
            c = conn.cursor()
            c.execute(
                'INSERT OR IGNORE INTO Symptom (name) VALUES (?)', (symptom_name,))
            symptom_id = c.execute(
                'SELECT id FROM Symptom WHERE name = ?', (symptom_name,)).fetchone()[0]

            try:
                datetime_str = f"{date} {time}"
                logged_time = datetime.strptime(datetime_str, '%Y-%m-%d %H:%M')
            except:
                logged_time = datetime.now()

            symptom_date = logged_time.date()
            symptom_time = logged_time.strftime('%H:%M')

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

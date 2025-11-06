import dash
from dash import html, dcc, Input, Output, State, callback
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import plotly.graph_objects as go
from backend.settings import DB_PATH
from backend.utils import get_db_connection

dash.register_page(__name__, path='/analysis', order=4)


layout = html.Div([
    html.Div([
        html.H2("Correlation Analysis"),
        html.Label("Select Symptom:"),
        dcc.Dropdown(id='analysis-symptom',
                     placeholder='Choose symptom to analyze...'),
        html.Button('Analyze', id='analyze-btn', n_clicks=0),
        html.Div(id='analysis-results')
    ])
])


@callback(
    Output('analysis-symptom', 'options'),
    Input('analyze-btn', 'n_clicks')
)
def populate_analysis_symptoms(_):
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT name FROM Symptom ORDER BY name", conn)
    conn.close()
    options = [{'label': sym, 'value': sym} for sym in df['name'].tolist()]
    return options


@callback(
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

    conn = sqlite3.connect(DB_PATH)
    symptom_id = conn.execute(
        'SELECT id FROM Symptom WHERE name = ?', (symptom_name,)).fetchone()
    if not symptom_id:
        return "Symptom not found"
    symptom_id = symptom_id[0]

    correlations = {}

    symptom_logs = pd.read_sql_query('''
        SELECT dl.date || ' ' || sle.time as date_logged FROM SymptomLogEntry sle
        JOIN DailyLog dl ON sle.daily_log_id = dl.id
        WHERE dl.user_id = ? AND sle.symptom_id = ?
        ORDER BY dl.date, sle.time
    ''', conn, params=(user_id, symptom_id))

    for _, sym_row in symptom_logs.iterrows():
        sym_time = datetime.fromisoformat(sym_row['date_logged'])

        start_time = sym_time - timedelta(hours=24)
        meal_ids = pd.read_sql_query('''
            SELECT DISTINCT fle.meal_id FROM FoodLogEntry fle
            JOIN DailyLog dl ON fle.daily_log_id = dl.id
            WHERE dl.user_id = ? AND (dl.date || ' ' || fle.time) BETWEEN ? AND ?
        ''', conn, params=(user_id, start_time.isoformat(), sym_time.isoformat()))

        for _, meal_row in meal_ids.iterrows():
            meal_id = meal_row['meal_id']
            food_logs = pd.read_sql_query('''
                SELECT fdc_id FROM FoodLogEntry WHERE daily_log_id IN (SELECT id FROM DailyLog WHERE user_id = ?) AND meal_id = ?
            ''', conn, params=(user_id, meal_id))
            for _, food_row in food_logs.iterrows():
                fdc_id = food_row['fdc_id']
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

    sorted_correlations = sorted(
        correlations.items(), key=lambda x: x[1], reverse=True)

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

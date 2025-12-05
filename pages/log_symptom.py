import dash
from dash import html, dcc, Input, Output, State
from dash import callback
import psycopg2
from datetime import datetime
from backend.utils import get_db_connection


@callback(
    Output('symptom-dropdown', 'options'),
    Input('symptom-dropdown', 'search_value'),
    State('symptom-dropdown', 'value'),
    prevent_initial_call=True
)
def update_symptom_options(search_value, current_value):
    conn = get_db_connection()
    with conn.cursor() as cur:
        if search_value:
            cur.execute(
                'SELECT name FROM "symptom" WHERE name ILIKE %s ORDER BY name', (f'%{search_value}%',))
        else:
            cur.execute('SELECT name FROM "symptom" ORDER BY name LIMIT 50')
        symptoms = cur.fetchall()
    conn.close()
    
    options = [{"label": s[0], "value": s[0]} for s in symptoms]
    
    # If search_value exists and doesn't match any existing symptom exactly, add it as an option
    if search_value and search_value.strip():
        search_title = search_value.strip().title()
        if not any(opt['value'].lower() == search_title.lower() for opt in options):
            options.insert(0, {"label": f"➕ Add new: {search_title}", "value": search_title})
    
    # If there's a current value, make sure it's in the options
    if current_value and not any(opt['value'] == current_value for opt in options):
        options.append({"label": current_value, "value": current_value})
    
    return options


@callback(
    Output('symptom-info', 'children'),
    Input('symptom-dropdown', 'value'),
    prevent_initial_call=True
)
def show_symptom_info(symptom_value):
    if not symptom_value:
        return ""
    
    # Check if symptom exists in database
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute('SELECT name FROM "symptom" WHERE name = %s', (symptom_value,))
            exists = cur.fetchone() is not None
        conn.close()
        
        if exists:
            return "✓ Existing symptom"
        else:
            return f"➕ This will be added as a new symptom: {symptom_value}"
    except:
        return ""


dash.register_page(__name__, path='/log-symptom', order=3)


layout = html.Div([
    html.Div([
        html.Div([
            html.H3("Symptom Information"),
            html.Label("What symptom are you experiencing?"),
            dcc.Dropdown(id='symptom-dropdown',
                         placeholder='Select or type a new symptom...', 
                         options=[], 
                         searchable=True,
                         clearable=True),
            html.Div(id='symptom-info', style={'fontSize': '12px', 'color': '#666', 'marginTop': '4px'}),
        ], style={'marginBottom': '24px', 'padding': '24px', 'backgroundColor': 'white', 'borderRadius': '8px', 'boxShadow': '0 2px 4px rgba(0,0,0,0.1)'}),
        
        html.Div([
            html.H3("Severity Level"),
            html.Label("How severe is this symptom?"),
        dcc.RadioItems(
            id='symptom-severity',
            options=[
                {'label': html.Div([
                    html.Div('', style={'fontSize': '32px', 'height': '40px', 'marginBottom': '4px'}),
                    html.Div('1', style={'fontSize': '14px', 'fontWeight': 'bold', 'marginTop': '4px'})
                ], style={'textAlign': 'center', 'display': 'flex', 'flexDirection': 'column', 'alignItems': 'center'}), 'value': 1},
                {'label': html.Div([
                    html.Div('🙁', style={'fontSize': '32px', 'height': '40px', 'lineHeight': '40px', 'marginBottom': '4px'}),
                    html.Div('2', style={'fontSize': '14px', 'fontWeight': 'bold', 'marginTop': '4px'})
                ], style={'textAlign': 'center', 'display': 'flex', 'flexDirection': 'column', 'alignItems': 'center'}), 'value': 2},
                {'label': html.Div([
                    html.Div('', style={'fontSize': '32px', 'height': '40px', 'marginBottom': '4px'}),
                    html.Div('3', style={'fontSize': '14px', 'fontWeight': 'bold', 'marginTop': '4px'})
                ], style={'textAlign': 'center', 'display': 'flex', 'flexDirection': 'column', 'alignItems': 'center'}), 'value': 3},
                {'label': html.Div([
                    html.Div('😕', style={'fontSize': '32px', 'height': '40px', 'lineHeight': '40px', 'marginBottom': '4px'}),
                    html.Div('4', style={'fontSize': '14px', 'fontWeight': 'bold', 'marginTop': '4px'})
                ], style={'textAlign': 'center', 'display': 'flex', 'flexDirection': 'column', 'alignItems': 'center'}), 'value': 4},
                {'label': html.Div([
                    html.Div('', style={'fontSize': '32px', 'height': '40px', 'marginBottom': '4px'}),
                    html.Div('5', style={'fontSize': '14px', 'fontWeight': 'bold', 'marginTop': '4px'})
                ], style={'textAlign': 'center', 'display': 'flex', 'flexDirection': 'column', 'alignItems': 'center'}), 'value': 5},
                {'label': html.Div([
                    html.Div('😟', style={'fontSize': '32px', 'height': '40px', 'lineHeight': '40px', 'marginBottom': '4px'}),
                    html.Div('6', style={'fontSize': '14px', 'fontWeight': 'bold', 'marginTop': '4px'})
                ], style={'textAlign': 'center', 'display': 'flex', 'flexDirection': 'column', 'alignItems': 'center'}), 'value': 6},
                {'label': html.Div([
                    html.Div('', style={'fontSize': '32px', 'height': '40px', 'marginBottom': '4px'}),
                    html.Div('7', style={'fontSize': '14px', 'fontWeight': 'bold', 'marginTop': '4px'})
                ], style={'textAlign': 'center', 'display': 'flex', 'flexDirection': 'column', 'alignItems': 'center'}), 'value': 7},
                {'label': html.Div([
                    html.Div('😣', style={'fontSize': '32px', 'height': '40px', 'lineHeight': '40px', 'marginBottom': '4px'}),
                    html.Div('8', style={'fontSize': '14px', 'fontWeight': 'bold', 'marginTop': '4px'})
                ], style={'textAlign': 'center', 'display': 'flex', 'flexDirection': 'column', 'alignItems': 'center'}), 'value': 8},
                {'label': html.Div([
                    html.Div('', style={'fontSize': '32px', 'height': '40px', 'marginBottom': '4px'}),
                    html.Div('9', style={'fontSize': '14px', 'fontWeight': 'bold', 'marginTop': '4px'})
                ], style={'textAlign': 'center', 'display': 'flex', 'flexDirection': 'column', 'alignItems': 'center'}), 'value': 9},
                {'label': html.Div([
                    html.Div('😫', style={'fontSize': '32px', 'height': '40px', 'lineHeight': '40px', 'marginBottom': '4px'}),
                    html.Div('10', style={'fontSize': '14px', 'fontWeight': 'bold', 'marginTop': '4px'})
                ], style={'textAlign': 'center', 'display': 'flex', 'flexDirection': 'column', 'alignItems': 'center'}), 'value': 10}
            ],
            value=6,
            inline=True,
            labelStyle={'display': 'inline-flex', 'flexDirection': 'column', 'alignItems': 'center', 'margin': '0 8px', 'cursor': 'pointer'},
            inputStyle={'margin': '4px 0'},
            style={'textAlign': 'center', 'margin': '16px 0'}
        ), ], style={'marginBottom': '24px', 'padding': '24px', 'backgroundColor': 'white', 'borderRadius': '8px', 'boxShadow': '0 2px 4px rgba(0,0,0,0.1)'}),
        
        html.Div([
            html.H3("Symptom Details"),
            dcc.Checklist(
                id='date-range-toggle',
                options=[{'label': ' Symptom lasted multiple days', 'value': 'range'}],
                value=[],
                style={'marginBottom': '12px'}
            ),
            html.Div([
                html.Div([
                    html.Label("Start Date:"),
                    dcc.DatePickerSingle(
                        id='symptom-date', date=datetime.now().date()),
                ], style={'display': 'inline-block', 'marginRight': '16px'}),
                html.Div([
                    html.Label("End Date:"),
                    dcc.DatePickerSingle(
                        id='symptom-end-date', date=datetime.now().date()),
                ], id='end-date-container', style={'display': 'none', 'marginRight': '16px'}),
                html.Div([
                    html.Label("Time:"),
                    dcc.Input(id='symptom-time', type='text', placeholder='HH:MM',
                              value=datetime.now().strftime('%H:%M'), style={'width': '120px'}),
                ], id='time-container', style={'display': 'inline-block', 'verticalAlign': 'top'}),
            ]),
            html.Label("Notes (Optional):", style={'marginTop': '16px', 'fontSize': '14px', 'fontWeight': '500'}),
            dcc.Textarea(id='symptom-notes',
                         placeholder='Add any additional details about this symptom...', 
                         style={'minHeight': '100px'}),
        ], style={'marginBottom': '24px', 'padding': '24px', 'backgroundColor': 'white', 'borderRadius': '8px', 'boxShadow': '0 2px 4px rgba(0,0,0,0.1)'}),
        
        html.Button('Save Symptom', id='save-symptom-btn', n_clicks=0, 
                   style={'width': '100%', 'padding': '12px', 'fontSize': '16px'}),
        html.Div(id='symptom-status', style={'marginTop': '16px', 'textAlign': 'center', 'fontWeight': 'bold'})
    ], style={'maxWidth': '1000px', 'margin': '0 auto', 'padding': '24px'})
])


@callback(
    Output('end-date-container', 'style'),
    Output('time-container', 'style'),
    Input('date-range-toggle', 'value')
)
def toggle_date_range(toggle_value):
    if 'range' in toggle_value:
        # Show end date, hide time
        return {'display': 'inline-block', 'marginRight': '16px'}, {'display': 'none'}
    else:
        # Hide end date, show time
        return {'display': 'none'}, {'display': 'inline-block', 'verticalAlign': 'top'}


@callback(
    Output('symptom-status', 'children'),
    Input('save-symptom-btn', 'n_clicks'),
    State('symptom-dropdown', 'value'),
    State('symptom-severity', 'value'),
    State('symptom-date', 'date'),
    State('symptom-end-date', 'date'),
    State('symptom-time', 'value'),
    State('symptom-notes', 'value'),
    State('date-range-toggle', 'value'),
    State('current-user-id', 'data')
)
def save_symptom(n_clicks, symptom_name, severity, start_date, end_date, time, notes, date_range_toggle, user_id):
    if not user_id:
        return "Please log in to log symptoms."
    if n_clicks > 0 and symptom_name:
        try:
            # Convert symptom name to Title Case
            symptom_name = symptom_name.strip().title()
            
            conn = get_db_connection()
            with conn.cursor() as cur:
                cur.execute(
                    'INSERT INTO "symptom" (name) VALUES (%s) ON CONFLICT (name) DO NOTHING', (symptom_name,))
                cur.execute(
                    'SELECT id FROM "symptom" WHERE name = %s', (symptom_name,))
                symptom_id = cur.fetchone()[0]

                # Check if date range is enabled
                is_date_range = 'range' in date_range_toggle
                
                if is_date_range and end_date:
                    # Handle date range - create entry for each day
                    try:
                        from datetime import timedelta
                        start = datetime.strptime(start_date, '%Y-%m-%d').date()
                        end = datetime.strptime(end_date, '%Y-%m-%d').date()
                        
                        if end < start:
                            return "⚠️ End date must be after start date."
                        
                        current_date = start
                        entries_created = 0
                        
                        while current_date <= end:
                            cur.execute(
                                'INSERT INTO "dailylog" (user_id, date) VALUES (%s, %s) ON CONFLICT (user_id, date) DO NOTHING', 
                                (user_id, current_date))
                            cur.execute(
                                'SELECT id FROM "dailylog" WHERE user_id = %s AND date = %s', 
                                (user_id, current_date))
                            daily_log_id = cur.fetchone()[0]
                            
                            # Use 00:00 for date range entries
                            cur.execute(
                                'INSERT INTO "symptomlogentry" (daily_log_id, symptom_id, time, severity, notes) VALUES (%s, %s, %s, %s, %s)',
                                (daily_log_id, symptom_id, '00:00', severity, notes))
                            
                            entries_created += 1
                            current_date += timedelta(days=1)
                        
                        conn.commit()
                        days_text = "day" if entries_created == 1 else "days"
                        return f"✓ Symptom '{symptom_name}' logged for {entries_created} {days_text}!"
                        
                    except Exception as e:
                        return f"⚠️ Error processing date range: {e}"
                else:
                    # Single date entry with specific time
                    try:
                        if not start_date or len(start_date.split('-')) != 3:
                            raise ValueError('Date missing or malformed')
                        datetime_str = f"{start_date} {time}"
                        logged_time = datetime.strptime(
                            datetime_str, '%Y-%m-%d %H:%M')
                    except Exception:
                        logged_time = datetime.now()

                    symptom_date = logged_time.date()
                    symptom_time = logged_time.strftime('%H:%M')

                    cur.execute(
                        'INSERT INTO "dailylog" (user_id, date) VALUES (%s, %s) ON CONFLICT (user_id, date) DO NOTHING', 
                        (user_id, symptom_date))
                    cur.execute(
                        'SELECT id FROM "dailylog" WHERE user_id = %s AND date = %s', 
                        (user_id, symptom_date))
                    daily_log_id = cur.fetchone()[0]

                    cur.execute(
                        'INSERT INTO "symptomlogentry" (daily_log_id, symptom_id, time, severity, notes) VALUES (%s, %s, %s, %s, %s)',
                        (daily_log_id, symptom_id, symptom_time, severity, notes))
                    conn.commit()
                    return f"✓ Symptom '{symptom_name}' logged!"
                    
            conn.close()
        except psycopg2.Error as e:
            return f"⚠️ Database error: {e}"
    return ""

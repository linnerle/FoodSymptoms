import dash
from dash import html, dcc, Input, Output, State, callback
from backend.utils import get_db_connection

dash.register_page(__name__, path='/settings', order=5)


layout = html.Div([
    dcc.Location(id='logout-redirect', refresh=True),
    
    html.Div([
        dcc.Loading(
            id='loading-settings',
            type='circle',
            color='#1976d2',
            children=html.Div([
                html.Div([
                    html.H2("User Settings", style={'color': '#1976d2', 'marginBottom': '24px', 'textAlign': 'center'}),
                    
                    html.Div([
                        html.Label("Username:", style={'fontWeight': '500', 'marginBottom': '4px', 'display': 'block'}),
                        dcc.Input(id='username-input', type='text',
                                  placeholder='Enter username',
                                  style={'width': '100%', 'padding': '10px', 'marginBottom': '16px', 'border': '1px solid #e0e0e0', 'borderRadius': '4px', 'fontSize': '14px'}),
                        
                        html.Label("Email:", style={'fontWeight': '500', 'marginBottom': '4px', 'display': 'block'}),
                        dcc.Input(id='email-input', type='email',
                                  placeholder='Enter email',
                                  style={'width': '100%', 'padding': '10px', 'marginBottom': '16px', 'border': '1px solid #e0e0e0', 'borderRadius': '4px', 'fontSize': '14px'}),
                        
                        html.Label("Password:", style={'fontWeight': '500', 'marginBottom': '4px', 'display': 'block'}),
                        dcc.Input(id='password-input', type='password',
                                  placeholder='Enter new password (leave blank to keep current)',
                                  style={'width': '100%', 'padding': '10px', 'marginBottom': '20px', 'border': '1px solid #e0e0e0', 'borderRadius': '4px', 'fontSize': '14px'}),
                        
                        html.Button('Save Settings',
                                    id='save-settings-btn', n_clicks=0,
                                    style={'width': '100%', 'padding': '12px', 'backgroundColor': '#1976d2', 'color': 'white', 'border': 'none', 'borderRadius': '4px', 'cursor': 'pointer', 'fontSize': '16px', 'fontWeight': '500', 'marginBottom': '12px'}),
                        
                        html.Div(id='settings-status', style={'textAlign': 'center', 'marginBottom': '20px', 'color': '#4caf50', 'fontWeight': '500'})
                    ]),
                    
                    html.Hr(style={'margin': '24px 0', 'border': 'none', 'borderTop': '1px solid #e0e0e0'}),
                    
                    html.Div([
                        html.Button('Logout', id='logout-btn', n_clicks=0,
                                    style={'width': '100%', 'padding': '12px', 'backgroundColor': '#ef5350', 'color': 'white', 'border': 'none', 'borderRadius': '4px', 'cursor': 'pointer', 'fontSize': '16px', 'fontWeight': '500'})
                    ])
                    
                ], style={'backgroundColor': 'white', 'borderRadius': '8px', 'boxShadow': '0 2px 4px rgba(0,0,0,0.1)', 'padding': '32px', 'maxWidth': '500px', 'margin': '0 auto'})
            ])
        )
    ], style={'maxWidth': '1000px', 'margin': '0 auto', 'padding': '40px 24px'})
])


@callback(
    Output('username-input', 'value'),
    Output('email-input', 'value'),
    Input('current-user-id', 'data')
)
def load_user_settings(user_id):
    if not user_id:
        return "", ""
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute('SELECT username, email FROM "user" WHERE id = %s', (user_id,))
        user = cur.fetchone()
    conn.close()
    if user:
        return user[0], user[1]
    return "", ""


@callback(
    Output('settings-status', 'children'),
    Input('save-settings-btn', 'n_clicks'),
    State('username-input', 'value'),
    State('email-input', 'value'),
    State('password-input', 'value'),
    State('current-user-id', 'data'),
    prevent_initial_call=True
)
def save_user_settings(n_clicks, username, email, password, user_id):
    if not user_id:
        return "Please log in to save settings."
    if n_clicks > 0 and username:
        conn = get_db_connection()
        with conn.cursor() as cur:
            # Update user with or without password
            if password and password.strip():
                # Update with new password
                cur.execute('UPDATE "user" SET username = %s, email = %s, password = %s WHERE id = %s',
                          (username, email, password, user_id))
            else:
                # Update without changing password
                cur.execute('UPDATE "user" SET username = %s, email = %s WHERE id = %s',
                          (username, email, user_id))
            conn.commit()
        conn.close()
        return "✓ Settings saved!"
    return ""


@callback(
    Output('login-status', 'data', allow_duplicate=True),
    Output('current-user-id', 'data', allow_duplicate=True),
    Output('logout-redirect', 'href'),
    Input('logout-btn', 'n_clicks'),
    State('current-user-id', 'data'),
    prevent_initial_call=True
)
def logout(n_clicks, user_id):
    if n_clicks > 0:
        # Clear the cache for this user
        if user_id:
            from backend.cache import invalidate_user_cache
            invalidate_user_cache(user_id)
        return False, None, '/'
    return dash.no_update, dash.no_update, dash.no_update

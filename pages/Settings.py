import dash
from dash import html, dcc, Input, Output, State, callback
import sqlite3
from backend.settings import DB_PATH
from backend.utils import get_db_connection

dash.register_page(__name__, path='/settings', order=5)


layout = html.Div([
    dcc.Location(id='logout-redirect', refresh=True),

    html.Div([
        html.H2("User Settings"),
        html.Label("Username:"),
        dcc.Input(id='username-input', type='text',
                  placeholder='Enter username'),
        html.Label("Email:"),
        dcc.Input(id='email-input', type='email',
                  placeholder='Enter email'),
        html.Label("Password:"),
        dcc.Input(id='password-input', type='password',
                  placeholder='Enter new password (leave blank to keep current)'),
        html.Button('Save Settings',
                    id='save-settings-btn', n_clicks=0),
        html.Div(id='settings-status'),
        html.Hr(),
        html.Button('Logout', id='logout-btn', n_clicks=0,
                    style={'backgroundColor': 'red', 'color': 'white'})
    ])
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
    user = conn.execute(
        'SELECT username, email FROM User WHERE id = ?', (user_id,)).fetchone()
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
        c = conn.cursor()

        # Update user with or without password
        if password and password.strip():
            # Update with new password
            c.execute('UPDATE User SET username = ?, email = ?, password = ? WHERE id = ?',
                      (username, email, password, user_id))
        else:
            # Update without changing password
            c.execute('UPDATE User SET username = ?, email = ? WHERE id = ?',
                      (username, email, user_id))

        conn.commit()
        conn.close()
        return "Settings saved!"
    return ""


@callback(
    Output('login-status', 'data', allow_duplicate=True),
    Output('current-user-id', 'data', allow_duplicate=True),
    Output('logout-redirect', 'href'),
    Input('logout-btn', 'n_clicks'),
    prevent_initial_call=True
)
def logout(n_clicks):
    if n_clicks > 0:
        return False, None, '/'
    return dash.no_update, dash.no_update, dash.no_update

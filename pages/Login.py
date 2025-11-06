import dash
from dash import html, dcc, Input, Output, State, callback
import sqlite3
from backend.utils import get_db_connection

dash.register_page(__name__, path='/', order=0)


layout = html.Div([
    html.H1("MealMap - Login"),
    dcc.Location(id='login-redirect', refresh=True),
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


@callback(
    Output('login-status', 'data'),
    Output('current-user-id', 'data'),
    Output('login-message', 'children'),
    Output('login-redirect', 'href'),
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
                'SELECT id FROM User WHERE username = ? AND password = ?',
                (username, password)
            ).fetchone()
            conn.close()
            if user:
                return True, user[0], "Login successful! Redirecting...", "/dashboard"
            else:
                return False, None, "Invalid username or password", dash.no_update
        except sqlite3.OperationalError as e:
            if "locked" in str(e).lower():
                return False, None, "Database is busy. Please try again.", dash.no_update
            else:
                return False, None, f"Database error: {e}", dash.no_update
    return False, None, "", dash.no_update


@callback(
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

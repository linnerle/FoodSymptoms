import dash
from dash import html, dcc, Input, Output, State, callback
import psycopg2
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
            with conn.cursor() as cur:
                cur.execute(
                    'SELECT id FROM "user" WHERE username = %s AND password = %s', (username, password))
                user = cur.fetchone()
            conn.close()
            if user:
                return True, user[0], "Login successful! Redirecting...", "/dashboard"
            else:
                return False, None, "Invalid username or password", dash.no_update
        except psycopg2.Error as e:
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
            with conn.cursor() as cur:
                cur.execute('INSERT INTO "user" (username, email, password) VALUES (%s, %s, %s)',
                            (username, email, password))
                conn.commit()
            conn.close()
            return "Account created successfully! Please login."
        except psycopg2.IntegrityError:
            return "Username already exists"
        except psycopg2.Error as e:
            return f"Database error: {e}"
    return ""

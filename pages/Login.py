import dash
from dash import html, dcc, Input, Output, State, callback
import psycopg2
from backend.utils import get_db_connection

dash.register_page(__name__, path='/', order=0)


layout = html.Div([
    dcc.Location(id='login-redirect', refresh=True),
    html.Div([
        html.Div([
            html.H1("MealMap", style={'textAlign': 'center', 'color': '#1976d2', 'marginBottom': '32px'}),
            dcc.Tabs(id='auth-tabs', value='login', children=[
                dcc.Tab(label='Login', value='login', children=[
                    html.Div([
                        html.Label("Username", style={'display': 'block', 'marginBottom': '8px', 'fontWeight': 'bold', 'color': '#333'}),
                        dcc.Input(id='login-username', type='text', placeholder='Enter username',
                                  style={'width': '100%', 'padding': '10px', 'marginBottom': '16px', 
                                         'border': '1px solid #e0e0e0', 'borderRadius': '4px', 'boxSizing': 'border-box'}),
                        html.Label("Password", style={'display': 'block', 'marginBottom': '8px', 'fontWeight': 'bold', 'color': '#333'}),
                        dcc.Input(id='login-password', type='password', placeholder='Enter password',
                                  style={'width': '100%', 'padding': '10px', 'marginBottom': '24px', 
                                         'border': '1px solid #e0e0e0', 'borderRadius': '4px', 'boxSizing': 'border-box'}),
                        html.Button('Login', id='login-btn', n_clicks=0,
                                    style={'width': '100%', 'padding': '12px', 'backgroundColor': '#1976d2', 
                                           'color': 'white', 'border': 'none', 'borderRadius': '4px', 
                                           'cursor': 'pointer', 'fontWeight': 'bold', 'fontSize': '16px'}),
                        dcc.Loading(
                            id='loading-login',
                            type='circle',
                            color='#1976d2',
                            children=html.Div(id='login-message', style={'marginTop': '16px', 'textAlign': 'center', 'color': '#666'})
                        )
                    ], style={'padding': '24px 0'})
                ]),
                dcc.Tab(label='Sign Up', value='signup', children=[
                    html.Div([
                        html.Label("Username", style={'display': 'block', 'marginBottom': '8px', 'fontWeight': 'bold', 'color': '#333'}),
                        dcc.Input(id='signup-username', type='text', placeholder='Choose username',
                                  style={'width': '100%', 'padding': '10px', 'marginBottom': '16px', 
                                         'border': '1px solid #e0e0e0', 'borderRadius': '4px', 'boxSizing': 'border-box'}),
                        html.Label("Email", style={'display': 'block', 'marginBottom': '8px', 'fontWeight': 'bold', 'color': '#333'}),
                        dcc.Input(id='signup-email', type='email', placeholder='Enter email',
                                  style={'width': '100%', 'padding': '10px', 'marginBottom': '16px', 
                                         'border': '1px solid #e0e0e0', 'borderRadius': '4px', 'boxSizing': 'border-box'}),
                        html.Label("Password", style={'display': 'block', 'marginBottom': '8px', 'fontWeight': 'bold', 'color': '#333'}),
                        dcc.Input(id='signup-password', type='password', placeholder='Choose password',
                                  style={'width': '100%', 'padding': '10px', 'marginBottom': '24px', 
                                         'border': '1px solid #e0e0e0', 'borderRadius': '4px', 'boxSizing': 'border-box'}),
                        html.Button('Sign Up', id='signup-btn', n_clicks=0,
                                    style={'width': '100%', 'padding': '12px', 'backgroundColor': '#1976d2', 
                                           'color': 'white', 'border': 'none', 'borderRadius': '4px', 
                                           'cursor': 'pointer', 'fontWeight': 'bold', 'fontSize': '16px'}),
                        dcc.Loading(
                            id='loading-signup',
                            type='circle',
                            color='#1976d2',
                            children=html.Div(id='signup-status', style={'marginTop': '16px', 'textAlign': 'center', 'color': '#666'})
                        )
                    ], style={'padding': '24px 0'})
                ])
            ])
        ], style={'maxWidth': '400px', 'margin': '0 auto', 'padding': '32px', 
                  'backgroundColor': 'white', 'borderRadius': '8px', 
                  'boxShadow': '0 2px 8px rgba(0,0,0,0.1)'})
    ], style={'display': 'flex', 'justifyContent': 'center', 'alignItems': 'center', 
              'minHeight': '100vh', 'backgroundColor': '#f5f5f5'})
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
                user_id = user[0]
                # Pre-load user data into cache for fast subsequent access
                from backend.cache import get_user_data
                try:
                    get_user_data(user_id, force_refresh=True)
                except Exception as e:
                    print(f"Cache pre-load warning: {e}")
                return True, user_id, "Login successful! Redirecting...", "/dashboard"
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

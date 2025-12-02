import dash
from dash import Dash, html, dcc, Input, Output, State, callback
from argparse import ArgumentParser

# Initialize the Dash app with multi-page support
app = Dash(
    __name__,
    use_pages=True,
    suppress_callback_exceptions=True
)

# Shared stores for authentication - these need to be in the main layout
app.layout = html.Div([
    dcc.Store(id='login-status', data=False, storage_type='session'),
    dcc.Store(id='current-user-id', data=None, storage_type='session'),
    dcc.Location(id='url', refresh=False),

    # Global header with navigation
    html.Div(id='global-header'),

    html.Div(id='page-content', children=[
        dash.page_container
    ])
])


@callback(
    Output('global-header', 'children'),
    Input('login-status', 'data'),
    Input('url', 'pathname')
)
def update_header(is_logged_in, pathname):
    # Don't show header on login page or if not logged in
    if not is_logged_in or pathname == '/':
        return html.Div()

    # Define navigation items
    nav_items = [
        {'label': 'Dashboard', 'path': '/dashboard'},
        {'label': 'Log Food', 'path': '/log-food'},
        {'label': 'Log Symptom', 'path': '/log-symptom'},
        {'label': 'Analysis', 'path': '/analysis'},
        {'label': 'Settings', 'path': '/settings'}
    ]

    # Create navigation links with active styling
    nav_links = []
    for item in nav_items:
        is_active = pathname == item['path']
        style = {
            'marginRight': '20px' if item['label'] != 'Settings' else '0px',
            'textDecoration': 'underline' if is_active else 'none',
            'color': '#0071ce',
            'fontWeight': 'bold',
            'display': 'inline-block'
        }
        nav_links.append(
            dcc.Link(item['label'], href=item['path'], style=style))

    # Create navigation header
    return html.Div([
        html.Div([
            html.Span("MealMap", style={
                'fontSize': '24px',
                'fontWeight': 'bold',
                'color': '#0071ce',
                'display': 'inline-block',
                'verticalAlign': 'middle'
            }),
            html.Div(nav_links, style={
                'display': 'inline-block',
                'float': 'right',
                'lineHeight': '24px'
            })
        ], style={
            'padding': '20px',
            'backgroundColor': '#f0f0f0',
            'borderBottom': '2px solid #ddd',
            'marginBottom': '20px',
            'overflow': 'hidden'
        })
    ])


if __name__ == "__main__":
    parser = ArgumentParser(
        prog='app.py',
        description='main application'
    )
    parser.add_argument('--hostname', default='0.0.0.0')
    parser.add_argument('--port', default='8080')
    args = parser.parse_args()

    app.run(debug=False, host=args.hostname, port=int(args.port))

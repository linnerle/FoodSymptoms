import dash
from dash import Dash, html, dcc, Input, Output, State, callback

# Initialize the Dash app with multi-page support
app = Dash(
    __name__,
    use_pages=True,
    suppress_callback_exceptions=True
)

# Disable default loading spinner (we'll use dcc.Loading components)
app.config.suppress_callback_exceptions = True

# Shared stores for authentication - these need to be in the main layout
app.layout = html.Div([
    dcc.Store(id='login-status', data=False, storage_type='session'),
    dcc.Store(id='current-user-id', data=None, storage_type='session'),
    dcc.Store(id='add-entry-click-data', data={}, storage_type='session'),
    dcc.Store(id='double-click-trigger', data=0),
    html.Button(id='hidden-doubleclick-btn', n_clicks=0, style={'display': 'none'}),
    dcc.Location(id='url', refresh=False),
    dcc.Location(id='page-navigation', refresh=True),

    # Global header with navigation
    html.Div(id='global-header'),

    html.Div(id='page-content', children=[
        dash.page_container
    ]),
    
    # Global add entry modal
    html.Div(
        id='add-entry-modal',
        style={'display': 'none', 'position': 'fixed', 'zIndex': 1001, 'left': 0, 'top': 0,
               'width': '100%', 'height': '100%', 'backgroundColor': 'rgba(0,0,0,0.4)'},
        children=[
            html.Div(
                style={'backgroundColor': 'white', 'margin': '15% auto', 'padding': '32px',
                       'borderRadius': '8px', 'boxShadow': '0 4px 12px rgba(0,0,0,0.15)',
                       'width': '400px', 'textAlign': 'center'},
                children=[
                    html.H3("What would you like to add?", style={'color': '#1976d2', 'marginBottom': '24px', 'fontSize': '20px'}),
                    html.Div([
                        html.Button('Meal / Food', id='add-meal-btn',
                                   style={'padding': '16px 32px', 'fontSize': '16px', 'backgroundColor': 'white', 
                                          'color': '#64b5f6', 'border': '2px solid #64b5f6', 'borderRadius': '4px', 
                                          'cursor': 'pointer', 'width': '100%', 'marginBottom': '12px', 
                                          'fontWeight': 'normal'}),
                        html.Button('Symptom', id='add-symptom-btn',
                                   style={'padding': '16px 32px', 'fontSize': '16px', 'backgroundColor': 'white', 
                                          'color': '#ef5350', 'border': '2px solid #ef9a9a', 'borderRadius': '4px', 
                                          'cursor': 'pointer', 'width': '100%', 'fontWeight': 'normal'}),
                    ], style={'marginBottom': '20px'}),
                    html.Button('Cancel', id='add-entry-cancel-btn',
                               n_clicks=0, style={'padding': '8px 24px', 'fontSize': '14px', 
                                                 'backgroundColor': '#f5f5f5', 'color': '#666', 
                                                 'border': '1px solid #ccc', 'borderRadius': '4px', 
                                                 'cursor': 'pointer'})
                ]
            )
        ]
    )
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

    # Define navigation items (removed Log Food and Log Symptom - accessed via calendar + button)
    nav_items = [
        {'label': 'Calendar', 'path': '/dashboard'},
        {'label': 'Analysis', 'path': '/analysis'},
        {'label': 'Settings', 'path': '/settings'}
    ]

    # Create navigation links with active styling
    nav_links = []
    for item in nav_items:
        is_active = pathname == item['path']
        style = {
            'marginRight': '20px',
            'textDecoration': 'underline' if is_active else 'none',
            'color': '#0071ce',
            'fontWeight': 'bold',
            'display': 'inline-block'
        }
        nav_links.append(
            dcc.Link(item['label'], href=item['path'], style=style))
    
    # Add the + Add Entry button
    nav_links.append(
        html.Button('+ Add Entry', id='add-entry-btn', n_clicks=0,
                   style={'fontSize': '14px', 'padding': '6px 16px', 'cursor': 'pointer', 
                          'height': '32px', 'border': '1px solid #1976d2', 'borderRadius': '4px', 
                          'backgroundColor': '#1976d2', 'color': 'white', 'fontWeight': 'normal',
                          'verticalAlign': 'middle', 'marginLeft': '4px'})
    )

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


# Clientside callback to capture double-click data from Dashboard
dash.clientside_callback(
    """
    function(n_clicks) {
        if (n_clicks > 0 && window._doubleClickData) {
            return window._doubleClickData;
        }
        return window.dash_clientside.no_update;
    }
    """,
    Output('double-click-trigger', 'data'),
    Input('hidden-doubleclick-btn', 'n_clicks'),
    prevent_initial_call=True
)


@callback(
    Output('add-entry-modal', 'style'),
    Output('add-entry-click-data', 'data'),
    Input('add-entry-btn', 'n_clicks'),
    Input('add-entry-cancel-btn', 'n_clicks'),
    Input('double-click-trigger', 'data'),
    State('add-entry-modal', 'style'),
    prevent_initial_call=True
)
def toggle_add_entry_modal(add_clicks, cancel_clicks, double_click_data, current_style):
    """Open/close the add entry modal"""
    from datetime import datetime, date
    
    ctx = dash.callback_context
    if not ctx.triggered:
        return dash.no_update, dash.no_update
    
    trigger_id = ctx.triggered[0]['prop_id']
    
    if 'add-entry-cancel-btn' in trigger_id:
        return {'display': 'none'}, {}
    
    if 'double-click-trigger' in trigger_id:
        # Only open if we have valid double-click data with date field
        if double_click_data and isinstance(double_click_data, dict) and 'date' in double_click_data:
            print(f"DEBUG: Double-click data received: {double_click_data}")
            return {'display': 'block', 'position': 'fixed', 'zIndex': 1001, 'left': 0, 'top': 0, 'width': '100%', 'height': '100%', 'backgroundColor': 'rgba(0,0,0,0.4)'}, double_click_data
        else:
            return dash.no_update, dash.no_update
    
    if 'add-entry-btn' in trigger_id and add_clicks and add_clicks > 0:
        # Prepare click data with current date/time
        click_data = {
            'date': date.today().isoformat(),
            'time': datetime.now().strftime('%H:%M'),
            'view_mode': 'month'
        }
        return {'display': 'block', 'position': 'fixed', 'zIndex': 1001, 'left': 0, 'top': 0, 'width': '100%', 'height': '100%', 'backgroundColor': 'rgba(0,0,0,0.4)'}, click_data
    
    return dash.no_update, dash.no_update


@callback(
    Output('page-navigation', 'href'),
    Output('add-entry-modal', 'style', allow_duplicate=True),
    Input('add-meal-btn', 'n_clicks'),
    Input('add-symptom-btn', 'n_clicks'),
    State('add-entry-click-data', 'data'),
    prevent_initial_call=True
)
def navigate_to_log_page(meal_clicks, symptom_clicks, click_data):
    """Navigate to log page with date/time as query parameters"""
    from datetime import datetime, date
    
    ctx = dash.callback_context
    if not ctx.triggered:
        return dash.no_update, dash.no_update
    
    trigger_id = ctx.triggered[0]['prop_id']
    
    # Get date and time from click data
    date_val = click_data.get('date', date.today().isoformat()) if click_data else date.today().isoformat()
    time_val = click_data.get('time', datetime.now().strftime('%H:%M')) if click_data else datetime.now().strftime('%H:%M')
    
    print(f"DEBUG navigate: click_data={click_data}, date={date_val}, time={time_val}")
    
    # Close modal and navigate
    modal_style = {'display': 'none'}
    
    if 'add-meal-btn' in trigger_id:
        return f'/log-food?date={date_val}&time={time_val}', modal_style
    elif 'add-symptom-btn' in trigger_id:
        return f'/log-symptom?date={date_val}&time={time_val}', modal_style
    
    return dash.no_update, dash.no_update


if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=8080)

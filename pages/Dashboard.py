import dash
from backend.utils import get_db_connection
import calendar
from datetime import datetime, date, timedelta
import pandas as pd
from dash import html, dcc, Input, Output, State, callback, ALL, MATCH


def get_entry_style(entry_type):
    if entry_type == 'symptom':
        return {
            'backgroundColor': 'white',
            'color': '#ef5350',
            'border': '1px solid #ef9a9a',
            'display': 'block',
            'margin': '2px',
            'padding': '5px',
            'fontSize': '10px',
            'cursor': 'pointer',
            'textAlign': 'left'
        }
    elif entry_type in ['meal', 'food']:
        return {
            'backgroundColor': 'white',
            'color': '#64b5f6',
            'border': '1px solid #64b5f6',
            'display': 'block',
            'margin': '2px',
            'padding': '5px',
            'fontSize': '10px',
            'cursor': 'pointer',
            'textAlign': 'left'
        }
    else:
        return {}


# Callback to update calendar-date based on navigation and view mode


dash.register_page(__name__, path='/dashboard', order=1)


layout = html.Div([
    html.Div([
        html.Button('←', id='calendar-prev-btn', n_clicks=0,
                    style={'fontSize': '14px', 'padding': '6px 12px', 'marginRight': '8px', 'cursor': 'pointer', 'height': '32px', 'border': '1px solid #ccc', 'borderRadius': '4px', 'backgroundColor': 'white', 'alignSelf': 'center'}),
        html.Div(
            dcc.Dropdown(
                id='calendar-view-mode',
                options=[
                    {'label': 'Day', 'value': 'day'},
                    {'label': 'Week', 'value': 'week'},
                    {'label': 'Month', 'value': 'month'}
                ],
                value='month',
                clearable=False,
                style={'width': '100px', 'fontSize': '14px'}
            ),
            style={'height': '32px', 'position': 'relative', 'top': '-3px'}
        ),
        html.Button('→', id='calendar-next-btn', n_clicks=0,
                    style={'fontSize': '14px', 'padding': '6px 12px', 'marginLeft': '8px', 'cursor': 'pointer', 'height': '32px', 'border': '1px solid #ccc', 'borderRadius': '4px', 'backgroundColor': 'white', 'alignSelf': 'center'})
    ], style={'textAlign': 'center', 'margin': '16px 0', 'display': 'flex', 'alignItems': 'center', 'justifyContent': 'center'}),
    html.Div([
        dcc.Loading(
            id='loading-calendar',
            type='circle',
            color='#1976d2',
            children=html.Div(id='calendar-view')
        )
    ]),
    dcc.Store(id='calendar-refresh', data=0),
    dcc.Store(id='calendar-date', data=date.today().isoformat()),
    dcc.Store(id='modal-close-store', data=0),
    dcc.Store(id='previous-view-mode', data='month'),
    dcc.Store(id='scroll-trigger', data=0),
    dcc.Store(id='modal-edit-mode', data=False),
    dcc.Store(id='modal-entry-data', data={}),
    html.Div(
        id='entry-modal',
        style={'display': 'none', 'position': 'fixed', 'zIndex': 1000, 'left': 0, 'top': 0,
               'width': '100%', 'height': '100%', 'backgroundColor': 'rgba(0,0,0,0.4)'},
        children=[
            html.Div(
                style={'backgroundColor': 'white', 'margin': '10% auto', 'padding': '32px',
                       'borderRadius': '8px', 'boxShadow': '0 4px 12px rgba(0,0,0,0.15)',
                       'width': '90%', 'maxWidth': '600px'},
                children=[
                    html.Div(id='modal-title-row'),
                    html.Div(id='entry-details'),
                    html.Div([
                        html.Button('Edit', id='modal-edit-btn',
                                    n_clicks=0, style={'padding': '6px 16px', 'fontSize': '14px', 'backgroundColor': '#e3f2fd', 'color': '#1976d2', 'border': '1px solid #90caf9', 'borderRadius': '4px', 'cursor': 'pointer', 'marginRight': '8px'}),
                        html.Button('Close', id='modal-close-btn',
                                    n_clicks=0, style={'padding': '6px 16px', 'fontSize': '14px'})
                    ], id='modal-buttons', style={'marginTop': '20px'})
                ]
            )
        ]
    )
])


@callback(
    Output('user-info', 'children'),
    Input('current-user-id', 'data')
)
@callback(
    Output('calendar-view', 'children'),
    Output('calendar-date', 'data', allow_duplicate=True),
    Output('previous-view-mode', 'data'),
    Output('scroll-trigger', 'data'),
    Input('current-user-id', 'data'),
    Input('calendar-refresh', 'data'),
    Input('calendar-view-mode', 'value'),
    Input('calendar-date', 'data'),
    Input('url', 'pathname'),
    State('previous-view-mode', 'data'),
    State('scroll-trigger', 'data'),
    prevent_initial_call='initial_duplicate'
)
def calendar_view(user_id, refresh_trigger, view_mode, current_date, pathname, prev_view_mode, scroll_trigger):
    if view_mode != prev_view_mode:
        date_output = date.today().isoformat()
        prev_output = view_mode
        scroll_output = (scroll_trigger or 0) + 1
    else:
        date_output = dash.no_update
        prev_output = view_mode
        scroll_output = (scroll_trigger or 0) + 1

    # ...existing code...

    today = date.today()
    if not current_date:
        base_date = today
    else:
        base_date = date.fromisoformat(current_date)

    # Determine date range for query
    if view_mode == 'day':
        start_date = end_date = base_date
    elif view_mode == 'week':
        start_date = base_date - timedelta(days=base_date.weekday())
        end_date = start_date + timedelta(days=6)
    else:  # month
        start_date = date(base_date.year, base_date.month, 1)
        last_day = calendar.monthrange(base_date.year, base_date.month)[1]
        end_date = date(base_date.year, base_date.month, last_day)

    # Query individual entries for the range
    conn = get_db_connection()

    # Query food entries
    print(
        f"DEBUG: user_id={user_id}, start_date={start_date}, end_date={end_date}")
    food_df = pd.read_sql_query('''
        SELECT dl.date, fle.id as entry_id, f.description as name, fle.time, fle.notes, fle.meal_id
        FROM "dailylog" dl
        JOIN "foodlogentry" fle ON dl.id = fle.daily_log_id
        JOIN "food" f ON fle.fdc_id = f.fdc_id
        WHERE dl.user_id = %s AND dl.date BETWEEN %s AND %s
        ORDER BY dl.date, fle.time
    ''', conn, params=(user_id, start_date.isoformat(), end_date.isoformat()))
    print(f"DEBUG: food_df rows={len(food_df)}")

    symptom_df = pd.read_sql_query('''
        SELECT dl.date, sle.id as entry_id, s.name, sle.time, sle.severity, sle.notes
        FROM "dailylog" dl
        JOIN "symptomlogentry" sle ON dl.id = sle.daily_log_id
        JOIN "symptom" s ON sle.symptom_id = s.id
        WHERE dl.user_id = %s AND dl.date BETWEEN %s AND %s
        ORDER BY dl.date, sle.time
    ''', conn, params=(user_id, start_date.isoformat(), end_date.isoformat()))
    print(f"DEBUG: symptom_df rows={len(symptom_df)}")
    conn.close()
    # Group by date
    entries = {}
    for _, row in food_df.iterrows():
        d = row['date'].isoformat() if hasattr(
            row['date'], 'isoformat') else str(row['date'])
        if d not in entries:
            entries[d] = {'meals': {}, 'symptoms': [], 'foods': []}
        meal_id = row['meal_id']
        # Only treat as meal if meal_id is a real, non-null, non-empty, non-zero value
        if meal_id is not None and str(meal_id).strip() not in ('', 'None', 'none', 'null', '0') and meal_id != 0:
            if meal_id not in entries[d]['meals']:
                entries[d]['meals'][meal_id] = {
                    'time': row['time'].strftime('%H:%M') if hasattr(row['time'], 'strftime') else str(row['time']),
                    'foods': []
                }
            entries[d]['meals'][meal_id]['foods'].append({
                'id': row['entry_id'],
                'name': row['name'],
                'notes': row['notes']
            })
        else:
            entries[d]['foods'].append({
                'id': row['entry_id'],
                'name': row['name'],
                'time': row['time'].strftime('%H:%M') if hasattr(row['time'], 'strftime') else str(row['time']),
                'notes': row['notes']
            })

    for _, row in symptom_df.iterrows():
        d = row['date'].isoformat() if hasattr(
            row['date'], 'isoformat') else str(row['date'])
        if d not in entries:
            entries[d] = {'meals': {}, 'symptoms': [], 'foods': []}
        entries[d]['symptoms'].append({
            'id': row['entry_id'],
            'name': row['name'],
            'time': row['time'].strftime('%H:%M') if hasattr(row['time'], 'strftime') else str(row['time']),
            'severity': row['severity'],
            'notes': row['notes']
        })

    def create_entry_cards(entry_list, entry_type):
        cards = []
        if entry_type == 'meal':
            for meal_id, meal_data in entry_list.items():
                # Only treat as meal if meal_id is not None/empty/zero/null
                if meal_id is not None and str(meal_id).lower() not in ('', 'none', 'null', '0'):
                    food_names = [f["name"] for f in meal_data['foods']]
                    card_text = f"{', '.join(food_names)} ({meal_data['time']})"
                    card = html.Button(
                        card_text,
                        id={'type': 'entry', 'entry_type': 'meal',
                            'entry_id': meal_id},
                        style=get_entry_style('meal')
                    )
                    cards.append(card)
        elif entry_type == 'food':
            for entry in entry_list:
                # Always treat as food if not a real grouped meal
                card = html.Button(
                    f"{entry['name']}{format_time_display(entry['time'])}",
                    id={'type': 'entry', 'entry_type': 'food',
                        'entry_id': entry['id']},
                    style=get_entry_style('food')
                )
                cards.append(card)
        elif entry_type == 'symptom':
            for entry in entry_list:
                card = html.Button(
                    f"{entry['name']}{format_time_display(entry['time'])}",
                    id={'type': 'entry', 'entry_type': 'symptom',
                        'entry_id': entry['id']},
                    style=get_entry_style('symptom')
                )
                cards.append(card)
        return cards

    # Helper to convert time string to hour and minute
    def parse_time(tstr):
        try:
            h, m = map(int, tstr.split(':'))
            return h, m
        except Exception:
            return 0, 0

    # Helper to format time for display (hide 00:00)
    def format_time_display(time_str):
        """Returns empty string if time is 00:00, otherwise returns time in parentheses"""
        if time_str == '00:00':
            return ''
        return f" ({time_str})"

    # Render view
    if view_mode == 'day':
        d = base_date.isoformat()
        day_entries = entries.get(
            d, {'meals': {}, 'symptoms': [], 'foods': []})
        # Collect all entries with time and type
        all_entries = []
        for meal_id, meal in day_entries['meals'].items():
            # Only add as meal if meal_id is a real, non-null, non-empty, non-zero value
            if meal_id is not None and str(meal_id).strip() not in ('', 'None', 'none', 'null', '0') and meal_id != 0:
                all_entries.append({
                    'type': 'meal',
                    'id': meal_id,
                    'name': ', '.join([f['name'] for f in meal['foods']]),
                    'time': meal['time'],
                })
        for entry in day_entries['foods']:
            all_entries.append({
                'type': 'food',
                'id': entry['id'],
                'name': entry['name'],
                'time': entry['time'],
            })
        for entry in day_entries['symptoms']:
            all_entries.append({
                'type': 'symptom',
                'id': entry['id'],
                'name': entry['name'],
                'time': entry['time'],
            })

        # Improved: Render all entries in a single absolute container spanning the full 24-hour grid
        hour_height = 90  # px
        entry_duration_minutes = 30  # default duration for each entry
        entry_divs = []
        for entry in all_entries:
            h, m = parse_time(entry['time'])
            top_px = (h * hour_height) + (m / 60) * hour_height
            height_px = (entry_duration_minutes / 60) * hour_height
            entry_style = {
                'position': 'absolute',
                'left': '120px',  # align with grid start
                'top': f'{top_px}px',
                'height': f'{height_px}px',
                'width': '700px',  # match grid width
                'borderRadius': '4px',
                'padding': '2px 6px',
                'fontSize': '12px',
                'overflow': 'hidden',
                'zIndex': 2,
                'boxSizing': 'border-box',
                'textAlign': 'left',
                'background': entry.get('type') == 'symptom' and '#fff' or '#fff',
                'border': entry.get('type') == 'symptom' and '1px solid #ef9a9a' or '1px solid #64b5f6',
                'color': entry.get('type') == 'symptom' and '#ef5350' or '#64b5f6',
                'cursor': 'pointer',
            }
            entry_style.update(get_entry_style(entry['type']))
            # Build button content - only show time if not 00:00
            button_content = []
            if entry['time'] != '00:00':
                button_content.append(
                    html.Span(entry['time'], style={
                        'fontWeight': 'bold', 'fontSize': '11px', 'color': '#1976d2', 'marginRight': '8px'})
                )
            button_content.append(entry['name'])

            entry_divs.append(html.Button(
                button_content,
                id={'type': 'entry',
                    'entry_type': entry['type'], 'entry_id': entry['id']},
                style=entry_style
            ))
        # Hour labels and grid lines
        hour_labels = []
        for hour in range(24):
            hour_labels.append(html.Div(
                f"{hour:02d}:00",
                style={
                    'position': 'absolute',
                    'top': f'{hour * hour_height}px',
                    'left': '0',
                    'width': '120px',
                    'color': '#888',
                    'textAlign': 'right',
                    'marginRight': '10px',
                    'lineHeight': '1',
                    'height': '0',
                    'transform': 'translateY(-50%)',
                }
            ))
        # Hour grid lines
        hour_grid_lines = []
        for hour in range(24):
            hour_grid_lines.append(html.Div(
                style={
                    'position': 'absolute',
                    'top': f'{hour * hour_height}px',
                    'left': '120px',
                    'width': '700px',
                    'height': '1px',
                    'backgroundColor': '#eee',
                    'zIndex': 1,
                }
            ))
        # Now line
        now = datetime.now()
        current_hour = now.hour
        current_minute = now.minute
        is_today = base_date == now.date()
        current_time_top = (current_hour * hour_height) + \
            (current_minute / 60) * hour_height
        now_line = []
        if is_today:
            now_line = [
                html.Div(
                    [
                        html.Span(
                            now.strftime('%H:%M'),
                            style={
                                'color': '#1976d2',
                                'fontWeight': 'bold',
                                'fontSize': '12px',
                                'position': 'absolute',
                                'left': '0',
                                'width': '120px',
                                'textAlign': 'right',
                                'top': f'{current_time_top - 8}px',
                                'zIndex': 21
                            }
                        ),
                        html.Div(style={
                            'position': 'absolute',
                            'left': '120px',
                            'top': f'{current_time_top}px',
                            'width': '700px',
                            'height': '2px',
                            'backgroundColor': '#1976d2',
                            'zIndex': 20,
                            'border': 'none',
                            'boxShadow': 'none',
                        })
                    ],
                    style={
                        'position': 'absolute',
                        'left': '0',
                        'top': '0',
                        'width': '100%',
                        'pointerEvents': 'none',
                    }
                )
            ]
        container_style = {
            'width': '850px',
            'margin': '0 auto',
            'border': '1px solid #eee',
            'borderRadius': '8px',
            'background': '#fff',
            'boxShadow': '0 2px 8px #eee',
            'overflowY': 'auto',
            'maxHeight': f'{hour_height*8}px',
            'position': 'relative',
            'height': f'{hour_height*24}px',
        }
        day_title_style = {'textAlign': 'center', 'margin': '16px 0 8px 0',
                           'color': '#1976d2', 'fontWeight': 'bold'}
        the_div = html.Div([
            html.Div([
                html.H4(base_date.strftime('%A, %B %d, %Y'),
                        style={'display': 'inline-block', 'margin': '0 8px 0 0', 'color': '#1976d2', 'fontWeight': 'bold'}),
                html.Button('Today', id='calendar-today-btn', n_clicks=0,
                            style={'padding': '6px 12px', 'cursor': 'pointer', 'verticalAlign': 'middle'})
            ], style={'textAlign': 'center', 'margin': '16px 0 8px 0'}),
            html.Div(
                hour_labels + hour_grid_lines + now_line + entry_divs,
                style=container_style,
                id='day-hour-scroll'
            )
        ], **{'data-scroll-position': int(current_time_top) if is_today else 0})
        return the_div, date_output, prev_output, scroll_output
        now_line = []
        if is_today:
            now_line = [
                html.Div(
                    [
                        html.Span(
                            now.strftime('%H:%M'),
                            style={
                                'color': '#1976d2',
                                'fontWeight': 'bold',
                                'fontSize': '12px',
                                'position': 'absolute',
                                'left': '0',
                                'width': '120px',
                                'textAlign': 'right',
                                'top': f'{current_time_top - 8}px',
                                'zIndex': 21
                            }
                        ),
                        html.Div(style={
                            'position': 'absolute',
                            'left': '120px',
                            'top': f'{current_time_top}px',
                            'width': '700px',
                            'height': '2px',
                            'backgroundColor': '#1976d2',
                            'zIndex': 20,
                            'border': 'none',
                            'boxShadow': 'none',
                        })
                    ],
                    style={
                        'position': 'absolute',
                        'left': '0',
                        'top': '0',
                        'width': '100%',
                        'pointerEvents': 'none',
                    }
                )
            ]
        container_style = {'width': '850px', 'margin': '0 auto', 'border': '1px solid #eee', 'borderRadius': '8px', 'background': '#fff',
                           'boxShadow': '0 2px 8px #eee', 'overflowY': 'auto', 'maxHeight': f'{hour_height*8}px', 'position': 'relative'}
        day_title_style = {'textAlign': 'center', 'margin': '16px 0 8px 0',
                           'color': '#1976d2', 'fontWeight': 'bold'}
        # Only show the month as part of the day/date
        return html.Div([
            html.Div(
                [
                    dcc.Store(id='calendar-nav-store'),
                    html.Div([
                        html.Button('←', id='calendar-prev',
                                    n_clicks=0, style={'marginRight': '8px'}),
                        html.Button('Today', id='calendar-today',
                                    n_clicks=0, style={'marginRight': '8px'}),
                        html.Button('→', id='calendar-next',
                                    n_clicks=0, style={'marginRight': '16px'}),
                        dcc.Dropdown(
                            id='calendar-view-mode',
                            options=[
                                {'label': 'Day', 'value': 'day'},
                                {'label': 'Week', 'value': 'week'},
                                {'label': 'Month', 'value': 'month'}
                            ],
                            value=view_mode,
                            clearable=False,
                            style={
                                'width': '120px', 'display': 'inline-block', 'verticalAlign': 'middle'}
                        )
                    ], style={'display': 'inline-block', 'verticalAlign': 'middle'})
                ],
                style={'width': '100%', 'display': 'flex', 'justifyContent': 'center',
                       'alignItems': 'center', 'margin': '0 0 12px 0'}
            ),
            html.H4(base_date.strftime('%A, %B %d, %Y'),
                    style=day_title_style),
            html.Div(now_line + hour_rows,
                     style=container_style, id='day-hour-scroll')
        ])
        # Scroll to current hour (centered)
        # Show 4 hours before current
        scroll_to_hour = max(current_hour - 4, 0)
        container_style = {'width': '850px', 'margin': '0 auto', 'border': '1px solid #eee', 'borderRadius': '8px',
                           'background': '#fff', 'boxShadow': '0 2px 8px #eee', 'overflowY': 'auto', 'maxHeight': f'{hour_height*8}px'}
        is_today = base_date == now.date()
        day_title_style = {'textAlign': 'center',
                           'color': '#1976d2' if is_today else 'inherit'}
        the_div = html.Div([
            html.H4(base_date.strftime('%A, %B %d, %Y'),
                    style=day_title_style),
            html.Div(hour_rows, style=container_style, id='day-hour-scroll')
        ])
        return the_div, date_output, prev_output
        # Highlight current day in blue
        today = date.today()
        is_today = base_date == today
        day_title_style = {'textAlign': 'center',
                           'color': '#1976d2' if is_today else 'inherit'}
        the_div = html.Div([
            html.H4(base_date.strftime('%A, %B %d, %Y'),
                    style=day_title_style),
            html.Div(hour_rows, style={'width': '850px', 'margin': '0 auto', 'border': '1px solid #eee',
                     'borderRadius': '8px', 'background': '#fff', 'boxShadow': '0 2px 8px #eee'})
        ])
        return the_div, date_output, prev_output
    elif view_mode == 'week':
        week_days = [start_date + timedelta(days=i) for i in range(7)]
        today = date.today()
        hour_height = 90
        entry_height = 44  # px, taller for long titles
        # Build a grid: y-axis is hours, x-axis is days
        grid_rows = []
        now = datetime.now()
        current_hour = now.hour
        current_minute = now.minute
        is_this_week = any(day == now.date() for day in week_days)
        current_time_top = (current_hour * hour_height) + \
            (current_minute / 60) * hour_height
        grid_rows = []
        for hour in range(24):
            row_cells = []
            max_entry_height = 0
            for day in week_days:
                day_entries = entries.get(
                    day.isoformat(), {'meals': {}, 'symptoms': [], 'foods': []})
                all_entries = []
                for meal_id, meal in day_entries['meals'].items():
                    all_entries.append({'type': 'meal', 'id': meal_id, 'name': ', '.join(
                        [f['name'] for f in meal['foods']]), 'time': meal['time']})
                for entry in day_entries['foods']:
                    all_entries.append(
                        {'type': 'food', 'id': entry['id'], 'name': entry['name'], 'time': entry['time']})
                for entry in day_entries['symptoms']:
                    all_entries.append(
                        {'type': 'symptom', 'id': entry['id'], 'name': entry['name'], 'time': entry['time']})
                cell_entries = []
                hour_entries = []
                for entry in all_entries:
                    h, m = parse_time(entry['time'])
                    if h == hour:
                        hour_entries.append((m, entry))
                hour_entries.sort(key=lambda x: x[0])
                entries_by_minute = {}
                for m, entry in hour_entries:
                    entries_by_minute.setdefault(m, []).append(entry)
                for m, entry_group in entries_by_minute.items():
                    n = len(entry_group)
                    for idx, entry in enumerate(entry_group):
                        left_pct = idx * (100 / n)
                        width_pct = 100 / n
                        top_px = (m / 60) * hour_height
                        entry_style = {
                            'position': 'absolute',
                            'left': f'{left_pct}%',
                            'top': f'{top_px}px',
                            'minHeight': f'{entry_height}px',
                            'width': f'calc({width_pct}% - 8px)',
                            'borderRadius': '4px',
                            'padding': '6px 8px',
                            'fontSize': '13px',
                            'overflow': 'hidden',  # Prevent overflow
                            'maxWidth': '100%',    # Ensure entry stays within column
                            'zIndex': 2,
                            'boxSizing': 'border-box',
                            'whiteSpace': 'nowrap',  # Prevent wrapping
                            'wordBreak': 'break-word',
                            'textOverflow': 'ellipsis',  # Show ellipsis for overflow
                        }
                        # Use unified style for all entry types
                        entry_style.update(get_entry_style(entry['type']))
                        # Build entry content - only show time if not 00:00
                        entry_content = []
                        if entry['time'] != '00:00':
                            entry_content.append(
                                html.Span(entry['time'], style={
                                    'fontWeight': 'bold', 'fontSize': '11px', 'color': '#1976d2', 'marginRight': '8px'})
                            )
                        entry_content.append(entry['name'])

                        cell_entries.append(html.Button(
                            entry_content,
                            id={'type': 'entry',
                                'entry_type': entry['type'], 'entry_id': entry['id']},
                            style=entry_style
                        ))
                        entry_bottom = top_px + entry_height
                        if entry_bottom > max_entry_height:
                            max_entry_height = entry_bottom
                row_cells.append(html.Td(
                    html.Div(style={'position': 'relative', 'height': f'{max(hour_height if max_entry_height > 0 else 28, int(max_entry_height))}px',
                             'width': '100%'}, children=cell_entries),
                    style={'verticalAlign': 'top', 'padding': '0',
                           'border': '1px solid #ddd', 'minWidth': '120px'}
                ))
            row_height = max(hour_height if max_entry_height >
                             0 else 28, int(max_entry_height))
            grid_rows.append(html.Tr([
                # Only show the hour label, not the current time label (handled by now_line)
                html.Td(
                    f"{hour:02d}:00",
                    style={'width': '120px', 'color': '#888', 'textAlign': 'right', 'border': 'none', 'paddingRight': '8px',
                           'verticalAlign': 'top', 'lineHeight': '1', 'position': 'relative', 'top': '-1px'}
                ),
                *row_cells
            ]))
        # Add blue line for current time across the whole week (on top)
        now_line = []
        if is_this_week:
            # Calculate blue line top based on dynamic row heights
            # Calculate blue line top so it is after the current hour, regardless of row expansion
            row_heights = []
            for hour in range(24):
                max_entry_height = 0
                for day in week_days:
                    day_entries = entries.get(
                        day.isoformat(), {'meals': {}, 'symptoms': [], 'foods': []})
                    all_entries = []
                    for meal_id, meal in day_entries['meals'].items():
                        all_entries.append({'type': 'meal', 'id': meal_id, 'name': ', '.join(
                            [f['name'] for f in meal['foods']]), 'time': meal['time']})
                    for entry in day_entries['foods']:
                        all_entries.append(
                            {'type': 'food', 'id': entry['id'], 'name': entry['name'], 'time': entry['time']})
                    for entry in day_entries['symptoms']:
                        all_entries.append(
                            {'type': 'symptom', 'id': entry['id'], 'name': entry['name'], 'time': entry['time']})
                    hour_entries = [entry for entry in all_entries if parse_time(entry['time'])[
                        0] == hour]
                    for entry in hour_entries:
                        m = parse_time(entry['time'])[1]
                        top_px = (m / 60) * hour_height
                        entry_bottom = top_px + entry_height
                        if entry_bottom > max_entry_height:
                            max_entry_height = entry_bottom
                row_height = max(hour_height if max_entry_height >
                                 0 else 28, int(max_entry_height))
                row_heights.append(row_height)
            # The blue line should be after the current hour, so sum all row heights up to and including current_hour
            blue_line_top = sum(row_heights[:current_hour+1])
            # Add offset for current minute within the next hour
            next_hour_height = row_heights[current_hour+1] if current_hour+1 < len(
                row_heights) else row_heights[-1]
            blue_line_top += (current_minute / 60) * next_hour_height
            now_line = [
                html.Tr([
                    html.Td(
                        html.Span(
                            now.strftime('%H:%M'),
                            style={
                                'color': '#1976d2',
                                'fontWeight': 'bold',
                                'fontSize': '12px',
                                'position': 'absolute',
                                'left': '0',
                                'width': '120px',
                                'textAlign': 'right',
                                # align label with line
                                'top': f'{blue_line_top - 8}px',
                                'zIndex': 21
                            }
                        ),
                        style={'border': 'none', 'padding': '0',
                               'width': '120px', 'position': 'relative'}
                    ),
                    html.Td(
                        html.Div(style={
                            'position': 'absolute',
                            'left': '0',
                            'top': f'{blue_line_top}px',
                            'width': '100%',
                            'height': '2px',
                            'backgroundColor': '#1976d2',
                            'zIndex': 20,
                            'border': 'none',
                            'boxShadow': 'none',
                        }),
                        colSpan=len(week_days),
                        style={'position': 'relative',
                               'padding': '0', 'border': 'none'}
                    )
                ])
            ]
        # Only show the month as part of the day/date headers
        header_row = html.Tr([
            html.Th('', style={'border': 'none', 'width': '120px'}),
            *(html.Th(day.strftime('%a, %b %d'), style={'textAlign': 'center', 'color': '#1976d2' if day == now.date() else 'inherit', 'minWidth': '120px'}) for day in week_days)
        ])
        # Create week title with date range and week number
        week_number = start_date.isocalendar()[1]
        week_title = html.Div([
            html.Div([
                html.Span(str(week_number),
                          style={'display': 'inline-block', 'width': '32px', 'height': '32px', 'lineHeight': '32px',
                                 'borderRadius': '50%', 'backgroundColor': '#1976d2', 'color': 'white',
                                 'fontWeight': 'bold', 'fontSize': '14px', 'textAlign': 'center'}),
            ], style={'position': 'absolute', 'left': '60px', 'top': '50%', 'transform': 'translateY(-50%)'}),
            html.H4(f"{start_date.strftime('%b %d')} - {end_date.strftime('%b %d, %Y')}",
                    style={'display': 'inline-block', 'margin': '0 8px 0 0', 'color': '#1976d2', 'fontWeight': 'bold'}),
            html.Button('Today', id='calendar-today-btn', n_clicks=0,
                        style={'padding': '6px 12px', 'cursor': 'pointer', 'verticalAlign': 'middle'})
        ], style={'position': 'relative', 'textAlign': 'center', 'margin': '16px 0 8px 0'})
        # Center scroll on current time row if this week
        table_style = {'width': '100%', 'borderCollapse': 'collapse',
                       'margin': '0 auto', 'tableLayout': 'fixed', 'position': 'relative'}
        # Calculate scroll position for week view
        week_scroll_position = 0
        if is_this_week:
            row_heights = []
            for hour in range(24):
                max_entry_height = 0
                for day in week_days:
                    day_entries = entries.get(
                        day.isoformat(), {'meals': {}, 'symptoms': [], 'foods': []})
                    all_entries = []
                    for meal_id, meal in day_entries['meals'].items():
                        all_entries.append({'type': 'meal', 'id': meal_id, 'name': ', '.join(
                            [f['name'] for f in meal['foods']]), 'time': meal['time']})
                    for entry in day_entries['foods']:
                        all_entries.append(
                            {'type': 'food', 'id': entry['id'], 'name': entry['name'], 'time': entry['time']})
                    for entry in day_entries['symptoms']:
                        all_entries.append(
                            {'type': 'symptom', 'id': entry['id'], 'name': entry['name'], 'time': entry['time']})
                    hour_entries = [entry for entry in all_entries if parse_time(entry['time'])[
                        0] == hour]
                    for entry in hour_entries:
                        m = parse_time(entry['time'])[1]
                        top_px = (m / 60) * hour_height
                        entry_bottom = top_px + entry_height
                        if entry_bottom > max_entry_height:
                            max_entry_height = entry_bottom
                row_height = max(hour_height if max_entry_height >
                                 0 else 28, int(max_entry_height))
                row_heights.append(row_height)
            week_scroll_position = sum(row_heights[:current_hour]) + (
                current_minute / 60) * row_heights[current_hour] if current_hour < len(row_heights) else 0
        the_div = html.Div([
            week_title,
            html.Table([
                html.Thead([header_row]),
                html.Tbody(now_line + grid_rows)
            ], style=table_style, id='week-table')
        ], **{'data-scroll-position': int(week_scroll_position) if is_this_week else 0})
        return the_div, date_output, prev_output, scroll_output
        # Header row for days
        header_row = html.Tr([
            html.Th('', style={'border': 'none'}),
            *(html.Th(day.strftime('%a %d'), style={'textAlign': 'center', 'color': '#1976d2' if day == today else 'inherit', 'minWidth': '120px'}) for day in week_days)
        ])
        return html.Table([
            html.Thead([header_row]),
            html.Tbody(grid_rows)
        ], style={'width': '100%', 'borderCollapse': 'collapse', 'margin': '0 auto', 'tableLayout': 'fixed'})
    else:  # month
        year = base_date.year
        month = base_date.month
        cal = calendar.monthcalendar(year, month)
        today = date.today()
        # Show the month and year above the calendar
        month_title = html.Div([
            html.H4(base_date.strftime('%B %Y'),
                    style={'display': 'inline-block', 'margin': '0 8px 0 0', 'color': '#1976d2', 'fontWeight': 'bold'}),
            html.Button('Today', id='calendar-today-btn', n_clicks=0,
                        style={'padding': '6px 12px', 'cursor': 'pointer', 'verticalAlign': 'middle'})
        ], style={'textAlign': 'center', 'margin': '8px 0 8px 0'})

        def get_td_style(day):
            base_style = {'height': '120px', 'verticalAlign': 'top',
                          'padding': '5px', 'border': '1px solid #ddd', 'width': '14.28%'}
            if day == today.day and today.year == year and today.month == month:
                base_style['border'] = '1.5px solid #1976d2'
                base_style.pop('boxShadow', None)
                base_style.pop('borderRadius', None)
            return base_style

        def create_month_entry_cards(entry_list, entry_type):
            cards = []
            if entry_type == 'meal':
                for meal_id, meal_data in entry_list.items():
                    if meal_id is not None and str(meal_id).strip() not in ('', 'None', 'none', 'null', '0') and meal_id != 0:
                        food_names = [f["name"] for f in meal_data['foods']]
                        # Build card content - only show time if not 00:00
                        card_content = []
                        if meal_data['time'] != '00:00':
                            card_content.append(
                                html.Span(meal_data['time'], style={
                                    'fontWeight': 'bold', 'fontSize': '11px', 'color': '#1976d2', 'marginRight': '8px'})
                            )
                        card_content.append(f"{', '.join(food_names)}")

                        card = html.Button(
                            card_content,
                            id={'type': 'entry', 'entry_type': 'meal',
                                'entry_id': meal_id},
                            style=get_entry_style('meal')
                        )
                        cards.append(card)
            elif entry_type == 'food':
                for entry in entry_list:
                    # Build card content - only show time if not 00:00
                    card_content = []
                    if entry['time'] != '00:00':
                        card_content.append(
                            html.Span(entry['time'], style={
                                'fontWeight': 'bold', 'fontSize': '11px', 'color': '#1976d2', 'marginRight': '8px'})
                        )
                    card_content.append(entry['name'])

                    card = html.Button(
                        card_content,
                        id={'type': 'entry', 'entry_type': 'food',
                            'entry_id': entry['id']},
                        style=get_entry_style('food')
                    )
                    cards.append(card)
            elif entry_type == 'symptom':
                for entry in entry_list:
                    # Build card content - only show time if not 00:00
                    card_content = []
                    if entry['time'] != '00:00':
                        card_content.append(
                            html.Span(entry['time'], style={
                                'fontWeight': 'bold', 'fontSize': '11px', 'color': '#1976d2', 'marginRight': '8px'})
                        )
                    card_content.append(entry['name'])

                    card = html.Button(
                        card_content,
                        id={'type': 'entry', 'entry_type': 'symptom',
                            'entry_id': entry['id']},
                        style=get_entry_style('symptom')
                    )
                    cards.append(card)
            return cards

        month_table = html.Table([
            html.Thead(html.Tr([
                html.Th(day, style={'textAlign': 'center', 'width': '14.28%', 'color': '#1976d2' if (
                    today.year == year and today.month == month and idx == today.weekday()) else 'inherit'})
                for idx, day in enumerate(['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'])
            ])),
            html.Tbody([
                html.Tr([
                    html.Td([
                        html.Div(str(day), style={
                            'fontWeight': 'bold', 'marginBottom': '5px', 'color': '#1976d2' if (day == today.day and today.year == year and today.month == month) else 'inherit'}) if day != 0 else "",
                        html.Div(
                            (lambda day_data: [item['card'] for item in sorted(
                                (
                                    [{'type': 'meal', 'time': v['time'], 'card': card} 
                                     for k, v in day_data.get('meals', {}).items() 
                                     if k is not None and str(k).strip() not in ('', 'None', 'none', 'null', '0') and k != 0
                                     for card in create_month_entry_cards({k: v}, 'meal')]
                                ) + 
                                (
                                    [{'type': 'food', 'time': e['time'], 'card': card}
                                     for e in day_data.get('foods', [])
                                     for card in create_month_entry_cards([e], 'food')]
                                ) + 
                                (
                                    [{'type': 'symptom', 'time': e['time'], 'card': card}
                                     for e in day_data.get('symptoms', [])
                                     for card in create_month_entry_cards([e], 'symptom')]
                                ),
                                key=lambda x: x['time']
                            )])(entries.get(f"{year}-{month:02d}-{day:02d}", {}))
                            if day != 0 else [], 
                            style={'display': 'flex', 'flexDirection': 'column', 'gap': '2px'}) if day != 0 else ""
                    ], style=get_td_style(day)) for day in week
                ]) for week in cal
            ])
        ], style={'width': '80%', 'borderCollapse': 'collapse', 'margin': '0 auto', 'tableLayout': 'fixed'})
        the_div = html.Div([
            month_title,
            month_table
        ])
        return the_div, date_output, prev_output, scroll_output


@callback(
    Output('entry-modal', 'style'),
    Output('modal-title-row', 'children'),
    Output('entry-details', 'children'),
    Output('calendar-refresh', 'data', allow_duplicate=True),
    Output('modal-close-store', 'data'),
    Output('modal-entry-data', 'data', allow_duplicate=True),
    Input({'type': 'entry', 'entry_type': ALL, 'entry_id': ALL}, 'n_clicks'),
    Input('modal-close-btn', 'n_clicks'),
    State('entry-modal', 'style'),
    State('calendar-refresh', 'data'),
    State('modal-close-store', 'data'),
    prevent_initial_call=True
)
def manage_entry_modal(entry_clicks, close_clicks, current_style, refresh_data, modal_close_data):
    ctx = dash.callback_context
    if not ctx.triggered:
        return {'display': 'none'}, "", "", refresh_data, modal_close_data, {}

    trigger_id = ctx.triggered[0]['prop_id']

    if 'modal-close-btn' in trigger_id and close_clicks > 0:
        # Only hide the modal, do not refresh the calendar
        return {'display': 'none'}, "", "", dash.no_update, (modal_close_data or 0) + 1, {}

    # Check if any entry button was clicked and modal is not already open
    filtered_clicks = [click for click in (
        entry_clicks or []) if click is not None]
    if not filtered_clicks or not any(click and click == max(filtered_clicks) for click in filtered_clicks):
        return current_style, "", "", dash.no_update, modal_close_data, {}

    # Find which entry was clicked
    if ctx.triggered and len(ctx.triggered) > 0:
        trigger_id = ctx.triggered[0]['prop_id']
        if trigger_id and trigger_id != '.' and not 'modal-close-btn' in trigger_id:
            import json
            try:
                id_str = trigger_id.split('.')[0]
                id_dict = json.loads(id_str)
                entry_type = id_dict['entry_type']
                entry_id = id_dict['entry_id']
                print(f"DEBUG: entry_type={entry_type}, entry_id={entry_id}")

                conn = get_db_connection()
                if entry_type == 'meal':
                    # Only show meal details if meal_id is not None/null/empty
                    if entry_id is None or str(entry_id).lower() == 'none' or str(entry_id).strip() == '' or str(entry_id).lower() == 'null':
                        details = "Meal not found"
                    else:
                        meal_id_str = str(entry_id)
                        foods_df = pd.read_sql_query('''
                            SELECT fle.id as food_entry_id, f.description, fle.time, fle.notes, fle.fdc_id
                            FROM "foodlogentry" fle
                            JOIN "food" f ON fle.fdc_id = f.fdc_id
                            WHERE fle.meal_id = %s
                            ORDER BY fle.time
                        ''', conn, params=(meal_id_str,))
                        if not foods_df.empty:
                            food_items = []
                            foods_list = []
                            for idx, row in foods_df.iterrows():
                                # Remove seconds from time
                                time_str = str(row['time'])[:5] if len(
                                    str(row['time'])) > 5 else str(row['time'])
                                time_display = "" if time_str == '00:00' else f" ({time_str})"
                                notes_display = f" - {row['notes']}" if row['notes'] and row['notes'].strip(
                                ) else ""
                                
                                food_items.append(html.Li(
                                    f"{row['description']}{time_display}{notes_display}",
                                    style={'marginBottom': '8px', 'fontSize': '14px'}
                                ))
                                
                                # Store food data for editing
                                foods_list.append({
                                    'food_entry_id': int(row['food_entry_id']),
                                    'description': row['description'],
                                    'time': time_str,
                                    'fdc_id': int(row['fdc_id'])
                                })

                            food_names = ', '.join(
                                foods_df['description'].tolist())
                            meal_time = str(foods_df.iloc[0]['time'])[:5] if len(
                                str(foods_df.iloc[0]['time'])) > 5 else str(foods_df.iloc[0]['time'])

                            # Build content parts list
                            content_parts = []

                            # Only add time if not 00:00
                            if meal_time != '00:00':
                                content_parts.append(
                                    html.Div([
                                        html.Strong("Time:", style={
                                                    'color': '#666', 'fontSize': '14px'}),
                                        html.Span(meal_time, style={
                                                  'fontSize': '16px', 'marginLeft': '8px'})
                                    ], style={'marginBottom': '16px'})
                                )

                            # Add foods list
                            content_parts.append(
                                html.Div([
                                    html.Strong("Foods in this meal:", style={
                                                'color': '#666', 'fontSize': '14px', 'marginBottom': '8px', 'display': 'block'}),
                                    html.Ul(food_items, style={
                                            'paddingLeft': '20px', 'marginTop': '8px'})
                                ], style={'marginBottom': '16px'})
                            )

                            details = {'content': html.Div(content_parts, style={
                                                           'padding': '8px'}), 'title': food_names, 'entry_type': 'meal', 'entry_id': entry_id, 'time': meal_time, 'foods': foods_list}
                        else:
                            details = {'content': "Meal not found",
                                       'title': 'Meal Details'}
                elif entry_type == 'food':
                    # Get food entry details with ingredients
                    food_df = pd.read_sql_query('''
                        SELECT f.description, f.fdc_id, fle.time, fle.notes, dl.date
                        FROM "foodlogentry" fle
                        JOIN "food" f ON fle.fdc_id = f.fdc_id
                        JOIN "dailylog" dl ON fle.daily_log_id = dl.id
                        WHERE fle.id = %s
                    ''', conn, params=(entry_id,))

                    if not food_df.empty:
                        food_row = food_df.iloc[0]
                        food_name = food_row['description']
                        fdc_id = food_row['fdc_id']

                        # Get ingredients
                        ingredients_df = pd.read_sql_query('''
                            SELECT ingredient FROM "ingredient" WHERE fdc_id = %s
                        ''', conn, params=(fdc_id,))

                        # Format time
                        time_str = str(food_row['time'])[:5] if len(
                            str(food_row['time'])) > 5 else str(food_row['time'])

                        content_parts = []

                        # Only add time if not 00:00
                        if time_str != '00:00':
                            content_parts.append(
                                html.Div([
                                    html.Strong("Time:", style={
                                                'color': '#666', 'fontSize': '14px'}),
                                    html.Span(time_str, style={
                                              'fontSize': '16px', 'marginLeft': '8px'})
                                ], style={'marginBottom': '12px'})
                            )

                        # Add ingredients section if they exist
                        if not ingredients_df.empty:
                            ingredient_items = [html.Li(ing, style={'fontSize': '14px', 'marginBottom': '4px'})
                                                for ing in ingredients_df['ingredient'].tolist()]
                            content_parts.append(
                                html.Div([
                                    html.Strong("Ingredients:", style={
                                                'color': '#666', 'fontSize': '14px', 'marginBottom': '8px', 'display': 'block'}),
                                    html.Ul(ingredient_items, style={
                                            'paddingLeft': '20px', 'marginTop': '8px'})
                                ], style={'marginBottom': '16px'})
                            )

                        # Add notes if they exist
                        if food_row['notes'] and str(food_row['notes']).strip():
                            content_parts.append(
                                html.Div([
                                    html.Strong("Notes:", style={
                                                'color': '#666', 'fontSize': '14px'}),
                                    html.Div(str(food_row['notes']), style={
                                             'marginTop': '4px', 'padding': '8px', 'backgroundColor': '#f8f9fa', 'borderRadius': '4px', 'fontSize': '14px'})
                                ], style={'marginBottom': '16px'})
                            )

                        details = {'content': html.Div([c for c in content_parts if c is not None], style={
                                                       'padding': '8px'}), 'title': food_name, 'entry_type': 'food', 'entry_id': entry_id, 'time': time_str}
                    else:
                        details = {'content': "Food entry not found",
                                   'title': 'Food Details'}

                elif entry_type == 'symptom':
                    df = pd.read_sql_query('''
                        SELECT s.name, sle.time, sle.severity, sle.notes, sle.id, dl.date
                        FROM "symptomlogentry" sle
                        JOIN "symptom" s ON sle.symptom_id = s.id
                        JOIN "dailylog" dl ON sle.daily_log_id = dl.id
                        WHERE sle.id = %s
                    ''', conn, params=(entry_id,))
                    if not df.empty:
                        row = df.iloc[0]
                        symptom_date = row['date']

                        # Format time display (hide if 00:00, remove seconds)
                        # If time is 00:00, check for date range
                        time_str = str(row['time'])[:5] if len(
                            str(row['time'])) > 5 else str(row['time'])

                        if time_str != '00:00':
                            time_display = f"Time: {time_str}"
                        else:
                            # Find date range for this symptom with 00:00 time
                            try:
                                # Get the symptom_id and current date for this entry
                                with conn.cursor() as cur:
                                    cur.execute(
                                        'SELECT symptom_id, daily_log_id FROM "symptomlogentry" WHERE id = %s', (entry_id,))
                                    symptom_info = cur.fetchone()
                                    symptom_id = symptom_info[0]
                                    daily_log_id = symptom_info[1]

                                    cur.execute(
                                        'SELECT date FROM "dailylog" WHERE id = %s', (daily_log_id,))
                                    current_date = cur.fetchone()[0]

                                # Calculate date range
                                from datetime import timedelta
                                start_range = current_date - timedelta(days=30)
                                end_range = current_date + timedelta(days=30)

                                range_df = pd.read_sql_query('''
                                    SELECT MIN(dl.date) as start_date, MAX(dl.date) as end_date, COUNT(*) as days
                                    FROM "symptomlogentry" sle
                                    JOIN "dailylog" dl ON sle.daily_log_id = dl.id
                                    WHERE sle.symptom_id = %s
                                    AND sle.time = '00:00'
                                    AND sle.severity = %s
                                    AND dl.date BETWEEN %s AND %s
                                ''', conn, params=(int(symptom_id), int(row['severity']), start_range, end_range))

                                if not range_df.empty and range_df.iloc[0]['days'] > 1:
                                    start = range_df.iloc[0]['start_date']
                                    end = range_df.iloc[0]['end_date']
                                    days = range_df.iloc[0]['days']
                                    time_display = f"Duration: {start.strftime('%b %d')} - {end.strftime('%b %d, %Y')} ({days} days)"
                                else:
                                    time_display = None
                            except Exception as e:
                                print(f"Error getting date range: {e}")
                                time_display = None

                        # Severity emoji mapping
                        severity_emojis = {
                            1: '', 2: '🙁', 3: '', 4: '😕', 5: '', 6: '😟', 7: '', 8: '😣', 9: '', 10: '😫'}
                        severity_emoji = severity_emojis.get(
                            row['severity'], '')

                        # Build content components
                        content_parts = []

                        # Add severity
                        if row['severity']:
                            content_parts.append(
                                html.Div([
                                    html.Strong("Severity:", style={
                                                'color': '#666', 'fontSize': '14px'}),
                                    html.Span(f" {severity_emoji} {row['severity']}/10", style={
                                              'fontSize': '16px', 'marginLeft': '8px'})
                                ], style={'marginBottom': '12px'})
                            )

                        # Add time/duration only if it exists
                        if time_display:
                            content_parts.append(
                                html.Div([
                                    html.Strong(time_display, style={
                                                'color': '#666', 'fontSize': '14px'})
                                ], style={'marginBottom': '12px'})
                            )

                        # Only add notes section if notes exist
                        if row['notes'] and row['notes'].strip():
                            content_parts.append(
                                html.Div([
                                    html.Strong("Notes:", style={
                                                'color': '#666', 'fontSize': '14px'}),
                                    html.Div(row['notes'], style={
                                             'marginTop': '4px', 'padding': '8px', 'backgroundColor': '#f8f9fa', 'borderRadius': '4px', 'fontSize': '14px'})
                                ], style={'marginBottom': '16px'})
                            )

                        details = {'content': html.Div([c for c in content_parts if c is not None], style={
                                                       'padding': '8px'}), 'title': row['name'], 'entry_type': 'symptom', 'entry_id': entry_id, 'time': time_str, 'severity': int(row['severity'])}
                    else:
                        details = {'content': "Entry not found",
                                   'title': 'Entry Details'}
                conn.close()
                # Return with dynamic title and delete button in title row
                if isinstance(details, dict) and 'entry_type' in details:
                    title_row = html.Div([
                        html.H3(details['title'], style={
                                'color': '#1976d2', 'marginBottom': '0', 'display': 'inline-block', 'flex': '1'}),
                        html.Button('Delete', id={'type': 'modal-delete-entry', 'entry_type': details['entry_type'], 'entry_id': details['entry_id']},
                                    n_clicks=0, style={'padding': '4px 12px', 'fontSize': '12px', 'backgroundColor': '#ffebee', 'color': '#d32f2f', 'border': '1px solid #ffcdd2', 'borderRadius': '4px', 'cursor': 'pointer'})
                    ], style={'display': 'flex', 'alignItems': 'center', 'marginBottom': '20px', 'paddingBottom': '8px', 'borderBottom': '2px solid #90caf9'})
                    # Extract entry data for editing
                    entry_data = {k: v for k, v in details.items() if k not in ['content', 'title']}
                    return {'display': 'block', 'position': 'fixed', 'zIndex': 1000, 'left': 0, 'top': 0, 'width': '100%', 'height': '100%', 'backgroundColor': 'rgba(0,0,0,0.4)'}, title_row, details['content'], dash.no_update, modal_close_data, entry_data
                elif isinstance(details, dict):
                    title_row = html.H3(details['title'], style={'color': '#1976d2', 'marginBottom': '20px', 'borderBottom': '2px solid #90caf9', 'paddingBottom': '8px'})
                    return {'display': 'block', 'position': 'fixed', 'zIndex': 1000, 'left': 0, 'top': 0, 'width': '100%', 'height': '100%', 'backgroundColor': 'rgba(0,0,0,0.4)'}, title_row, details['content'], dash.no_update, modal_close_data, {}
                else:
                    return {'display': 'block', 'position': 'fixed', 'zIndex': 1000, 'left': 0, 'top': 0, 'width': '100%', 'height': '100%', 'backgroundColor': 'rgba(0,0,0,0.4)'}, "", details, dash.no_update, modal_close_data, {}
            except Exception as e:
                return current_style, "", f"Error: {e}", dash.no_update, modal_close_data, {}

    return current_style, "", "", dash.no_update, modal_close_data, {}


@callback(
    Output('entry-modal', 'style', allow_duplicate=True),
    Output('calendar-refresh', 'data', allow_duplicate=True),
    Input({'type': 'modal-delete-entry',
          'entry_type': ALL, 'entry_id': ALL}, 'n_clicks'),
    State('current-user-id', 'data'),
    State('calendar-refresh', 'data'),
    prevent_initial_call=True
)
def delete_entry(delete_clicks, user_id, current_refresh):
    ctx = dash.callback_context
    if not ctx.triggered:
        return dash.no_update, dash.no_update

    # Check if any delete button was actually clicked
    if not any(click > 0 for click in delete_clicks if click is not None):
        return dash.no_update, dash.no_update

    trigger_id = ctx.triggered[0]['prop_id']
    import json
    id_str = trigger_id.split('.')[0]
    id_dict = json.loads(id_str)
    entry_type = id_dict['entry_type']
    entry_id = id_dict['entry_id']

    conn = get_db_connection()
    with conn.cursor() as cur:
        if entry_type == 'meal':
            cur.execute(
                'DELETE FROM "foodlogentry" WHERE meal_id = %s AND daily_log_id IN (SELECT id FROM "dailylog" WHERE user_id = %s)',
                (entry_id, user_id))
        elif entry_type == 'food':
            cur.execute(
                'DELETE FROM "foodlogentry" WHERE id = %s AND daily_log_id IN (SELECT id FROM "dailylog" WHERE user_id = %s)',
                (entry_id, user_id))
        elif entry_type == 'symptom':
            cur.execute(
                'DELETE FROM "symptomlogentry" WHERE id = %s AND daily_log_id IN (SELECT id FROM "dailylog" WHERE user_id = %s)',
                (entry_id, user_id))
        conn.commit()
    conn.close()
    return {'display': 'none'}, (current_refresh or 0) + 1


@callback(
    Output('entry-details', 'children', allow_duplicate=True),
    Output('modal-edit-mode', 'data'),
    Output('modal-entry-data', 'data'),
    Output('calendar-refresh', 'data', allow_duplicate=True),
    Input('modal-edit-btn', 'n_clicks'),
    Input({'type': 'modal-save-edit', 'index': ALL}, 'n_clicks'),
    Input({'type': 'modal-cancel-edit', 'index': ALL}, 'n_clicks'),
    State('modal-edit-mode', 'data'),
    State('modal-entry-data', 'data'),
    State({'type': 'modal-edit-time', 'index': ALL}, 'value'),
    State({'type': 'modal-edit-severity', 'index': ALL}, 'value'),
    State({'type': 'modal-edit-meal-name', 'index': ALL}, 'value'),
    State({'type': 'modal-edit-food-keep', 'index': ALL}, 'value'),
    State('calendar-refresh', 'data'),
    prevent_initial_call=True
)
def handle_edit_mode(edit_clicks, save_clicks, cancel_clicks, edit_mode, entry_data, time_values, severity_values, meal_name_values, food_keep_values, refresh_data):
    """Toggle edit mode and save changes to entry"""
    ctx = dash.callback_context
    if not ctx.triggered:
        return dash.no_update, dash.no_update, dash.no_update, dash.no_update
    
    trigger_id = ctx.triggered[0]['prop_id']
    
    # Cancel edit mode
    if 'modal-cancel-edit' in trigger_id:
        # Rebuild readonly view from entry_data
        return build_entry_view(entry_data), False, entry_data, dash.no_update
    
    # Save changes
    if 'modal-save-edit' in trigger_id and entry_data:
        # Get edited values from State
        new_time = time_values[0] if time_values and len(time_values) > 0 else None
        new_severity = severity_values[0] if severity_values and len(severity_values) > 0 else None
        
        # Update database
        conn = get_db_connection()
        with conn.cursor() as cur:
            entry_type = entry_data.get('entry_type')
            entry_id = entry_data.get('entry_id')
            
            if entry_type == 'food' and new_time:
                cur.execute(
                    'UPDATE "foodlogentry" SET time = %s WHERE id = %s',
                    (new_time, entry_id))
            elif entry_type == 'meal':
                # Update time for all food entries in the meal
                if new_time:
                    cur.execute(
                        'UPDATE "foodlogentry" SET time = %s WHERE meal_id = %s',
                        (new_time, entry_id))
                
                # Handle food removal - delete unchecked foods
                foods = entry_data.get('foods', [])
                for idx, food in enumerate(foods):
                    if idx < len(food_keep_values):
                        keep_values = food_keep_values[idx]
                        if not keep_values or 'keep' not in keep_values:
                            # Delete this food entry
                            cur.execute(
                                'DELETE FROM "foodlogentry" WHERE id = %s',
                                (food['food_entry_id'],))
                
                # Check if any foods remain in the meal
                cur.execute(
                    'SELECT COUNT(*) FROM "foodlogentry" WHERE meal_id = %s',
                    (entry_id,))
                remaining_count = cur.fetchone()[0]
                
                # If no foods remain, the meal is deleted (handled by the delete cascade)
                if remaining_count == 0:
                    conn.commit()
                    conn.close()
                    # Close modal and refresh
                    return dash.no_update, False, {}, (refresh_data or 0) + 1
                
                # Update foods list in entry_data
                entry_data['foods'] = [f for idx, f in enumerate(foods) 
                                      if idx < len(food_keep_values) and food_keep_values[idx] and 'keep' in food_keep_values[idx]]
                
            elif entry_type == 'symptom':
                if new_time and new_severity:
                    cur.execute(
                        'UPDATE "symptomlogentry" SET time = %s, severity = %s WHERE id = %s',
                        (new_time, int(new_severity), entry_id))
                elif new_time:
                    cur.execute(
                        'UPDATE "symptomlogentry" SET time = %s WHERE id = %s',
                        (new_time, entry_id))
                elif new_severity:
                    cur.execute(
                        'UPDATE "symptomlogentry" SET severity = %s WHERE id = %s',
                        (int(new_severity), entry_id))
            
            conn.commit()
        conn.close()
        
        # Update entry_data with new values
        if new_time:
            entry_data['time'] = new_time
        if new_severity:
            entry_data['severity'] = int(new_severity)
        
        # Return updated view and trigger calendar refresh
        return build_entry_view(entry_data), False, entry_data, (refresh_data or 0) + 1
    
    # Enter edit mode
    if 'modal-edit-btn' in trigger_id and edit_clicks > 0:
        # Build editable view
        return build_entry_edit_view(entry_data), True, entry_data, dash.no_update
    
    return dash.no_update, dash.no_update, dash.no_update, dash.no_update


def build_entry_view(entry_data):
    """Build readonly view of entry"""
    if not entry_data:
        return html.Div("No entry data")
    
    entry_type = entry_data.get('entry_type')
    content_parts = []
    
    if entry_type in ['food', 'meal', 'symptom']:
        time_str = entry_data.get('time', '00:00')
        if time_str != '00:00':
            content_parts.append(
                html.Div([
                    html.Strong("Time:", style={'color': '#666', 'fontSize': '14px'}),
                    html.Span(time_str, style={'fontSize': '16px', 'marginLeft': '8px'})
                ], style={'marginBottom': '12px'})
            )
    
    if entry_type == 'meal':
        foods = entry_data.get('foods', [])
        if foods and isinstance(foods, list):
            food_items = [html.Li(f.get('description', ''), style={'fontSize': '14px', 'marginBottom': '4px'}) 
                         for f in foods if isinstance(f, dict)]
            if food_items:
                content_parts.append(
                    html.Div([
                        html.Strong("Foods in this meal:", style={'color': '#666', 'fontSize': '14px', 'marginBottom': '8px', 'display': 'block'}),
                        html.Ul(food_items, style={'paddingLeft': '20px', 'marginTop': '8px'})
                    ], style={'marginBottom': '16px'})
                )
    
    if entry_type == 'symptom':
        severity = entry_data.get('severity', 5)
        severity_emojis = {1: '', 2: '🙁', 3: '', 4: '😕', 5: '', 6: '😟', 7: '', 8: '😣', 9: '', 10: '😫'}
        severity_emoji = severity_emojis.get(severity, '')
        content_parts.append(
            html.Div([
                html.Strong("Severity:", style={'color': '#666', 'fontSize': '14px'}),
                html.Span(f" {severity}/10 {severity_emoji}", style={'fontSize': '16px', 'marginLeft': '8px'})
            ], style={'marginBottom': '12px'})
        )
    
    return html.Div(content_parts, style={'padding': '8px'})


def build_entry_edit_view(entry_data):
    """Build editable view of entry with input fields"""
    if not entry_data:
        return html.Div("No entry data available")
    
    entry_type = entry_data.get('entry_type')
    content_parts = []
    
    if entry_type in ['food', 'meal', 'symptom']:
        # Time input (using text type with placeholder for HH:MM format)
        time_value = entry_data.get('time', '00:00')
        content_parts.append(
            html.Div([
                html.Strong("Time:", style={'color': '#666', 'fontSize': '14px', 'display': 'block', 'marginBottom': '4px'}),
                dcc.Input(
                    id={'type': 'modal-edit-time', 'index': 0},
                    type='text',
                    value=time_value,
                    placeholder='HH:MM',
                    style={'width': '150px', 'padding': '6px', 'fontSize': '14px', 'borderRadius': '4px', 'border': '1px solid #ccc'}
                )
            ], style={'marginBottom': '16px'})
        )
    
    if entry_type == 'meal':
        # Meal name input
        foods = entry_data.get('foods', [])
        if foods and isinstance(foods, list):
            meal_name = ', '.join([f.get('description', '') for f in foods if isinstance(f, dict)])
        else:
            meal_name = ''
        content_parts.append(
            html.Div([
                html.Strong("Meal Name:", style={'color': '#666', 'fontSize': '14px', 'display': 'block', 'marginBottom': '4px'}),
                dcc.Input(
                    id={'type': 'modal-edit-meal-name', 'index': 0},
                    type='text',
                    value=meal_name,
                    style={'width': '300px', 'padding': '6px', 'fontSize': '14px', 'borderRadius': '4px', 'border': '1px solid #ccc'}
                )
            ], style={'marginBottom': '16px'})
        )
        
        # Foods list with remove buttons
        foods = entry_data.get('foods', [])
        if foods and isinstance(foods, list):
            food_checkboxes = []
            for idx, food in enumerate(foods):
                if isinstance(food, dict):
                    food_checkboxes.append(
                        html.Div([
                            dcc.Checklist(
                                id={'type': 'modal-edit-food-keep', 'index': idx},
                                options=[{'label': food.get('description', 'Unknown food'), 'value': 'keep'}],
                                value=['keep'],
                                style={'display': 'inline-block'}
                            ),
                            html.Span(' (uncheck to remove)', style={'fontSize': '12px', 'color': '#999', 'marginLeft': '8px'})
                        ], style={'marginBottom': '8px'})
                    )
            
            if food_checkboxes:
                content_parts.append(
                    html.Div([
                        html.Strong("Foods in meal:", style={'color': '#666', 'fontSize': '14px', 'display': 'block', 'marginBottom': '8px'}),
                        html.Div(food_checkboxes)
                    ], style={'marginBottom': '16px'})
                )
    
    if entry_type == 'symptom':
        # Severity dropdown
        severity_value = entry_data.get('severity', 5)
        content_parts.append(
            html.Div([
                html.Strong("Severity:", style={'color': '#666', 'fontSize': '14px', 'display': 'block', 'marginBottom': '4px'}),
                dcc.Dropdown(
                    id={'type': 'modal-edit-severity', 'index': 0},
                    options=[{'label': str(i), 'value': i} for i in range(1, 11)],
                    value=severity_value,
                    clearable=False,
                    style={'width': '150px'}
                )
            ], style={'marginBottom': '16px'})
        )
    
    # Action buttons
    content_parts.append(
        html.Div([
            html.Button('Save', id={'type': 'modal-save-edit', 'index': 0},
                       style={'padding': '8px 16px', 'fontSize': '14px', 'backgroundColor': '#4caf50', 'color': 'white', 'border': 'none', 'borderRadius': '4px', 'cursor': 'pointer', 'marginRight': '8px'}),
            html.Button('Cancel', id={'type': 'modal-cancel-edit', 'index': 0},
                       style={'padding': '8px 16px', 'fontSize': '14px', 'backgroundColor': '#f5f5f5', 'color': '#666', 'border': '1px solid #ccc', 'borderRadius': '4px', 'cursor': 'pointer'})
        ], style={'marginTop': '20px'})
    )
    
    return html.Div(content_parts, style={'padding': '8px'})


@callback(
    Output('calendar-date', 'data', allow_duplicate=True),
    Input('calendar-prev-btn', 'n_clicks'),
    Input('calendar-next-btn', 'n_clicks'),
    Input('calendar-today-btn', 'n_clicks'),
    State('calendar-date', 'data'),
    State('calendar-view-mode', 'value'),
    prevent_initial_call=True
)
def navigate_calendar(prev_clicks, next_clicks, today_clicks, current_date, view_mode):
    """Navigate between days, weeks, or months based on view mode."""
    ctx = dash.callback_context
    if not ctx.triggered:
        return dash.no_update

    trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]

    # Handle "Today" button
    if trigger_id == 'calendar-today-btn':
        return date.today().isoformat()

    # Parse current date
    if not current_date:
        base_date = date.today()
    else:
        base_date = date.fromisoformat(current_date)

    # Navigate based on view mode and button clicked
    if trigger_id == 'calendar-prev-btn':
        if view_mode == 'day':
            new_date = base_date - timedelta(days=1)
        elif view_mode == 'week':
            new_date = base_date - timedelta(weeks=1)
        else:  # month
            # Go to previous month
            if base_date.month == 1:
                new_date = date(base_date.year - 1, 12, 1)
            else:
                new_date = date(base_date.year, base_date.month - 1, 1)
    elif trigger_id == 'calendar-next-btn':
        if view_mode == 'day':
            new_date = base_date + timedelta(days=1)
        elif view_mode == 'week':
            new_date = base_date + timedelta(weeks=1)
        else:  # month
            # Go to next month
            if base_date.month == 12:
                new_date = date(base_date.year + 1, 1, 1)
            else:
                new_date = date(base_date.year, base_date.month + 1, 1)
    else:
        return dash.no_update

    return new_date.isoformat()


# Clientside callback to auto-scroll to current time in day and week views
dash.clientside_callback(
    """
    function(scrollTrigger, viewMode) {
        if (!scrollTrigger) return window.dash_clientside.no_update;
        
        setTimeout(function() {
            // For day view
            const dayContainer = document.getElementById('day-hour-scroll');
            if (dayContainer) {
                const scrollPosition = parseInt(dayContainer.parentElement.getAttribute('data-scroll-position') || 0);
                if (scrollPosition > 0) {
                    const scrollTo = Math.max(scrollPosition - 300, 0);
                    dayContainer.scrollTop = scrollTo;
                }
            }
            
            // For week view
            const weekTable = document.getElementById('week-table');
            if (weekTable && weekTable.parentElement) {
                const scrollPosition = parseInt(weekTable.parentElement.getAttribute('data-scroll-position') || 0);
                if (scrollPosition > 0) {
                    const scrollTo = Math.max(scrollPosition - 300, 0);
                    weekTable.parentElement.scrollTop = scrollTo;
                    weekTable.scrollIntoView({behavior: 'auto', block: 'start'});
                    window.scrollTo(0, scrollTo);
                }
            }
        }, 100);
        
        return window.dash_clientside.no_update;
    }
    """,
    Output('calendar-view', 'data-dummy', allow_duplicate=True),
    Input('scroll-trigger', 'data'),
    State('calendar-view-mode', 'value'),
    prevent_initial_call=True
)

# Clientside callback to handle double-clicks on calendar and extract date/time
dash.clientside_callback(
    """
    function(viewMode, calendarDate) {
        // Add double-click listener to calendar
        setTimeout(function() {
            const calendarView = document.getElementById('calendar-view');
            const hiddenBtn = document.getElementById('hidden-doubleclick-btn');
            
            if (!calendarView || !hiddenBtn) return;
            
            // Remove existing listener
            if (calendarView._dblClickHandler) {
                calendarView.removeEventListener('dblclick', calendarView._dblClickHandler);
            }
            
            // Create new handler
            calendarView._dblClickHandler = function(event) {
                // Get current time
                let now = new Date();
                let currentTime = String(now.getHours()).padStart(2, '0') + ':' + String(now.getMinutes()).padStart(2, '0');
                
                let clickData = {
                    view_mode: viewMode,
                    date: calendarDate,
                    time: currentTime
                };
                
                // Month view - extract date from day cell, keep current time
                if (viewMode === 'month') {
                    let cell = event.target.closest('td');
                    if (cell) {
                        let dayDiv = cell.querySelector('div');
                        if (dayDiv && dayDiv.textContent) {
                            let day = parseInt(dayDiv.textContent);
                            if (day > 0 && day <= 31) {
                                // Find the month title to get the correct year and month being displayed
                                let monthTitleElem = document.querySelector('h4');
                                if (monthTitleElem) {
                                    let monthYearText = monthTitleElem.textContent.trim();
                                    // Parse "Month YYYY" format
                                    let dateFromTitle = new Date(monthYearText + ' 1');
                                    clickData.date = dateFromTitle.getFullYear() + '-' + 
                                                   String(dateFromTitle.getMonth() + 1).padStart(2, '0') + '-' + 
                                                   String(day).padStart(2, '0');
                                } else {
                                    // Fallback to calendarDate if title not found
                                    let dateObj = new Date(calendarDate);
                                    clickData.date = dateObj.getFullYear() + '-' + 
                                                   String(dateObj.getMonth() + 1).padStart(2, '0') + '-' + 
                                                   String(day).padStart(2, '0');
                                }
                            }
                        }
                    }
                    // Store and trigger for month view
                    window._doubleClickData = clickData;
                    hiddenBtn.click();
                    return;
                }
                // Day view - extract time from position
                else if (viewMode === 'day') {
                    // Check if we clicked inside the hour scroll container
                    let container = document.getElementById('day-hour-scroll');
                    if (container && container.contains(event.target)) {
                        // Avoid triggering on entry buttons
                        if (event.target.closest('button[id*="entry"]')) {
                            return;
                        }
                        let rect = container.getBoundingClientRect();
                        let y = event.clientY - rect.top + container.scrollTop;
                        let hourHeight = 90; // pixels per hour
                        let totalMinutes = Math.floor((y / hourHeight) * 60);
                        let hours = Math.floor(totalMinutes / 60);
                        let minutes = totalMinutes % 60;
                        clickData.time = String(hours).padStart(2, '0') + ':' + String(minutes).padStart(2, '0');
                        
                        // Store and trigger
                        window._doubleClickData = clickData;
                        hiddenBtn.click();
                    }
                    return;
                }
                // Week view - extract date and time
                else if (viewMode === 'week') {
                    // Avoid triggering on entry buttons
                    if (event.target.closest('button[id*="entry"]')) {
                        return;
                    }
                    
                    let cell = event.target.closest('td');
                    if (cell) {
                        let table = cell.closest('table');
                        if (table) {
                            let row = cell.parentElement;
                            let cellIndex = Array.from(row.children).indexOf(cell);
                            
                            // Skip if it's the time label column (first column)
                            if (cellIndex === 0) {
                                return;
                            }
                            
                            // Get the header row to find date
                            let headerRow = table.querySelector('thead tr');
                            if (headerRow) {
                                let headerCells = headerRow.querySelectorAll('th');
                                if (headerCells[cellIndex]) {
                                    let headerText = headerCells[cellIndex].textContent.trim();
                                    // Parse "Day DD" format to get the day number
                                    let dayMatch = headerText.match(/(\d+)/);
                                    if (dayMatch) {
                                        let day = parseInt(dayMatch[1]);
                                        let dateObj = new Date(calendarDate);
                                        // Find the week that contains this date
                                        let weekStart = new Date(dateObj);
                                        weekStart.setDate(dateObj.getDate() - dateObj.getDay() + 1); // Monday
                                        // Calculate which day of the week this is (cellIndex - 1 for 0-based after time column)
                                        let targetDate = new Date(weekStart);
                                        targetDate.setDate(weekStart.getDate() + (cellIndex - 1));
                                        clickData.date = targetDate.getFullYear() + '-' + 
                                                       String(targetDate.getMonth() + 1).padStart(2, '0') + '-' + 
                                                       String(targetDate.getDate()).padStart(2, '0');
                                    }
                                }
                            }
                            
                            // Get the row to determine the hour
                            let rowIndex = Array.from(table.querySelectorAll('tbody tr')).indexOf(row);
                            if (rowIndex >= 0) {
                                // Each row is one hour
                                let hour = rowIndex;
                                // Calculate minutes from Y position within cell
                                let rect = cell.getBoundingClientRect();
                                let y = event.clientY - rect.top;
                                let cellHeight = rect.height;
                                let minuteFraction = y / cellHeight;
                                let minutes = Math.floor(minuteFraction * 60);
                                clickData.time = String(hour).padStart(2, '0') + ':' + String(minutes).padStart(2, '0');
                            }
                        }
                        
                        // Store and trigger
                        window._doubleClickData = clickData;
                        hiddenBtn.click();
                    }
                    return;
                }
                
                // Store the click data in a global variable
                window._doubleClickData = clickData;
                
                // Trigger the hidden button
                hiddenBtn.click();
            };
            
            // Add the listener
            calendarView.addEventListener('dblclick', calendarView._dblClickHandler);
        }, 500);
        
        return window.dash_clientside.no_update;
    }
    """,
    Output('calendar-view', 'data-doubleclick', allow_duplicate=True),
    Input('calendar-view-mode', 'value'),
    Input('calendar-date', 'data'),
    prevent_initial_call=True
)

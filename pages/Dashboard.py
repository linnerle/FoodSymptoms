import dash
from backend.utils import get_db_connection
import calendar
from datetime import datetime, date, timedelta
import pandas as pd
from dash import html, dcc, Input, Output, State, callback, ALL


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

    dcc.Dropdown(
        id='calendar-view-mode',
        options=[
            {'label': 'Day', 'value': 'day'},
            {'label': 'Week', 'value': 'week'},
            {'label': 'Month', 'value': 'month'}
        ],
        value='day',
        style={'width': '120px', 'margin': '16px auto', 'display': 'block'}
    ),
    html.Div([
        html.Div(id='calendar-view')
    ]),
    dcc.Store(id='calendar-refresh', data=0),
    dcc.Store(id='calendar-date', data=date.today().isoformat()),
    dcc.Store(id='modal-close-store', data=0),
    dcc.Store(id='previous-view-mode', data='day'),
    html.Div(
        id='entry-modal',
        style={'display': 'none', 'position': 'fixed', 'zIndex': 1000, 'left': 0, 'top': 0,
               'width': '100%', 'height': '100%', 'backgroundColor': 'rgba(0,0,0,0.4)'},
        children=[
            html.Div(
                style={'backgroundColor': '#fefefe', 'margin': '15% auto', 'padding': '20px',
                       'border': '1px solid #888', 'width': '80%', 'maxWidth': '500px'},
                children=[
                    html.H3("Entry Details"),
                    html.Div(id='entry-details'),
                    html.Button('Close', id='modal-close-btn',
                                n_clicks=0, style={'marginTop': '10px'})
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
    Input('current-user-id', 'data'),
    Input('calendar-refresh', 'data'),
    Input('calendar-view-mode', 'value'),
    Input('calendar-date', 'data'),
    Input('url', 'pathname'),
    State('previous-view-mode', 'data'),
    prevent_initial_call='initial_duplicate'
)
def calendar_view(user_id, refresh_trigger, view_mode, current_date, pathname, prev_view_mode):
    if view_mode != prev_view_mode:
        date_output = date.today().isoformat()
        prev_output = view_mode
    else:
        date_output = dash.no_update
        prev_output = view_mode

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
                    f"{entry['name']} ({entry['time']})",
                    id={'type': 'entry', 'entry_type': 'food',
                        'entry_id': entry['id']},
                    style=get_entry_style('food')
                )
                cards.append(card)
        elif entry_type == 'symptom':
            for entry in entry_list:
                card = html.Button(
                    f"{entry['name']} ({entry['time']})",
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
            entry_divs.append(html.Button(
                [
                    html.Span(entry['time'], style={
                        'fontWeight': 'bold', 'fontSize': '11px', 'color': '#1976d2', 'marginRight': '8px'}),
                    entry['name']
                ],
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
        # Add JS to scroll to current time on load
        # Use dcc.Interval to trigger scroll after render
        scroll_interval = None
        if is_today:
            scroll_interval = dcc.Interval(
                id='scroll-to-now-interval', interval=500, n_intervals=0, max_intervals=1)
        scroll_script = None
        if is_today:
            scroll_script = html.Script(f"""
                setTimeout(function() {{
                    var container = document.getElementById('day-hour-scroll');
                    if (container) {{
                        var scrollTo = {int(current_time_top) - 300};
                        if (scrollTo < 0) scrollTo = 0;
                        container.scrollTop = scrollTo;
                    }}
                }}, 500);
            """)
        the_div = html.Div([
            html.H4(base_date.strftime('%A, %B %d, %Y'),
                    style=day_title_style),
            html.Div(
                hour_labels + hour_grid_lines + now_line + entry_divs,
                style=container_style,
                id='day-hour-scroll'
            ),
            scroll_interval if scroll_interval else None,
            scroll_script if scroll_script else None
        ])
        return the_div, date_output, prev_output
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
                        cell_entries.append(html.Div(
                            [
                                html.Span(entry['time'], style={
                                    'fontWeight': 'bold', 'fontSize': '11px', 'color': '#1976d2', 'marginRight': '8px'}),
                                entry['name']
                            ],
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
        # Center scroll on current time row if this week
        table_style = {'width': '100%', 'borderCollapse': 'collapse',
                       'margin': '0 auto', 'tableLayout': 'fixed', 'position': 'relative'}
        if is_this_week:
            table_style['scrollMarginTop'] = f'{max(current_time_top - 4 * hour_height, 0)}px'
        # Add JS to scroll to current time on load for week view
        scroll_script = None
        if is_this_week:
            scroll_script = html.Script(f"""
                window.addEventListener('DOMContentLoaded', function() {{
                    var tables = document.getElementsByTagName('table');
                    if (tables.length > 0) {{
                        var table = tables[0];
                        var scrollTo = {int(current_time_top) - 300};
                        if (scrollTo < 0) scrollTo = 0;
                        table.parentElement.scrollTop = scrollTo;
                    }}
                }});
            """)
        the_div = html.Div([
            html.Table([
                html.Thead([header_row]),
                html.Tbody(now_line + grid_rows)
            ], style=table_style),
            scroll_script if scroll_script else None
        ])
        return the_div, date_output, prev_output
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
        month_title = html.H4(base_date.strftime('%B %Y'), style={
                              'textAlign': 'center', 'color': '#1976d2', 'margin': '8px 0 8px 0', 'fontWeight': 'bold'})

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
                        card = html.Button(
                            [
                                html.Span(meal_data['time'], style={
                                    'fontWeight': 'bold', 'fontSize': '11px', 'color': '#1976d2', 'marginRight': '8px'}),
                                f"{', '.join(food_names)}"
                            ],
                            id={'type': 'entry', 'entry_type': 'meal',
                                'entry_id': meal_id},
                            style=get_entry_style('meal')
                        )
                        cards.append(card)
            elif entry_type == 'food':
                for entry in entry_list:
                    card = html.Button(
                        [
                            html.Span(entry['time'], style={
                                'fontWeight': 'bold', 'fontSize': '11px', 'color': '#1976d2', 'marginRight': '8px'}),
                            entry['name']
                        ],
                        id={'type': 'entry', 'entry_type': 'food',
                            'entry_id': entry['id']},
                        style=get_entry_style('food')
                    )
                    cards.append(card)
            elif entry_type == 'symptom':
                for entry in entry_list:
                    card = html.Button(
                        [
                            html.Span(entry['time'], style={
                                'fontWeight': 'bold', 'fontSize': '11px', 'color': '#1976d2', 'marginRight': '8px'}),
                            entry['name']
                        ],
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
                            (
                                create_month_entry_cards(
                                    {k: v for k, v in entries.get(f"{year}-{month:02d}-{day:02d}", {}).get('meals', {}).items()
                                     if k is not None and str(k).strip() not in ('', 'None', 'none', 'null', '0') and k != 0},
                                    'meal'
                                ) if any(k is not None and str(k).strip() not in ('', 'None', 'none', 'null', '0') and k != 0 for k in entries.get(f"{year}-{month:02d}-{day:02d}", {}).get('meals', {}).keys()) else []
                            ) + create_month_entry_cards(
                                entries.get(
                                    f"{year}-{month:02d}-{day:02d}", {}).get('foods', []),
                                'food'
                            ) + create_month_entry_cards(
                                entries.get(
                                    f"{year}-{month:02d}-{day:02d}", {}).get('symptoms', []),
                                'symptom'
                            ), style={'display': 'flex', 'flexDirection': 'column', 'gap': '2px'}) if day != 0 else ""
                    ], style=get_td_style(day)) for day in week
                ]) for week in cal
            ])
        ], style={'width': '80%', 'borderCollapse': 'collapse', 'margin': '0 auto', 'tableLayout': 'fixed'})
        the_div = html.Div([
            month_title,
            month_table
        ])
        return the_div, date_output, prev_output


@callback(
    Output('entry-modal', 'style'),
    Output('entry-details', 'children'),
    Output('calendar-refresh', 'data', allow_duplicate=True),
    Output('modal-close-store', 'data'),
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
        return {'display': 'none'}, "", refresh_data

    trigger_id = ctx.triggered[0]['prop_id']

    if 'modal-close-btn' in trigger_id and close_clicks > 0:
        # Only hide the modal, do not refresh the calendar
        return {'display': 'none'}, "", refresh_data, (modal_close_data or 0) + 1

    # Check if any entry button was clicked and modal is not already open
    filtered_clicks = [click for click in (
        entry_clicks or []) if click is not None]
    if not filtered_clicks or not any(click and click == max(filtered_clicks) for click in filtered_clicks):
        return current_style, "", refresh_data, modal_close_data

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
                            SELECT f.description, fle.time, fle.notes
                            FROM "foodlogentry" fle
                            JOIN "food" f ON fle.fdc_id = f.fdc_id
                            WHERE fle.meal_id = %s
                            ORDER BY fle.time
                        ''', conn, params=(meal_id_str,))
                        if not foods_df.empty:
                            food_list = [html.Li(
                                f"{row['description']} ({row['time']}) - Notes: {row['notes'] or 'None'}") for _, row in foods_df.iterrows()]
                            food_names = ', '.join(
                                foods_df['description'].tolist())
                            details = html.Div([
                                html.H4(f"Meal: {food_names}"),
                                html.H5("Foods in this meal:"),
                                html.Ul(food_list),
                                html.Button('Delete', id={'type': 'modal-delete-entry', 'entry_type': 'meal', 'entry_id': entry_id}, n_clicks=0, style={
                                    'marginTop': '10px', 'backgroundColor': 'red', 'color': 'white'})
                            ])
                        else:
                            details = "Meal not found"
                elif entry_type == 'symptom':
                    df = pd.read_sql_query('''
                        SELECT s.name, sle.time, sle.severity, sle.notes
                        FROM "symptomlogentry" sle
                        JOIN "symptom" s ON sle.symptom_id = s.id
                        WHERE sle.id = %s
                    ''', conn, params=(entry_id,))
                    if not df.empty:
                        row = df.iloc[0]
                        details = html.Div([
                            html.H4("Symptom Entry Details"),
                            html.P(f"Symptom: {row['name']}"),
                            html.P(f"Time: {row['time']}"),
                            html.P(f"Severity: {row['severity']}/10"),
                            html.P(f"Notes: {row['notes'] or 'None'}"),
                            html.Button('Delete', id={'type': 'modal-delete-entry', 'entry_type': 'symptom', 'entry_id': entry_id},
                                        n_clicks=0, style={'marginTop': '10px', 'backgroundColor': 'red', 'color': 'white'})
                        ])
                    else:
                        details = "Entry not found"
                conn.close()
                return {'display': 'block', 'position': 'fixed', 'zIndex': 1000, 'left': 0, 'top': 0, 'width': '100%', 'height': '100%', 'backgroundColor': 'rgba(0,0,0,0.4)'}, details, refresh_data, modal_close_data
            except Exception as e:
                return current_style, f"Error: {e}", refresh_data, modal_close_data

    return current_style, "", refresh_data, modal_close_data


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
    if entry_type == 'meal':
        conn.execute(
            'DELETE FROM foodlogentry WHERE meal_id = %s AND daily_log_id IN (SELECT id FROM dailylog WHERE user_id = %s)', (entry_id, user_id))
    elif entry_type == 'food':
        conn.execute(
            'DELETE FROM foodlogentry WHERE id = %s AND daily_log_id IN (SELECT id FROM dailylog WHERE user_id = %s)', (entry_id, user_id))
    elif entry_type == 'symptom':
        conn.execute(
            'DELETE FROM symptomlogentry WHERE id = %s AND daily_log_id IN (SELECT id FROM dailylog WHERE user_id = %s)', (entry_id, user_id))
    conn.commit()
    conn.close()
    return {'display': 'none'}, (current_refresh or 0) + 1

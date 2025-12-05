import dash
from dash import html, dcc, Input, Output, State, callback
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import plotly.graph_objects as go
import plotly.express as px
from scipy import stats
from backend.utils import get_db_connection

dash.register_page(__name__, path='/analysis', order=4)


layout = html.Div([
    html.Div([
        html.H2("Health Analysis Dashboard", style={
                'color': '#1976d2', 'marginBottom': '24px'}),

        # View selector
        html.Div([
            dcc.RadioItems(
                id='analysis-view-mode',
                options=[
                    {'label': 'Overview', 'value': 'overview'},
                    {'label': 'Symptom Analysis', 'value': 'symptom'}
                ],
                value='overview',
                inline=True,
                style={'marginBottom': '20px'},
                labelStyle={'display': 'inline-block', 'marginRight': '24px'}
            )
        ]),

        # Symptom selector (only shown in symptom view)
        html.Div([
            html.Label("Select Symptom to Analyze:", style={
                       'fontWeight': 'bold', 'marginBottom': '8px'}),
            dcc.Dropdown(
                id='analysis-symptom',
                placeholder='Choose a symptom...',
                style={'marginBottom': '20px'}
            )
        ], id='symptom-selector-container', style={'display': 'none'}),

        # Analysis results container with loading spinner
        dcc.Loading(
            id='loading-analysis',
            type='circle',
            color='#1976d2',
            children=html.Div(id='analysis-content',
                              style={'marginTop': '20px'})
        )
    ], style={'maxWidth': '1400px', 'margin': '0 auto', 'padding': '24px'})
])


@callback(
    Output('symptom-selector-container', 'style'),
    Input('analysis-view-mode', 'value')
)
def toggle_symptom_selector(view_mode):
    """Show/hide symptom selector based on view mode"""
    if view_mode == 'symptom':
        return {'display': 'block', 'marginBottom': '20px'}
    return {'display': 'none'}


@callback(
    Output('analysis-symptom', 'options'),
    Input('current-user-id', 'data')
)
def populate_symptoms(user_id):
    """Populate symptom dropdown with symptoms user has experienced"""
    if not user_id:
        return []

    conn = get_db_connection()
    df = pd.read_sql_query('''
        SELECT DISTINCT s.name 
        FROM "symptom" s
        JOIN "symptomlogentry" sle ON s.id = sle.symptom_id
        JOIN "dailylog" dl ON sle.daily_log_id = dl.id
        WHERE dl.user_id = %s
        ORDER BY s.name
    ''', conn, params=(user_id,))
    conn.close()

    return [{'label': name, 'value': name} for name in df['name'].tolist()]


@callback(
    Output('analysis-content', 'children'),
    Input('analysis-view-mode', 'value'),
    Input('analysis-symptom', 'value'),
    State('current-user-id', 'data')
)
def render_analysis(view_mode, symptom_name, user_id):
    """Render either overview or symptom-specific analysis"""
    if not user_id:
        return html.Div("Please log in to view analysis.", style={'textAlign': 'center', 'padding': '40px', 'color': '#666'})

    if view_mode == 'overview':
        return render_overview(user_id)
    elif view_mode == 'symptom' and symptom_name:
        return render_symptom_analysis(user_id, symptom_name)
    elif view_mode == 'symptom':
        return html.Div("Please select a symptom to analyze.", style={'textAlign': 'center', 'padding': '40px', 'color': '#666'})

    return html.Div()


def render_overview(user_id):
    """Render overview dashboard with general health statistics"""
    conn = get_db_connection()

    # Get total counts
    total_meals = pd.read_sql_query('''
        SELECT COUNT(DISTINCT meal_id) as count
        FROM "foodlogentry" fle
        JOIN "dailylog" dl ON fle.daily_log_id = dl.id
        WHERE dl.user_id = %s AND fle.meal_id IS NOT NULL
    ''', conn, params=(user_id,))['count'].iloc[0]

    total_symptoms = pd.read_sql_query('''
        SELECT COUNT(*) as count
        FROM "symptomlogentry" sle
        JOIN "dailylog" dl ON sle.daily_log_id = dl.id
        WHERE dl.user_id = %s
    ''', conn, params=(user_id,))['count'].iloc[0]

    # Symptom frequency over time
    symptom_timeline = pd.read_sql_query('''
        SELECT dl.date, s.name, sle.severity
        FROM "symptomlogentry" sle
        JOIN "dailylog" dl ON sle.daily_log_id = dl.id
        JOIN "symptom" s ON sle.symptom_id = s.id
        WHERE dl.user_id = %s
        ORDER BY dl.date
    ''', conn, params=(user_id,))

    # Add color mapping for severity (orange to red gradient)
    if not symptom_timeline.empty:
        # Normalize severity to 0-1 range for color mapping
        min_sev = symptom_timeline['severity'].min()
        max_sev = symptom_timeline['severity'].max()
        if max_sev > min_sev:
            symptom_timeline['color_val'] = (
                symptom_timeline['severity'] - min_sev) / (max_sev - min_sev)
        else:
            symptom_timeline['color_val'] = 0.5

    # Most common symptoms
    common_symptoms = pd.read_sql_query('''
        SELECT s.name, COUNT(*) as count, AVG(sle.severity) as avg_severity
        FROM "symptomlogentry" sle
        JOIN "symptom" s ON sle.symptom_id = s.id
        JOIN "dailylog" dl ON sle.daily_log_id = dl.id
        WHERE dl.user_id = %s
        GROUP BY s.name
        ORDER BY count DESC
        LIMIT 10
    ''', conn, params=(user_id,))

    # Most consumed ingredients
    top_ingredients = pd.read_sql_query('''
        SELECT i.ingredient, COUNT(*) as count
        FROM "ingredient" i
        JOIN "foodlogentry" fle ON i.fdc_id = fle.fdc_id
        JOIN "dailylog" dl ON fle.daily_log_id = dl.id
        WHERE dl.user_id = %s
        GROUP BY i.ingredient
        ORDER BY count DESC
        LIMIT 15
    ''', conn, params=(user_id,))

    # Meals per day trend
    meals_per_day = pd.read_sql_query('''
        SELECT dl.date, COUNT(DISTINCT fle.meal_id) as meal_count
        FROM "dailylog" dl
        LEFT JOIN "foodlogentry" fle ON dl.id = fle.daily_log_id AND fle.meal_id IS NOT NULL
        WHERE dl.user_id = %s
        GROUP BY dl.date
        ORDER BY dl.date
    ''', conn, params=(user_id,))

    conn.close()

    # Create visualizations
    graphs = []

    # Summary stats
    graphs.append(html.Div([
        html.Div([
            html.H3(str(int(total_meals)), style={
                    'fontSize': '48px', 'margin': '0', 'color': '#1976d2'}),
            html.P("Total Meals Logged", style={
                   'color': '#666', 'margin': '0'})
        ], style={'textAlign': 'center', 'padding': '20px', 'backgroundColor': 'white', 'borderRadius': '8px', 'boxShadow': '0 2px 4px rgba(0,0,0,0.1)', 'flex': '1', 'marginRight': '16px'}),

        html.Div([
            html.H3(str(int(total_symptoms)), style={
                    'fontSize': '48px', 'margin': '0', 'color': '#ef5350'}),
            html.P("Total Symptoms Logged", style={
                   'color': '#666', 'margin': '0'})
        ], style={'textAlign': 'center', 'padding': '20px', 'backgroundColor': 'white', 'borderRadius': '8px', 'boxShadow': '0 2px 4px rgba(0,0,0,0.1)', 'flex': '1'})
    ], style={'display': 'flex', 'marginBottom': '24px'}))

    # Symptom timeline
    if not symptom_timeline.empty:
        fig_timeline = px.scatter(symptom_timeline, x='date', y='name',
                                  color='severity',
                                  color_continuous_scale=[[0, "#ffb94f"], [
                                      0.5, "#ff7f15"], [1, "#a70000"]],
                                  title='Symptom Timeline',
                                  labels={'date': 'Date', 'name': 'Symptom', 'severity': 'Severity'})
        fig_timeline.update_layout(height=400)
        fig_timeline.update_traces(marker=dict(
            size=20, line=dict(width=1, color='white')))
        graphs.append(html.Div([
            dcc.Graph(figure=fig_timeline)
        ], style={'backgroundColor': 'white', 'borderRadius': '8px', 'boxShadow': '0 2px 4px rgba(0,0,0,0.1)', 'padding': '16px', 'marginBottom': '24px'}))

    # Most common symptoms
    if not common_symptoms.empty:
        fig_symptoms = go.Figure(data=[
            go.Bar(x=common_symptoms['name'], y=common_symptoms['count'],
                   marker_color='#ef5350',
                   text=common_symptoms['count'],
                   textposition='outside')
        ])
        fig_symptoms.update_layout(title='Most Common Symptoms',
                                   xaxis_title='Symptom',
                                   yaxis_title='Occurrences',
                                   height=400)
        graphs.append(html.Div([
            dcc.Graph(figure=fig_symptoms)
        ], style={'backgroundColor': 'white', 'borderRadius': '8px', 'boxShadow': '0 2px 4px rgba(0,0,0,0.1)', 'padding': '16px', 'marginBottom': '24px'}))

    # Top ingredients
    if not top_ingredients.empty:
        fig_ingredients = go.Figure(data=[
            go.Bar(x=top_ingredients['ingredient'], y=top_ingredients['count'],
                   marker_color='#64b5f6',
                   text=top_ingredients['count'],
                   textposition='outside')
        ])
        fig_ingredients.update_layout(title='Most Consumed Ingredients',
                                      xaxis_title='Ingredient',
                                      yaxis_title='Times Consumed',
                                      height=400)
        graphs.append(html.Div([
            dcc.Graph(figure=fig_ingredients)
        ], style={'backgroundColor': 'white', 'borderRadius': '8px', 'boxShadow': '0 2px 4px rgba(0,0,0,0.1)', 'padding': '16px', 'marginBottom': '24px'}))

    # Meals per day trend
    if not meals_per_day.empty:
        fig_meals = px.line(meals_per_day, x='date', y='meal_count',
                            title='Meals Per Day Over Time',
                            labels={'date': 'Date', 'meal_count': 'Number of Meals'})
        fig_meals.update_traces(line_color='#64b5f6')
        fig_meals.update_layout(height=400)
        graphs.append(html.Div([
            dcc.Graph(figure=fig_meals)
        ], style={'backgroundColor': 'white', 'borderRadius': '8px', 'boxShadow': '0 2px 4px rgba(0,0,0,0.1)', 'padding': '16px', 'marginBottom': '24px'}))

    if not graphs:
        return html.Div("No data available yet. Start logging meals and symptoms!",
                        style={'textAlign': 'center', 'padding': '40px', 'color': '#666'})

    return html.Div(graphs)


def render_symptom_analysis(user_id, symptom_name):
    """Render detailed analysis for a specific symptom - analyzing ingredients consumed 24h before each symptom"""
    from backend.cache import get_user_data
    
    # Get cached user data (fast!)
    user_data = get_user_data(user_id)
    
    # Filter symptom log entries for this specific symptom
    symptom_logs = user_data['symptom_log_entries'][
        user_data['symptom_log_entries']['symptom_name'] == symptom_name
    ].copy()

    if symptom_logs.empty:
        return html.Div("No occurrences of this symptom found. Log symptoms to see analysis.",
                        style={'textAlign': 'center', 'padding': '40px', 'color': '#666'})

    # Get all food log entries, ingredients, and subingredients from cache
    food_entries = user_data['food_log_entries'].copy()
    foods = user_data['foods'].copy()
    ingredients = user_data['ingredients'].copy()
    subingredients = user_data['subingredients'].copy()
    
    # Create datetime column for food entries
    food_entries['datetime'] = pd.to_datetime(food_entries['date'].astype(str) + ' ' + food_entries['time'].astype(str))
    
    # Merge to get food descriptions and ingredients
    food_entries = food_entries.merge(foods[['fdc_id', 'description']], on='fdc_id', how='left')
    ingredients_with_food = ingredients.merge(foods[['fdc_id', 'description']], on='fdc_id', how='left')
    subingredients_with_food = subingredients.merge(ingredients[['id', 'fdc_id']], left_on='ingredient_id', right_on='id', how='left')
    subingredients_with_food = subingredients_with_food.merge(foods[['fdc_id', 'description']], on='fdc_id', how='left')
    
    # Count how many times each ingredient appeared before symptoms
    ingredient_frequency = {}
    symptom_details = []
    food_frequency = {}

    for _, symptom_log in symptom_logs.iterrows():
        symptom_datetime = pd.to_datetime(str(symptom_log['date']) + ' ' + str(symptom_log['time']))
        start_time = symptom_datetime - timedelta(hours=24)

        # Filter food entries in 24h window
        foods_in_window = food_entries[
            (food_entries['datetime'] >= start_time) & 
            (food_entries['datetime'] < symptom_datetime)
        ]
        
        # Get unique fdc_ids consumed in window
        fdc_ids_in_window = foods_in_window['fdc_id'].unique()
        
        # Get ingredients for these foods
        ingredients_in_window = ingredients_with_food[
            ingredients_with_food['fdc_id'].isin(fdc_ids_in_window)
        ]
        
        # Get subingredients for these foods
        subingredients_in_window = subingredients_with_food[
            subingredients_with_food['fdc_id'].isin(fdc_ids_in_window)
        ]
        
        # Collect all ingredients and map to foods
        consumed_ingredients = set()
        ingredient_to_foods = {}
        
        for _, row in ingredients_in_window.iterrows():
            ing = row['ingredient']
            consumed_ingredients.add(ing)
            if ing not in ingredient_to_foods:
                ingredient_to_foods[ing] = set()
            ingredient_to_foods[ing].add(row['description'])
        
        for _, row in subingredients_in_window.iterrows():
            ing = row['sub_ingredient']
            consumed_ingredients.add(ing)
            if ing not in ingredient_to_foods:
                ingredient_to_foods[ing] = set()
            ingredient_to_foods[ing].add(row['description'])
        
        # Track food frequency
        for food_desc in foods_in_window['description'].unique():
            food_frequency[food_desc] = food_frequency.get(food_desc, 0) + 1
        
        # Update ingredient frequency count
        for ingredient in consumed_ingredients:
            ingredient_frequency[ingredient] = ingredient_frequency.get(ingredient, 0) + 1

        # Store details for this symptom occurrence
        symptom_details.append({
            'datetime': symptom_datetime,
            'date': symptom_log['date'],
            'time': symptom_log['time'],
            'severity': symptom_log['severity'],
            'notes': symptom_log['notes'],
            'ingredients': consumed_ingredients,
            'ingredient_to_foods': ingredient_to_foods
        })

    # Calculate statistics for each ingredient
    total_symptom_occurrences = len(symptom_logs)

    ingredient_stats = []
    for ingredient, frequency in ingredient_frequency.items():
        percentage = (frequency / total_symptom_occurrences) * 100

        ingredient_stats.append({
            'ingredient': ingredient,
            'times_before_symptom': frequency,
            'total_occurrences': total_symptom_occurrences,
            'percentage': percentage
        })

    # Initial dataframe (will be sorted after correlation calculation)
    ingredient_stats_df = pd.DataFrame(ingredient_stats)

    # Get total consumption count for ALL ingredients using cached data
    all_ingredient_consumption = {}

    if ingredient_frequency:
        # Merge ingredients with food entries to count total consumption
        # Rename id columns to avoid conflicts
        ingredients_merged = ingredients_with_food.merge(
            food_entries[['fdc_id', 'id']].rename(columns={'id': 'entry_id'}), 
            on='fdc_id', how='inner'
        )
        
        # Count occurrences for each ingredient
        ingredient_counts = ingredients_merged.groupby('ingredient')['entry_id'].nunique().to_dict()
        
        # Count occurrences for each subingredient
        subingredients_merged = subingredients_with_food.merge(
            food_entries[['fdc_id', 'id']].rename(columns={'id': 'entry_id'}), 
            on='fdc_id', how='inner'
        )
        subingredient_counts = subingredients_merged.groupby('sub_ingredient')['entry_id'].nunique().to_dict()
        
        # Combine counts
        for ingredient in ingredient_frequency.keys():
            total = ingredient_counts.get(ingredient, 0) + subingredient_counts.get(ingredient, 0)
            all_ingredient_consumption[ingredient] = max(total, ingredient_frequency[ingredient])

    # Add correlation metric (times before symptom / total times consumed)
    for i, row in ingredient_stats_df.iterrows():
        ingredient = row['ingredient']
        total_consumed = all_ingredient_consumption.get(
            ingredient, row['times_before_symptom'])
        correlation_rate = (row['times_before_symptom'] /
                            total_consumed * 100) if total_consumed > 0 else 0
        ingredient_stats_df.at[i, 'total_consumed'] = total_consumed
        ingredient_stats_df.at[i, 'correlation_rate'] = correlation_rate

    # Sort by correlation rate (highest correlation = most likely culprit)
    ingredient_stats_df = ingredient_stats_df.sort_values(
        'correlation_rate', ascending=False)

    # Calculate food culprits (foods ranked by how often they appeared before symptoms)
    food_culprits = []
    if food_frequency:
        # Count total consumption for each food using cached data
        food_consumption_counts = food_entries.groupby('description')['id'].nunique().to_dict()
        
        # Calculate correlation rates
        for food_name, freq in food_frequency.items():
            total_consumed = food_consumption_counts.get(food_name, freq)
            correlation_rate = (freq / total_consumed * 100) if total_consumed > 0 else 0

            food_culprits.append({
                'food': food_name,
                'times_before_symptom': freq,
                'total_consumed': total_consumed,
                'correlation_rate': correlation_rate
            })

    food_culprits_df = pd.DataFrame(food_culprits).sort_values(
        'correlation_rate', ascending=False).head(10) if food_culprits else pd.DataFrame()

    # Symptom timeline (already has datetime from cache)
    symptom_logs['datetime'] = pd.to_datetime(
        symptom_logs['date'].astype(str) + ' ' + symptom_logs['time'].astype(str))

    # Create visualizations
    graphs = []

    # Summary stats
    total_occurrences = len(symptom_logs)
    avg_severity = symptom_logs['severity'].mean(
    ) if not symptom_logs.empty else 0
    total_unique_ingredients = len(ingredient_frequency)

    graphs.append(html.Div([
        html.H3(f"Analysis: {symptom_name}", style={
                'color': '#1976d2', 'marginBottom': '24px'}),
        html.Div([
            html.Div([
                html.H3(str(total_occurrences), style={
                        'fontSize': '48px', 'margin': '0', 'color': '#ef5350'}),
                html.P("Total Occurrences", style={
                       'color': '#666', 'margin': '0'})
            ], style={'textAlign': 'center', 'padding': '20px', 'backgroundColor': 'white', 'borderRadius': '8px', 'boxShadow': '0 2px 4px rgba(0,0,0,0.1)', 'flex': '1', 'marginRight': '16px'}),

            html.Div([
                html.H3(f"{avg_severity:.1f}", style={
                        'fontSize': '48px', 'margin': '0', 'color': '#ef5350'}),
                html.P("Average Severity", style={
                       'color': '#666', 'margin': '0'})
            ], style={'textAlign': 'center', 'padding': '20px', 'backgroundColor': 'white', 'borderRadius': '8px', 'boxShadow': '0 2px 4px rgba(0,0,0,0.1)', 'flex': '1', 'marginRight': '16px'}),

            html.Div([
                html.H3(str(total_unique_ingredients), style={
                        'fontSize': '48px', 'margin': '0', 'color': '#ff9800'}),
                html.P("Unique Ingredients", style={
                       'color': '#666', 'margin': '0'})
            ], style={'textAlign': 'center', 'padding': '20px', 'backgroundColor': 'white', 'borderRadius': '8px', 'boxShadow': '0 2px 4px rgba(0,0,0,0.1)', 'flex': '1'})
        ], style={'display': 'flex', 'marginBottom': '24px'})
    ]))

    # Severity timeline
    if not symptom_logs.empty:
        # Sort by datetime for proper line chart
        symptom_logs_sorted = symptom_logs.sort_values('datetime')
        fig_severity = px.line(symptom_logs_sorted, x='datetime', y='severity',
                               title=f'{symptom_name} Severity Over Time',
                               labels={'datetime': 'Date',
                                       'severity': 'Severity'},
                               markers=True)
        fig_severity.update_traces(line_color='#ef5350', marker=dict(size=8))
        fig_severity.update_layout(height=400)
        graphs.append(html.Div([
            dcc.Graph(figure=fig_severity)
        ], style={'backgroundColor': 'white', 'borderRadius': '8px', 'boxShadow': '0 2px 4px rgba(0,0,0,0.1)', 'padding': '16px', 'marginBottom': '24px'}))

    # Top culprit foods
    if not food_culprits_df.empty:
        culprit_cards = []
        for idx, (_, row) in enumerate(food_culprits_df.iterrows(), 1):
            corr_color = '#d32f2f' if row['correlation_rate'] > 50 else '#ff5722' if row['correlation_rate'] > 25 else '#ff9800'
            culprit_cards.append(
                html.Div([
                    html.Div([
                        html.Span(f"#{idx}", style={
                                  'fontSize': '16px', 'fontWeight': 'bold', 'color': corr_color, 'marginRight': '8px'}),
                        html.Span(row['food'], style={
                                  'fontSize': '14px', 'fontWeight': '500', 'flex': '1'})
                    ], style={'display': 'flex', 'alignItems': 'center', 'marginBottom': '4px'}),
                    html.Div([
                        html.Span(f"Correlation: ", style={
                                  'fontSize': '12px', 'color': '#666'}),
                        html.Span(f"{row['correlation_rate']:.1f}%", style={
                                  'fontSize': '12px', 'fontWeight': 'bold', 'color': corr_color}),
                        html.Span(f" • Before symptom: {row['times_before_symptom']}/{row['total_consumed']} times", style={
                                  'fontSize': '12px', 'color': '#666', 'marginLeft': '8px'})
                    ])
                ], style={'padding': '12px', 'backgroundColor': '#f9f9f9', 'borderRadius': '4px', 'marginBottom': '8px', 'borderLeft': f'3px solid {corr_color}'})
            )

        graphs.append(html.Div([
            html.H4("Most Likely Culprit Foods", style={
                    'marginBottom': '12px', 'color': '#d32f2f'}),
            html.P("Foods ranked by correlation rate (how often consuming this food led to the symptom)",
                   style={'fontSize': '12px', 'color': '#666', 'marginBottom': '12px'}),
            html.Div(culprit_cards)
        ], style={'backgroundColor': 'white', 'borderRadius': '8px', 'boxShadow': '0 2px 4px rgba(0,0,0,0.1)', 'padding': '16px', 'marginBottom': '24px'}))

    # Ingredient frequency chart - show ALL ingredients consumed 24h before symptoms, sorted by frequency
    if not ingredient_stats_df.empty:
        # Sort by times_before_symptom (descending) to show most frequent first
        all_ingredients = ingredient_stats_df.sort_values(
            'times_before_symptom', ascending=False)

        fig_freq = go.Figure(data=[
            go.Bar(x=all_ingredients['ingredient'],
                   y=all_ingredients['times_before_symptom'],
                   marker_color='#ef5350',
                   text=all_ingredients['times_before_symptom'],
                   textposition='outside',
                   hovertemplate='<b>%{x}</b><br>' +
                                'Appeared before symptom: %{y} times<br>' +
                                'Out of %{customdata[0]} total occurrences<br>' +
                                'Percentage: %{customdata[1]:.1f}%<br>' +
                                'Total times consumed: %{customdata[2]}<br>' +
                                'Correlation rate: %{customdata[3]:.1f}%<extra></extra>',
                   customdata=all_ingredients[['total_occurrences', 'percentage', 'total_consumed', 'correlation_rate']].values)
        ])
        fig_freq.update_layout(
            title=f'All Ingredients Consumed 24h Before {symptom_name}',
            xaxis_title='Ingredient',
            yaxis_title='Times Appeared Before Symptom',
            # Dynamic height based on number of ingredients
            height=max(500, len(all_ingredients) * 20),
            xaxis={'tickangle': -45}
        )
        graphs.append(html.Div([
            dcc.Graph(figure=fig_freq),
            html.Div([
                html.P([
                    html.Strong("Analysis Window: "),
                    "Shows all ingredients consumed in the 24 hours before each symptom occurrence. ",
                    html.Br(),
                    html.Strong("Frequency Count: "),
                    "How many times each ingredient appeared before the symptom. ",
                    html.Br(),
                    html.Strong("Correlation Rate: "),
                    "(Times before symptom / Total times consumed) × 100. Higher percentage means stronger association."
                ], style={'fontSize': '12px', 'color': '#666', 'fontStyle': 'italic', 'marginTop': '8px'})
            ])
        ], style={'backgroundColor': 'white', 'borderRadius': '8px', 'boxShadow': '0 2px 4px rgba(0,0,0,0.1)', 'padding': '16px', 'marginBottom': '24px'}))

    # Ingredient statistics table
    if not ingredient_stats_df.empty:
        top_stats = ingredient_stats_df.head(30)

        table_rows = [
            html.Tr([
                html.Th("Ingredient", style={
                        'textAlign': 'left', 'padding': '8px', 'borderBottom': '2px solid #ddd'}),
                html.Th("Before Symptom", style={
                        'textAlign': 'left', 'padding': '8px', 'borderBottom': '2px solid #ddd'}),
                html.Th("Total Consumed", style={
                        'textAlign': 'left', 'padding': '8px', 'borderBottom': '2px solid #ddd'}),
                html.Th("Correlation %", style={
                        'textAlign': 'left', 'padding': '8px', 'borderBottom': '2px solid #ddd'}),
                html.Th("Frequency %", style={
                        'textAlign': 'left', 'padding': '8px', 'borderBottom': '2px solid #ddd'})
            ])
        ]

        for _, row in top_stats.iterrows():
            corr_color = '#d32f2f' if row['correlation_rate'] > 50 else '#ff9800' if row['correlation_rate'] > 25 else '#666'
            table_rows.append(
                html.Tr([
                    html.Td(row['ingredient'], style={
                            'padding': '8px', 'borderBottom': '1px solid #eee', 'maxWidth': '200px'}),
                    html.Td(f"{row['times_before_symptom']}/{row['total_occurrences']}",
                            style={'padding': '8px', 'borderBottom': '1px solid #eee'}),
                    html.Td(str(int(row['total_consumed'])), style={
                            'padding': '8px', 'borderBottom': '1px solid #eee'}),
                    html.Td(f"{row['correlation_rate']:.1f}%", style={
                            'padding': '8px', 'borderBottom': '1px solid #eee', 'color': corr_color, 'fontWeight': 'bold'}),
                    html.Td(f"{row['percentage']:.1f}%", style={
                            'padding': '8px', 'borderBottom': '1px solid #eee'})
                ])
            )

        graphs.append(html.Div([
            html.H4("Ingredient Statistics", style={'marginBottom': '16px'}),
            html.P([
                html.Strong("Before Symptom: "),
                "How many times ingredient appeared in 24h before symptom out of total symptom occurrences. ",
                html.Strong("Correlation %: "),
                "Percentage of times consuming this ingredient led to symptom. ",
                html.Strong("Frequency %: "),
                "How often this ingredient appeared before symptoms."
            ], style={'fontSize': '12px', 'color': '#666', 'marginBottom': '12px'}),
            html.Table(table_rows, style={
                       'width': '100%', 'borderCollapse': 'collapse', 'fontSize': '13px'})
        ], style={'backgroundColor': 'white', 'borderRadius': '8px', 'boxShadow': '0 2px 4px rgba(0,0,0,0.1)', 'padding': '16px', 'marginBottom': '24px'}))

    # Recent occurrences with ingredients and foods consumed before each
    if symptom_details:
        recent_details = symptom_details[:10]

        occurrence_cards = []
        for detail in recent_details:
            # Group ingredients by food
            food_to_ingredients = {}
            for ingredient in detail['ingredients']:
                foods = detail['ingredient_to_foods'].get(ingredient, set())
                for food in foods:
                    if food not in food_to_ingredients:
                        food_to_ingredients[food] = []
                    food_to_ingredients[food].append(ingredient)

            # Build food list with ingredients
            food_items = []
            for food_name in sorted(food_to_ingredients.keys()):
                ingredients_list = ', '.join(
                    sorted(food_to_ingredients[food_name]))
                food_items.append(html.Div([
                    html.Strong(food_name, style={
                                'fontSize': '12px', 'color': '#1976d2'}),
                    html.Span(f": {ingredients_list}", style={
                              'fontSize': '12px', 'color': '#666'})
                ], style={'marginBottom': '4px'}))

            food_display = food_items if food_items else html.Span(
                'No foods logged in 24h before', style={'fontSize': '12px', 'color': '#666'})

            occurrence_cards.append(
                html.Div([
                    html.Div([
                        html.Strong(f"{detail['date']} at {detail['time']}", style={
                                    'color': '#1976d2', 'fontSize': '14px'}),
                        html.Span(f" • Severity: {detail['severity']}", style={
                                  'color': '#ef5350', 'marginLeft': '12px', 'fontSize': '13px'})
                    ], style={'marginBottom': '8px'}),
                    html.Div([
                        html.Strong("Foods consumed (24h before):", style={
                                    'fontSize': '12px', 'marginBottom': '4px', 'display': 'block'}),
                        html.Div(food_display, style={'marginLeft': '8px'})
                    ], style={'marginBottom': '4px'}),
                    html.Div([
                        html.Strong("Notes: ", style={'fontSize': '12px'}),
                        html.Span(detail['notes'] if pd.notna(detail['notes']) and detail['notes'] else 'None',
                                  style={'fontSize': '12px', 'color': '#666', 'fontStyle': 'italic'})
                    ]) if detail['notes'] else html.Div()
                ], style={'padding': '12px', 'marginBottom': '8px', 'backgroundColor': '#f9f9f9', 'borderRadius': '4px', 'borderLeft': '3px solid #ef5350'})
            )

        graphs.append(html.Div([
            html.H4("Recent Occurrences with Ingredients Consumed",
                    style={'marginBottom': '16px'}),
            html.Div(occurrence_cards)
        ], style={'backgroundColor': 'white', 'borderRadius': '8px', 'boxShadow': '0 2px 4px rgba(0,0,0,0.1)', 'padding': '16px', 'marginBottom': '24px'}))

    return html.Div(graphs)

#!/usr/bin/env python3
"""
Aviation Safety Data Dashboard with Enhanced Details
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import glob
import os

# Chart type configurations for custom chart builder
CHART_TYPES = {
    'bar': {'label': 'Bar Chart', 'needs_y': True, 'supports_orientation': True},
    'line': {'label': 'Line Chart', 'needs_y': True, 'supports_markers': True},
    'scatter': {'label': 'Scatter Plot', 'needs_y': True, 'supports_size': True},
    'pie': {'label': 'Pie Chart', 'needs_y': True, 'y_label': 'Values'},
    'histogram': {'label': 'Histogram', 'needs_y': False},
    'box': {'label': 'Box Plot', 'needs_y': True},
    'violin': {'label': 'Violin Plot', 'needs_y': True},
    'area': {'label': 'Area Chart', 'needs_y': True},
    'funnel': {'label': 'Funnel Chart', 'needs_y': True},
    'sunburst': {'label': 'Sunburst Chart', 'needs_y': True, 'hierarchical': True},
    'treemap': {'label': 'Treemap', 'needs_y': True, 'hierarchical': True},
}

AGGREGATIONS = ['count', 'sum', 'mean', 'median', 'min', 'max']

# Page configuration
st.set_page_config(
    page_title="Turboprop Aircraft Safety Data Dashboard",
    page_icon="✈️",
    layout="wide"
)


@st.cache_data
def load_data():
    """Load and preprocess data"""
    # Look for enhanced CSV files first
    csv_files = glob.glob('aviation_safety_enhanced_*.csv')

    if not csv_files:
        # Fall back to basic files
        csv_files = glob.glob('aviation_safety_data_*.csv')

    if not csv_files:
        st.error("No data files found. Please run the scraper first.")
        return None, False

    latest_file = max(csv_files, key=os.path.getctime)
    is_enhanced = 'enhanced' in latest_file
    st.sidebar.success(f"Data file: {os.path.basename(latest_file)}")
    if is_enhanced:
        st.sidebar.info("✓ Enhanced data with detailed information")

    df = pd.read_csv(latest_file)

    # Date preprocessing
    df['date_parsed'] = pd.to_datetime(df['date'], format='%d %b %Y', errors='coerce')
    df['year'] = df['date_parsed'].dt.year
    df['month'] = df['date_parsed'].dt.month

    # Convert fatalities to numeric
    df['fatalities_num'] = pd.to_numeric(df['fatalities'], errors='coerce').fillna(0)

    # Fatal accident flag
    df['is_fatal'] = df['fatalities_num'] > 0

    # Damage mapping (English)
    damage_map = {
        'w/o': 'Written off',
        'sub': 'Substantial',
        'min': 'Minor',
        'non': 'None',
        '': 'Unknown'
    }
    df['damage_full'] = df['damage'].map(damage_map).fillna('Unknown')

    return df, is_enhanced


def get_numeric_fields(df, is_enhanced):
    """Get list of numeric fields available for charts"""
    base_numeric = ['year', 'month', 'fatalities_num']
    return base_numeric


def get_categorical_fields(df, is_enhanced):
    """Get list of categorical fields available for charts"""
    base_categorical = ['type', 'aircraft_category', 'operator', 'location',
                        'damage', 'damage_full', 'type_code']

    if is_enhanced:
        enhanced_categorical = ['phase', 'nature', 'departure_airport',
                                'destination_airport', 'category', 'engine_model']
        # Filter out fields that don't exist or are all null
        enhanced_categorical = [f for f in enhanced_categorical if f in df.columns and df[f].notna().any()]
        return base_categorical + enhanced_categorical

    return base_categorical


def prepare_chart_data(df, config):
    """Prepare data with aggregations for chart generation"""
    try:
        x_field = config['x_field']
        y_field = config.get('y_field')
        aggregation = config.get('aggregation', 'count')

        # If no aggregation needed (e.g., scatter with raw data)
        if aggregation == 'none' or config['chart_type'] in ['scatter', 'histogram']:
            return df

        # Apply aggregation
        if aggregation == 'count':
            result = df.groupby(x_field).size().reset_index(name='count')
            config['y_field'] = 'count'
            return result
        elif y_field and aggregation in ['sum', 'mean', 'median', 'min', 'max']:
            if aggregation == 'median':
                result = df.groupby(x_field)[y_field].median().reset_index()
            else:
                result = df.groupby(x_field)[y_field].agg(aggregation).reset_index()
            return result
        else:
            return df

    except Exception as e:
        st.error(f"Data preparation error: {str(e)}")
        return None


def generate_chart(df, config):
    """Generate Plotly chart from configuration"""
    try:
        if df is None or len(df) == 0:
            st.warning("No data available for this chart configuration.")
            return None

        # Get the Plotly Express function dynamically
        chart_type = config['chart_type']
        px_func = getattr(px, chart_type)

        # Build parameters
        params = {'title': config['title']}

        # Handle different chart type parameter requirements
        if chart_type in ['pie', 'sunburst', 'treemap']:
            params['values'] = config.get('y_field', 'count')
            params['names'] = config['x_field']
            if chart_type in ['sunburst', 'treemap']:
                # For hierarchical charts, use path parameter
                params['path'] = [config['x_field']]
                del params['names']
        else:
            params['x'] = config['x_field']
            if config.get('y_field'):
                params['y'] = config['y_field']

        # Add optional parameters
        if config.get('color_field'):
            params['color'] = config['color_field']

        if config.get('orientation'):
            params['orientation'] = config['orientation']

        # Generate chart
        fig = px_func(df, **params)
        return fig

    except Exception as e:
        st.error(f"Chart generation error: {str(e)}")
        return None


def render_chart_builder(df, is_enhanced):
    """Render the chart builder UI in sidebar"""
    with st.sidebar.expander("📊 Custom Chart Builder"):
        st.markdown("Create your own charts")

        # Chart title
        chart_title = st.text_input("Chart Title", value="My Custom Chart")

        # Chart type selection
        chart_type = st.selectbox(
            "Chart Type",
            options=list(CHART_TYPES.keys()),
            format_func=lambda x: CHART_TYPES[x]['label']
        )

        chart_config = CHART_TYPES[chart_type]

        # Get available fields
        numeric_fields = get_numeric_fields(df, is_enhanced)
        categorical_fields = get_categorical_fields(df, is_enhanced)
        all_fields = categorical_fields + numeric_fields

        # X-axis field
        x_field = st.selectbox("X-axis Field", options=all_fields)

        # Y-axis field (conditional based on chart type)
        y_field = None
        if chart_config['needs_y']:
            y_label = chart_config.get('y_label', 'Y-axis Field')
            y_field = st.selectbox(y_label, options=numeric_fields)

        # Aggregation (for categorical X with numeric Y)
        aggregation = 'count'
        if x_field in categorical_fields and y_field:
            aggregation = st.selectbox("Aggregation", options=AGGREGATIONS)
        elif chart_type == 'histogram':
            aggregation = 'none'

        # Optional: Color field
        color_field = None
        show_advanced = st.checkbox("Show Advanced Options", value=False)

        if show_advanced:
            st.markdown("**Advanced Options**")
            color_field = st.selectbox(
                "Color by (optional)",
                options=['None'] + categorical_fields,
                index=0
            )
            if color_field == 'None':
                color_field = None

            # Orientation for bar charts
            orientation = None
            if chart_config.get('supports_orientation'):
                orientation = st.radio("Orientation", options=['Horizontal', 'Vertical'], horizontal=True)
                orientation = 'h' if orientation == 'Horizontal' else 'v'
        else:
            orientation = None

        # Add chart button
        if st.button("Add Chart ➕", use_container_width=True):
            # Create chart configuration
            new_chart = {
                'id': f"chart_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}",
                'title': chart_title,
                'chart_type': chart_type,
                'x_field': x_field,
                'y_field': y_field,
                'aggregation': aggregation,
                'color_field': color_field,
                'orientation': orientation,
            }

            # Add to session state
            st.session_state.custom_charts.append(new_chart)
            st.success("✓ Chart added successfully!")
            st.rerun()


def render_custom_charts(filtered_df):
    """Render all custom charts in the main area"""
    st.subheader("📊 Your Custom Charts")

    if not st.session_state.custom_charts:
        st.info("No custom charts yet. Use the Chart Builder in the sidebar to create one!")
        return

    # Render each chart
    for idx, chart_config in enumerate(st.session_state.custom_charts):
        col1, col2 = st.columns([5, 1])

        with col1:
            # Prepare data
            chart_data = prepare_chart_data(filtered_df.copy(), chart_config.copy())

            # Generate and display chart
            if chart_data is not None and len(chart_data) > 0:
                fig = generate_chart(chart_data, chart_config)
                if fig:
                    st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning(f"No data available for chart: {chart_config['title']}")

        with col2:
            # Delete button
            st.write("")  # Spacing
            st.write("")  # Spacing
            if st.button(f"🗑️ Delete", key=f"delete_{chart_config['id']}"):
                st.session_state.custom_charts.pop(idx)
                st.rerun()

        # Add separator between charts
        if idx < len(st.session_state.custom_charts) - 1:
            st.markdown("---")


def main():
    st.title("✈️ Turboprop Aircraft Safety Data Dashboard")
    st.markdown("---")

    # Load data
    result = load_data()
    if result is None:
        return
    df, is_enhanced = result

    # Initialize session state for custom charts
    if 'custom_charts' not in st.session_state:
        st.session_state.custom_charts = []

    # Sidebar filters
    st.sidebar.header("Filters")

    # Year range filter
    min_year = int(df['year'].min())
    max_year = int(df['year'].max())
    year_range = st.sidebar.slider(
        "Year Range",
        min_value=min_year,
        max_value=max_year,
        value=(min_year, max_year)
    )

    # Aircraft type filter
    aircraft_types = ['All'] + sorted(df['aircraft_category'].unique().tolist())
    selected_aircraft = st.sidebar.multiselect(
        "Aircraft Type",
        options=aircraft_types,
        default=['All']
    )

    # Fatal accidents only
    show_fatal_only = st.sidebar.checkbox("Show fatal accidents only", value=False)

    # Phase filter (if enhanced data)
    selected_phases = []
    if is_enhanced and 'phase' in df.columns:
        phases = ['All'] + sorted([p for p in df['phase'].dropna().unique() if p])
        selected_phases = st.sidebar.multiselect(
            "Flight Phase",
            options=phases,
            default=['All']
        )

    # Custom Chart Builder
    st.sidebar.markdown("---")
    render_chart_builder(df, is_enhanced)

    # Apply filters
    filtered_df = df[
        (df['year'] >= year_range[0]) &
        (df['year'] <= year_range[1])
    ]

    if 'All' not in selected_aircraft and selected_aircraft:
        filtered_df = filtered_df[filtered_df['aircraft_category'].isin(selected_aircraft)]

    if show_fatal_only:
        filtered_df = filtered_df[filtered_df['is_fatal']]

    if is_enhanced and 'All' not in selected_phases and selected_phases:
        filtered_df = filtered_df[filtered_df['phase'].isin(selected_phases)]

    # Key Performance Indicators (KPI)
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Total Accidents", f"{len(filtered_df):,}")

    with col2:
        total_fatalities = int(filtered_df['fatalities_num'].sum())
        st.metric("Total Fatalities", f"{total_fatalities:,}")

    with col3:
        fatal_accidents = len(filtered_df[filtered_df['is_fatal']])
        fatal_rate = (fatal_accidents / len(filtered_df) * 100) if len(filtered_df) > 0 else 0
        st.metric("Fatal Accidents", f"{fatal_accidents:,} ({fatal_rate:.1f}%)")

    with col4:
        avg_fatalities = filtered_df['fatalities_num'].mean()
        st.metric("Avg Fatalities", f"{avg_fatalities:.2f}")

    st.markdown("---")

    # Chart 1: Yearly trends
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📊 Accidents by Year")
        yearly_counts = filtered_df.groupby('year').size().reset_index(name='count')
        fig1 = px.line(
            yearly_counts,
            x='year',
            y='count',
            title='Annual Accident Count',
            labels={'year': 'Year', 'count': 'Accidents'}
        )
        fig1.update_traces(mode='lines+markers')
        st.plotly_chart(fig1, use_container_width=True)

    with col2:
        st.subheader("📊 Fatalities by Year")
        yearly_fatalities = filtered_df.groupby('year')['fatalities_num'].sum().reset_index()
        fig2 = px.bar(
            yearly_fatalities,
            x='year',
            y='fatalities_num',
            title='Annual Total Fatalities',
            labels={'year': 'Year', 'fatalities_num': 'Fatalities'}
        )
        st.plotly_chart(fig2, use_container_width=True)

    # Chart 2: Aircraft type analysis
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("🛩️ Accidents by Aircraft Type")
        aircraft_counts = filtered_df['aircraft_category'].value_counts().reset_index()
        aircraft_counts.columns = ['aircraft', 'count']
        fig3 = px.bar(
            aircraft_counts.head(15),
            x='count',
            y='aircraft',
            orientation='h',
            title='Top 15 Aircraft Types',
            labels={'aircraft': 'Aircraft', 'count': 'Accidents'}
        )
        st.plotly_chart(fig3, use_container_width=True)

    with col2:
        st.subheader("💀 Fatalities by Aircraft Type")
        aircraft_fatalities = filtered_df.groupby('aircraft_category')['fatalities_num'].sum().reset_index()
        aircraft_fatalities = aircraft_fatalities.sort_values('fatalities_num', ascending=False).head(15)
        fig4 = px.bar(
            aircraft_fatalities,
            x='fatalities_num',
            y='aircraft_category',
            orientation='h',
            title='Top 15 Aircraft Types',
            labels={'aircraft_category': 'Aircraft', 'fatalities_num': 'Fatalities'}
        )
        st.plotly_chart(fig4, use_container_width=True)

    # Enhanced data visualizations
    if is_enhanced and 'phase' in filtered_df.columns:
        st.markdown("---")
        st.subheader("🔍 Enhanced Analysis - Flight Phase & Nature")

        col1, col2 = st.columns(2)

        with col1:
            st.subheader("✈️ Accidents by Flight Phase")
            phase_counts = filtered_df['phase'].value_counts().reset_index().head(15)
            phase_counts.columns = ['phase', 'count']
            fig_phase = px.bar(
                phase_counts,
                x='count',
                y='phase',
                orientation='h',
                title='Top 15 Flight Phases',
                labels={'phase': 'Flight Phase', 'count': 'Accidents'}
            )
            st.plotly_chart(fig_phase, use_container_width=True)

        with col2:
            st.subheader("📋 Accidents by Nature")
            if 'nature' in filtered_df.columns:
                nature_counts = filtered_df['nature'].value_counts().reset_index().head(15)
                nature_counts.columns = ['nature', 'count']
                fig_nature = px.bar(
                    nature_counts,
                    x='count',
                    y='nature',
                    orientation='h',
                    title='Top 15 Flight Nature',
                    labels={'nature': 'Flight Nature', 'count': 'Accidents'}
                )
                st.plotly_chart(fig_nature, use_container_width=True)

    # Chart 3: Damage and operator distribution
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("💥 Damage Distribution")
        damage_counts = filtered_df['damage_full'].value_counts().reset_index()
        damage_counts.columns = ['damage', 'count']
        fig5 = px.pie(
            damage_counts,
            values='count',
            names='damage',
            title='Accidents by Damage Level'
        )
        st.plotly_chart(fig5, use_container_width=True)

    with col2:
        st.subheader("🏢 Top Operators")
        operator_counts = filtered_df['operator'].value_counts().reset_index().head(15)
        operator_counts.columns = ['operator', 'count']
        fig6 = px.bar(
            operator_counts,
            x='count',
            y='operator',
            orientation='h',
            title='Top 15 Operators',
            labels={'operator': 'Operator', 'count': 'Accidents'}
        )
        st.plotly_chart(fig6, use_container_width=True)

    # Custom Charts Section
    if st.session_state.custom_charts:
        st.markdown("---")
        render_custom_charts(filtered_df)

    # Fatal accidents list
    st.markdown("---")
    st.subheader("⚠️ Major Fatal Accidents")

    fatal_df = filtered_df[filtered_df['is_fatal']].sort_values('fatalities_num', ascending=False).head(20)

    if len(fatal_df) > 0:
        display_cols = ['date', 'aircraft_category', 'operator', 'location', 'fatalities_num', 'damage_full']
        if is_enhanced and 'phase' in fatal_df.columns:
            display_cols.append('phase')

        display_df = fatal_df[display_cols].copy()
        col_names = ['Date', 'Aircraft', 'Operator', 'Location', 'Fatalities', 'Damage']
        if is_enhanced and 'phase' in fatal_df.columns:
            col_names.append('Phase')
        display_df.columns = col_names
        st.dataframe(display_df, use_container_width=True)
    else:
        st.info("No fatal accidents match the selected filters.")

    # Accident details (for enhanced data)
    if is_enhanced and 'narrative' in filtered_df.columns:
        st.markdown("---")
        st.subheader("📖 Detailed Accident Information")

        # Search box
        search_term = st.text_input("Search in narratives (e.g., 'landing gear', 'engine failure'):")

        if search_term:
            search_df = filtered_df[
                filtered_df['narrative'].fillna('').str.contains(search_term, case=False, na=False)
            ].head(10)

            if len(search_df) > 0:
                for idx, row in search_df.iterrows():
                    with st.expander(f"{row['date']} - {row['aircraft_category']} - {row['operator']}"):
                        col1, col2 = st.columns(2)
                        with col1:
                            st.write(f"**Location:** {row['location']}")
                            st.write(f"**Fatalities:** {row['fatalities']}")
                            st.write(f"**Damage:** {row['damage_full']}")
                            if pd.notna(row.get('phase')):
                                st.write(f"**Phase:** {row['phase']}")
                        with col2:
                            if pd.notna(row.get('departure_airport')):
                                st.write(f"**From:** {row['departure_airport']}")
                            if pd.notna(row.get('destination_airport')):
                                st.write(f"**To:** {row['destination_airport']}")
                            if pd.notna(row.get('msn')):
                                st.write(f"**MSN:** {row['msn']}")

                        if pd.notna(row['narrative']):
                            st.write("**Narrative:**")
                            st.write(row['narrative'])
            else:
                st.info("No accidents found matching your search.")

    # Raw data view
    st.markdown("---")
    with st.expander("📋 View Full Data"):
        st.dataframe(filtered_df, use_container_width=True)

        # CSV download button
        csv = filtered_df.to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            label="📥 Download Filtered Data as CSV",
            data=csv,
            file_name=f'filtered_aviation_data_{datetime.now().strftime("%Y%m%d")}.csv',
            mime='text/csv',
        )

    # Statistics summary
    st.markdown("---")
    st.subheader("📈 Statistics Summary")
    col1, col2, col3 = st.columns(3)

    with col1:
        st.write("**Period**")
        st.write(f"From: {filtered_df['date'].min()}")
        st.write(f"To: {filtered_df['date'].max()}")

    with col2:
        st.write("**Aircraft Types**")
        st.write(f"Total: {filtered_df['aircraft_category'].nunique()} types")

    with col3:
        st.write("**Operators**")
        st.write(f"Total: {filtered_df['operator'].nunique()} operators")


if __name__ == "__main__":
    main()

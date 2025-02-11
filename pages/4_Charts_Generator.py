import streamlit as st
from utils.check_auth import check_auth
import os
import tempfile
from excel_reader_for_llm import excel_to_json
from chart_generation_multiple import main as generate_charts, ChartConfig, ChartGenerator

# Check authentication
check_auth()

# Page config
st.set_page_config(page_title="Charts Generator", page_icon="📊")

# Title and description
st.title("Charts Generator")
with st.expander("Instructions", expanded=False):
    st.markdown("""
    Generate insightful charts from your SuperPro Designer Economic Evaluation Reports (EER)! This tool:

    - Processes EER files to extract economic data
    - Generates comparative charts for:
        - Operating Costs
        - Material Costs
        - Consumable Costs
        - Utility Costs
    - Creates a detailed stacked bar chart for Unit Production Costs
    - Allows easy comparison between different scenarios

    How to use:
    1. Upload one or more EER files (.xls/.xlsx)
    2. Provide a scenario name for each file
    3. Click "Generate Charts" to process the files
    4. View and download the generated charts

    The generated charts will help you:
    - Compare costs across different scenarios
    - Identify major cost drivers
    - Analyze unit production costs
    - Make data-driven decisions
    """)

# Initialize chart settings in session state
if 'chart_settings' not in st.session_state:
    st.session_state.chart_settings = ChartConfig()

# Chart Settings
with st.expander("Chart Settings", expanded=False):
    st.subheader("Font Settings")
    col1, col2 = st.columns(2)
    with col1:
        st.session_state.chart_settings.title_font_size = st.slider(
            "Title Font Size", 8, 24, 18, help="Font size for chart titles")
        st.session_state.chart_settings.label_font_size = st.slider(
            "Label Font Size", 8, 20, 15, help="Font size for axis labels")
        st.session_state.chart_settings.legend_font_size = st.slider(
            "Legend Font Size", 8, 18, 15, help="Font size for legend text")
        st.session_state.chart_settings.tick_font_size = st.slider(
            "Tick Label Font Size", 8, 16, 15, help="Font size for axis tick labels (both horizontal and vertical)")
    with col2:
        st.session_state.chart_settings.value_font_size = st.slider(
            "Value Label Font Size", 8, 16, 15, help="Font size for value labels")
    
    st.subheader("Bar Settings")
    st.session_state.chart_settings.bar_width = st.slider(
        "Bar Width", 0.1, 1.0, 0.7, 0.1, help="Width of the bars in the chart")
    
    st.subheader("Chart Settings")
    col1, col2 = st.columns(2)
    with col1:
        st.session_state.chart_settings.figure_width = st.number_input(
            "Chart Width", 8, 30, 10, help="Width of the chart in inches")
        st.session_state.chart_settings.dpi = st.selectbox(
            "Resolution (DPI)", [72, 100, 150, 300], 3, help="Chart resolution in dots per inch")
    with col2:
        st.session_state.chart_settings.figure_height = st.number_input(
            "Chart Height", 6, 20, 8, help="Height of the chart in inches")
    
    st.subheader("Text Customization")
    
    # Show titles checkbox in its own row
    st.session_state.chart_settings.show_title = st.checkbox(
        "Show Chart Titles", value=True, help="Toggle visibility of chart titles")
    
    # Prefix inputs and unit scale in a single row with equal columns
    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        st.session_state.chart_settings.title_prefix = st.text_input(
            "Title Prefix", "Comparative", help="Prefix for chart titles", 
            disabled=not st.session_state.chart_settings.show_title)
    with col2:
        st.session_state.chart_settings.y_axis_prefix = st.text_input(
            "Y-Axis Label Prefix", "Annual Cost", help="Prefix for y-axis labels")
    with col3:
        st.session_state.chart_settings.unit_scale = st.selectbox(
            "Cost Unit Scale", 
            options=["€", "k€", "m€"],
            help="Scale for cost values (except unit production costs)")
    
    if st.button("Reset to Defaults"):
        st.session_state.chart_settings = ChartConfig()

# Main interface
st.subheader("Upload Files")

# Create a container for file uploaders
file_uploaders = st.container()

# Initialize session state for file uploaders if not exists
if 'num_files' not in st.session_state:
    st.session_state.num_files = 1

# Add/Remove file uploader buttons
col1, col2 = st.columns([1, 5])
with col1:
    if st.button("Add File"):
        st.session_state.num_files += 1
with col2:
    if st.button("Remove File") and st.session_state.num_files > 1:
        st.session_state.num_files -= 1

# Create dynamic file uploaders
uploaded_files = []
scenario_names = []

for i in range(st.session_state.num_files):
    with file_uploaders:
        col1, col2 = st.columns([1, 1])
        with col1:
            file = st.file_uploader(f"Upload EER file #{i+1}", type=['xls', 'xlsx'], key=f"file_{i}")
            if file:
                uploaded_files.append(file)
        with col2:
            scenario_name = st.text_input("Scenario Name", key=f"scenario_{i}", 
                                        placeholder=f"Scenario {i+1}")
            if scenario_name:
                scenario_names.append(scenario_name)

if uploaded_files:
    if st.button("Generate Charts"):
        with st.spinner("Processing files and generating charts..."):
            try:
                # Create temporary directory for processing
                with tempfile.TemporaryDirectory() as temp_dir:
                    # Process each file
                    json_files = []
                    
                    # Save uploaded files and convert to JSON
                    for i, file in enumerate(uploaded_files):
                        # Save uploaded file
                        temp_file_path = os.path.join(temp_dir, file.name)
                        with open(temp_file_path, 'wb') as f:
                            f.write(file.getvalue())
                        
                        # Convert to JSON
                        try:
                            json_file = excel_to_json(temp_file_path)
                            json_files.append(json_file)
                        except Exception as e:
                            st.error(f"Error processing {file.name}: {str(e)}")
                            continue
                    
                    if json_files:
                        # Create output directory for charts
                        charts_dir = os.path.join(temp_dir, 'charts')
                        os.makedirs(charts_dir, exist_ok=True)
                        
                        # Generate charts
                        try:
                            # Initialize or clear charts data in session state
                            if 'generated_charts' not in st.session_state:
                                st.session_state.generated_charts = {}
                            
                            generate_charts(json_files, scenario_names, charts_dir, config=st.session_state.chart_settings)
                            
                            # Display charts
                            st.subheader("Generated Charts")
                            
                            # List all generated chart files
                            chart_files = [
                                'AOC.png',
                                'Materials.png',
                                'Consumables.png',
                                'Utilities.png',
                                'stacked_bar_chart.png'
                            ]
                            
                            # Store available charts and their data
                            available_charts = {}
                            
                            # Display each chart with download button
                            for chart_file in chart_files:
                                chart_path = os.path.join(charts_dir, chart_file)
                                if os.path.exists(chart_path):
                                    # Read chart file
                                    with open(chart_path, 'rb') as f:
                                        chart_data = f.read()
                                    
                                    # Store chart data in session state
                                    st.session_state.generated_charts[chart_file] = {
                                        'data': chart_data,
                                        'name': chart_file.replace('.png', '')
                                    }
                                    
                                    # Display chart
                                    st.image(chart_data, caption=chart_file.replace('.png', ''))
                                    
                                    # Add download button
                                    st.download_button(
                                        label=f"Download {chart_file}",
                                        data=chart_data,
                                        file_name=chart_file,
                                        mime="image/png",
                                        key=f"download_gen_{chart_file}"  # Unique key for generated charts
                                    )
                                    
                                    st.markdown("---")  # Add separator between charts
                            
                        except Exception as e:
                            st.error(f"Error generating charts: {str(e)}")
                    else:
                        st.error("No files were successfully processed")
            
            except Exception as e:
                st.error(f"An error occurred: {str(e)}")

# Display generated charts and multi-panel figure interface if charts exist
if 'generated_charts' in st.session_state and st.session_state.generated_charts:
    # Display each chart with download button
    for chart_file, chart_info in st.session_state.generated_charts.items():
        # Display chart
        st.image(chart_info['data'], caption=chart_info['name'])
        
        # Add download button
        st.download_button(
            label=f"Download {chart_file}",
            data=chart_info['data'],
            file_name=chart_file,
            mime="image/png",
            key=f"download_view_{chart_file}"  # Unique key for chart viewer
        )
        
        st.markdown("---")  # Add separator between charts
    
    # Multi-panel figure creation section
    st.subheader("Create Multi-panel Figure")
    st.markdown("""
    Select charts to include in a multi-panel figure and assign labels (a, b, c, etc.) to each selected chart.
    The charts will be arranged in a grid layout.
    """)
    
    # Create columns for chart selection and label assignment
    selected_charts = []
    
    # Create a temporary directory for multi-panel figure creation
    with tempfile.TemporaryDirectory() as temp_dir:
        # Save charts to temporary files for multi-panel creation
        for chart_file, chart_info in st.session_state.generated_charts.items():
            temp_chart_path = os.path.join(temp_dir, chart_file)
            with open(temp_chart_path, 'wb') as f:
                f.write(chart_info['data'])
            
            col1, col2 = st.columns([3, 1])
            with col1:
                if st.checkbox(f"Include {chart_info['name']}", key=f"select_{chart_file}"):
                    with col2:
                        label = st.text_input("Label", 
                                            key=f"label_{chart_file}",
                                            max_chars=1,
                                            placeholder="a",
                                            help="Single letter label (a, b, c, etc.)")
                        if label:
                            selected_charts.append((temp_chart_path, label))
        
        if selected_charts:
            # Grid layout controls
            st.subheader("Grid Layout")
            st.markdown("""
            Specify the grid layout for your multi-panel figure. The charts will be arranged from left to right, top to bottom.
            """)
            
            col1, col2 = st.columns(2)
            with col1:
                n_rows = st.number_input("Number of Rows", min_value=1, max_value=len(selected_charts), 
                                       value=min(2, len(selected_charts)),
                                       help="Number of rows in the grid layout")
            with col2:
                n_cols = st.number_input("Number of Columns", min_value=1, max_value=len(selected_charts),
                                       value=min(2, len(selected_charts)),
                                       help="Number of columns in the grid layout")
            
            # Validate grid dimensions
            total_cells = n_rows * n_cols
            if total_cells < len(selected_charts):
                st.error(f"Grid size ({n_rows}×{n_cols} = {total_cells} cells) is too small for {len(selected_charts)} charts. Please increase the number of rows or columns.")
            else:
                if st.button("Generate Multi-panel Figure"):
                    with st.spinner("Creating multi-panel figure..."):
                        # Generate multi-panel figure
                        chart_gen = ChartGenerator(temp_dir, config=st.session_state.chart_settings)
                        chart_gen.create_multi_panel_figure(selected_charts, "multi_panel_figure.png", n_rows=n_rows, n_cols=n_cols)
                    
                    # Display and offer download of multi-panel figure
                    multi_panel_path = os.path.join(temp_dir, "multi_panel_figure.png")
                    if os.path.exists(multi_panel_path):
                        with open(multi_panel_path, 'rb') as f:
                            multi_panel_data = f.read()
                        
                        st.subheader("Multi-panel Figure")
                        st.image(multi_panel_data)
                        
                        st.download_button(
                            label="Download Multi-panel Figure",
                            data=multi_panel_data,
                            file_name="multi_panel_figure.png",
                            mime="image/png",
                            key="download_multi_panel"  # Unique key for multi-panel figure
                        )

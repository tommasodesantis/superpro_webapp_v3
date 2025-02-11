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
    with col2:
        st.session_state.chart_settings.tick_font_size = st.slider(
            "Tick Label Font Size", 8, 16, 15, help="Font size for axis tick labels")
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
    col1, col2 = st.columns(2)
    with col1:
        st.session_state.chart_settings.title_prefix = st.text_input(
            "Title Prefix", "Comparative", help="Prefix for chart titles")
    with col2:
        st.session_state.chart_settings.y_axis_prefix = st.text_input(
            "Y-Axis Label Prefix", "Annual Cost", help="Prefix for y-axis labels")
    
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
                            
                            # Display each chart with download button
                            for chart_file in chart_files:
                                chart_path = os.path.join(charts_dir, chart_file)
                                if os.path.exists(chart_path):
                                    # Read chart file
                                    with open(chart_path, 'rb') as f:
                                        chart_data = f.read()
                                    
                                    # Display chart
                                    st.image(chart_data, caption=chart_file.replace('.png', ''))
                                    
                                    # Add download button
                                    st.download_button(
                                        label=f"Download {chart_file}",
                                        data=chart_data,
                                        file_name=chart_file,
                                        mime="image/png"
                                    )
                                    
                                    st.markdown("---")  # Add separator between charts
                            
                        except Exception as e:
                            st.error(f"Error generating charts: {str(e)}")
                    else:
                        st.error("No files were successfully processed")
            
            except Exception as e:
                st.error(f"An error occurred: {str(e)}")

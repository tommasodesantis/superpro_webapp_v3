import json
import matplotlib.pyplot as plt
import numpy as np
import os
import sys
from typing import Dict, List, Union, Tuple

class SuperProAnalyzer:
    """Class to analyze and visualize SuperPro Designer JSON output files."""
    
    def __init__(self):
        # Standard cost categories matching chart_generation_multiple
        self.standard_cost_categories = [
            'Raw materials (OPEX)', 
            'Labor (OPEX)', 
            'Utilities (OPEX)',
            'Consumables (OPEX)', 
            'Wastewater treatment (OPEX)', 
            'Laboratory/QC/QA (OPEX)', 
            'Facility-dependent (CAPEX)'
        ]
        
        # Column mappings for different types of cost values
        self.cost_columns = {
            'yearly': ('$/year', 4),  # Column D
            'per_unit': ('$/kg MP', 2),  # Column B
            'percentage': ('%', 5)  # Column E
        }

        # Define standard colors to match chart_generation_multiple
        self.colors = ['skyblue', 'orange', 'navy', 'green', 'red', 'purple', 'gray']

        # Category name mapping to standardize labels
        self.category_mapping = {
            'Materials': 'Raw materials (OPEX)',
            'Labor': 'Labor (OPEX)',
            'Utilities': 'Utilities (OPEX)',
            'Consumables': 'Consumables (OPEX)',
            'Waste Trtmt/Disp': 'Wastewater treatment (OPEX)',
            'Lab/QC/QA': 'Laboratory/QC/QA (OPEX)',
            'Facility': 'Facility-dependent (CAPEX)'
        }

    def load_json_data(self, file_paths: Union[str, List[str]], scenario_names: List[str] = None) -> Dict:
        """
        Load and validate one or multiple JSON files.
        
        Args:
            file_paths: Single file path or list of file paths to JSON files
            scenario_names: Optional list of scenario names to use instead of filenames
            
        Returns:
            Dictionary mapping process names to their data
        """
        if isinstance(file_paths, str):
            file_paths = [file_paths]
            
        if scenario_names and len(scenario_names) != len(file_paths):
            raise ValueError("Number of scenario names must match number of files")
            
        process_data = {}
        
        for i, file_path in enumerate(file_paths):
            try:
                with open(file_path, 'r') as file:
                    data = json.load(file)
                    
                # Use scenario name if provided, otherwise use filename
                process_name = scenario_names[i] if scenario_names else os.path.splitext(os.path.basename(file_path))[0]
                process_data[process_name] = data
                print(f"[INFO] Loaded data for process: {process_name}")
                
            except FileNotFoundError:
                print(f"Error: File not found: {file_path}", file=sys.stderr)
                continue
            except json.JSONDecodeError:
                print(f"Error: Invalid JSON format in file: {file_path}", file=sys.stderr)
                continue
                
        return process_data

    def identify_sections(self, cells: List[Dict]) -> List[str]:
        """
        Identify process sections from the JSON data.
        
        Args:
            cells: List of cell data from JSON
            
        Returns:
            List of identified process sections
        """
        sections = []
        in_section_area = False

        for cell in cells:
            value = str(cell.get('value', ''))

            # Look for the section header row using a more flexible pattern
            if ("CAPITAL INVESTMENT PER PROCESS SECTION" in value.upper() and 
                "PRICES" in value.upper()):
                in_section_area = True
                continue

            if in_section_area and cell['column'] == 1:
                if value == "Total":
                    break
                if value not in ["Section", ""]:
                    sections.append(value)

        print(f"[DEBUG] Identified sections: {sections}")
        return sections

    def extract_cost_data(self, data: Dict, cost_type: str = 'yearly') -> Tuple[Dict, List[str]]:
        """
        Extract cost data for each section and category from the JSON data.
        
        Args:
            data: Parsed JSON data
            cost_type: Type of cost to extract ('yearly', 'per_unit', or 'percentage')
            
        Returns:
            Tuple of (cost_data_dict, sections_list)
        """
        cells = data['Table p. 1']['cells']
        sections = self.identify_sections(cells)

        if not sections:
            print("Warning: No process sections found in data", file=sys.stderr)
            return {}, []

        print(f"[INFO] Extracting cost data for sections: {sections}")
        # Initialize cost data dictionary with mapped category names
        cost_data = {section: {cat: 0.0 for cat in self.standard_cost_categories} for section in sections}

        cost_col_name, cost_col = self.cost_columns[cost_type]
        current_section = None

        for i, cell in enumerate(cells):
            value = str(cell.get('value', ''))

            # Track current section
            if cell['column'] == 1 and value in sections:
                current_section = value
                print(f"[DEBUG] Current section: {current_section}")
                continue

            # Extract costs for current section using category mapping
            if current_section and cell['column'] == 1 and value in self.category_mapping:
                mapped_category = self.category_mapping[value]
                row = cell['row']

                # Find corresponding cost value
                for cost_cell in cells:
                    if cost_cell['row'] == row and cost_cell['column'] == cost_col:
                        try:
                            cost_value = float(str(cost_cell['value']).replace(',', ''))
                            cost_data[current_section][mapped_category] = cost_value
                            print(f"[DEBUG] Extracted cost - Section: {current_section}, Category: {mapped_category}, Value: {cost_value}")
                        except (ValueError, TypeError):
                            print(f"Warning: Invalid cost value for {mapped_category} in {current_section}", file=sys.stderr)
                        break

        print(f"[INFO] Cost data extracted: {cost_data}")
        return cost_data, sections

    def create_comparison_chart(self, all_process_data: Dict, output_path: str):
        """
        Create a grouped stacked bar chart comparing multiple processes.
        
        Args:
            all_process_data: Dictionary mapping process names to their cost data
            output_path: Path to save the chart
        """
        processes = list(all_process_data.keys())
        if not processes:
            print("Error: No process data available for comparison", file=sys.stderr)
            return

        # Extract cost data for each process
        process_costs = {}
        all_sections = set()

        for process_name, data in all_process_data.items():
            print(f"[INFO] Processing data for: {process_name}")
            cost_data, sections = self.extract_cost_data(data)
            process_costs[process_name] = cost_data
            all_sections.update(sections)

        # Convert set to list to maintain order
        all_sections = list(all_sections)
        print(f"[DEBUG] All sections before sorting: {all_sections}")

        # Sort sections by total cost
        section_totals = {
            section: sum(
                sum(costs.get(cat, 0) for cat in self.standard_cost_categories)
                for costs in [
                    proc_data.get(section, {}) for proc_data in process_costs.values()
                ]
            )
            for section in all_sections
        }
        all_sections = sorted(all_sections, key=lambda x: section_totals.get(x, 0), reverse=True)
        print(f"[DEBUG] All sections after sorting: {all_sections}")

        # Set up the plot with matching style
        fig, ax = plt.subplots(figsize=(14, 10))

        # Calculate bar positions
        n_processes = len(processes)
        bar_width = 0.6 / n_processes
        indices = np.arange(len(all_sections))
        print(f"[DEBUG] Indices for sections: {indices}")

        # Create stacked bars for each process
        for p_idx, process in enumerate(processes):
            bottom = np.zeros(len(all_sections))
            cost_data = process_costs[process]
            print(f"[INFO] Plotting data for process: {process}")
            print(f"[DEBUG] Cost data: {cost_data}")

            # Plot bars for each category in standard order
            for cat_idx, category in enumerate(self.standard_cost_categories):
                values = [cost_data.get(section, {}).get(category, 0) for section in all_sections]
                offset = p_idx * bar_width - (n_processes - 1) * bar_width / 2
                print(f"[DEBUG] Values for category '{category}' in process '{process}': {values}")

                ax.bar(indices + offset, values, bar_width, bottom=bottom,
                       label=category if p_idx == 0 else "",
                       color=self.colors[cat_idx % len(self.colors)],
                       edgecolor='white', linewidth=0.5)

                bottom += values
                print(f"[DEBUG] Updated bottom for stacking: {bottom}")

        # Customize chart appearance to match chart_generation_multiple
        ax.set_xticks(indices)
        ax.set_xticklabels(all_sections, rotation=45, ha='right', fontsize=10)
        print(f"[DEBUG] Set x-tick labels: {all_sections}")
        ax.set_ylabel(f'Unit Production Cost [€ kg⁻¹]', fontsize=12)
        ax.set_title('Comparative Unit Production Cost', fontsize=14, fontweight='bold')

        # Remove top and right spines
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)

        # Add legend with matching style
        ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=10)

        # Adjust layout and save with matching style
        plt.subplots_adjust(left=0.1, right=0.85, bottom=0.15, top=0.9)
        plt.tight_layout()
        plt.savefig(output_path, bbox_inches='tight', dpi=300)
        plt.close()
        print(f"[INFO] Chart saved to {output_path}")

def main():
    """Main execution function."""
    if len(sys.argv) < 4:
        print("Error: Usage: python script.py <json_file1> [json_file2 ...] <scenario_name1> [scenario_name2 ...] <output_dir>", file=sys.stderr)
        sys.exit(1)
        
    try:
        # Split arguments into files, scenario names, and output directory
        num_files = (len(sys.argv) - 2) // 2  # -2 for script name and output_dir
        json_files = sys.argv[1:num_files+1]
        scenario_names = sys.argv[num_files+1:-1]
        output_dir = sys.argv[-1]

        if len(json_files) != len(scenario_names):
            print("Error: Number of files must match number of scenario names", file=sys.stderr)
            sys.exit(1)

        print(f"[INFO] JSON files: {json_files}")
        print(f"[INFO] Scenario names: {scenario_names}")
        print(f"[INFO] Output directory: {output_dir}")

        # Initialize analyzer and process data
        analyzer = SuperProAnalyzer()
        process_data = analyzer.load_json_data(json_files, scenario_names)

        if not process_data:
            print("Error: No valid process data loaded", file=sys.stderr)
            sys.exit(1)

        # Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)

        # Generate comparison chart with expected filename
        output_path = os.path.join(output_dir, 'icr_stacked_bar_chart.png')
        analyzer.create_comparison_chart(process_data, output_path)
        
    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
import json
import matplotlib.pyplot as plt
import numpy as np
import os
import re
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass


@dataclass
class ProcessData:
    """Class to store standardized process data"""
    name: str
    currency: str
    year: int
    operating_costs: Dict[str, float]
    material_costs: Dict[str, float]
    consumable_costs: Dict[str, float]
    utility_costs: Dict[str, float]
    annual_rate: float

class ProcessDataExtractor:
    """Class to handle extraction of process data from SuperPro Designer JSON output"""

    # Add this as a class attribute
    name_mapping = {
        "Prot-A Reg Buff": "Strip Buffer",
        "Prot-A Wash Buf": "Wash Buffer",
        "Protein A eluti": "Eluti. Buffer",
        "Protein A Equil": "Equil. Buffer",
        "Trisodium citra": "Trisodium citrate",
        "Dft DEF Cartridge": "DEF Cartridge",
        "Dft PBA Chrom Resin": "Chrom. Resin",
        "Waste Treatment/Disposal": "Wastewater treatment (OPEX)",
        "Labor-Dependent": "Labor (OPEX)",
        "Utilities": "Utilities (OPEX)",
        "Consumables": "Consumables (OPEX)",
        "Raw Materials": "Raw materials (OPEX)",
        "Laboratory/QC/QA": "Laboratory/QC/QA (OPEX)",
        "Facility-Dependent": "Facility-dependent (CAPEX)"
    }

    def _rename_item(self, name: str) -> str:
        """Rename items according to standardized naming"""
        return self.name_mapping.get(name, name)
    
    def __init__(self, file_path: str, scenario_name: Optional[str] = None):
        self.data = self._load_json_data(file_path)
        self.currency = self._detect_currency()
        self.year = self._detect_year()
        self.number_format = self._detect_number_format()
        self.file_path = file_path
        self.scenario_name = scenario_name
        
    @staticmethod
    def _load_json_data(file_path: str) -> Dict:
        """Load and validate JSON data"""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                data = json.load(file)
            if 'Table p. 1' not in data:
                raise ValueError("Invalid SuperPro Designer output format")
            return data
        except Exception as e:
            raise Exception(f"Error loading {file_path}: {str(e)}")

    def _detect_currency(self) -> str:
        """Detect currency symbol from the data"""
        cells = self.data['Table p. 1']['cells']
        for cell in cells:
            if cell['row'] == 1 and cell['column'] == 3:
                currency = cell['value'].strip()
                # Handle euro symbol specifically
                if 'EUR' in currency or '€' in currency:
                    return '€'
                return currency.replace(' ', '')
        return '$'  # Default to USD if not found

    def _detect_year(self) -> int:
        """Detect base year from the data"""
        cells = self.data['Table p. 1']['cells']
        year_pattern = r'.*?(\d{4}).*?prices'
        for cell in cells:
            if cell['column'] == 1:
                match = re.search(year_pattern, str(cell['value']))
                if match:
                    return int(match.group(1))
        return 2024  # Default to current year if not found

    def _detect_number_format(self) -> str:
        """Detect number formatting style: 'EU' for European format and 'US' for American format.
        Heuristic: if a value contains both '.' and ',', and the dot appears before the comma, assume European.
        """
        cells = self.data['Table p. 1']['cells']
        for cell in cells:
            value_str = str(cell.get('value', '')).strip()
            if '.' in value_str and ',' in value_str:
                if value_str.find('.') < value_str.find(','):
                    return 'EU'
                else:
                    return 'US'
        return 'US'

    def _find_section_bounds(self, section_name: str) -> Tuple[int, int]:
        """Find the start and end rows for a given section"""
        cells = self.data['Table p. 1']['cells']
        start_row = None
        end_row = None
        
        for cell in cells:
            if cell['column'] == 1:
                if section_name in str(cell['value']):
                    start_row = cell['row']
                elif start_row and not end_row:
                    if cell['value'].startswith(str(int(section_name[0]) + 1)):
                        end_row = cell['row']
                        break
        
        return start_row, end_row or self.data['Table p. 1']['max_row']

    def _extract_costs(self, start_marker: str, end_marker: str = None, value_column: int = 5, exclude_patterns: List[str] = None) -> Dict[str, float]:
        costs = {}
        cells = self.data['Table p. 1']['cells']
        
        # Find start row of the section header
        start_row = None
        for cell in cells:
            if cell['column'] == 1 and start_marker in str(cell['value']):
                start_row = cell['row']
                break
                
        if not start_row:
            return costs

        # Find the header row (contains column names)
        header_row = None
        for cell in cells:
            if cell['row'] > start_row and cell['column'] == 1:
                header_row = cell['row']
                break

        if not header_row:
            return costs

        # Find end row
        end_row = None
        if end_marker:
            for cell in cells:
                if cell['row'] > header_row and cell['column'] == 1 and end_marker in str(cell['value']):
                    end_row = cell['row']
                    break

        # Process rows between header and end
        for cell in cells:
            if (cell['row'] > header_row and 
                cell['column'] == 1 and 
                (not end_row or cell['row'] < end_row)):
                
                name = cell['value'].strip() if cell.get('value') else ''
                
                # Skip if name matches any exclude pattern or is a header/total
                if (not name or 
                    name == 'TOTAL' or 
                    (exclude_patterns and any(pattern in name for pattern in exclude_patterns))):
                    continue
                
                # Only process rows where column 1 contains the item name
                cost_value = next((c['value'] for c in cells 
                                if c['row'] == cell['row'] and c['column'] == value_column), None)
                
                if cost_value is not None:
                    try:
                        if self.number_format == 'EU':
                            cost_str = str(cost_value).replace('.', '').replace(',', '.')
                        else:
                            cost_str = str(cost_value).replace(',', '')
                        cost_str = ''.join(c for c in cost_str if c.isdigit() or c in '.-')
                        cost = float(cost_str)
                        if cost > 0:
                            name = self._rename_item(name)
                            costs[name] = cost
                    except ValueError:
                        continue
                            
        return costs

    def extract_process_data(self) -> ProcessData:
        """Extract all relevant process data"""
        name = self._extract_process_name()
        operating_costs = self._extract_operating_costs()
        material_costs = self._extract_material_costs()
        consumable_costs = self._extract_consumable_costs()
        utility_costs = self._extract_utility_costs()
        annual_rate = self._extract_annual_rate()
        
        return ProcessData(
            name=name,
            currency=self.currency,
            year=self.year,
            operating_costs=operating_costs,
            material_costs=material_costs,
            consumable_costs=consumable_costs,
            utility_costs=utility_costs,
            annual_rate=annual_rate
        )

    def _extract_process_name(self) -> str:
        """Extract process name from scenario name or filename"""
        if self.scenario_name:
            return self.scenario_name
        # Fallback to filename without timestamp prefix if no scenario name provided
        filename = os.path.splitext(os.path.basename(self.file_path))[0]
        # Remove timestamp prefix if present (e.g., "1729777526733-")
        if '-' in filename:
            filename = filename.split('-', 1)[1]
        return filename

    def _extract_operating_costs(self) -> Dict[str, float]:
        """Extract operating costs using column 2 for values"""
        return self._extract_costs('ANNUAL OPERATING COST', '10.', value_column=2)

    def _extract_material_costs(self) -> Dict[str, float]:
        """Extract material costs"""
        return self._extract_costs('MATERIALS COST', '6.')

    def _extract_consumable_costs(self) -> Dict[str, float]:
        """Extract consumable costs"""
        return self._extract_costs('VARIOUS CONSUMABLES COST', '9.')

    def _extract_utility_costs(self) -> Dict[str, float]:
        """Extract utility costs"""
        return self._extract_costs('UTILITIES COST', '7.')

    def _extract_annual_rate(self) -> float:
        """Extract cost basis annual rate"""
        cells = self.data['Table p. 1']['cells']
        for cell in cells:
            if cell['row'] == 6 and cell['column'] == 2:
                try:
                    value_str = str(cell['value'])
                    if self.number_format == 'EU':
                        # For European format (1.200 means 1200)
                        value_str = value_str.replace('.', '').replace(',', '.')
                    else:
                        # For US format
                        value_str = value_str.replace(',', '')
                    return float(value_str)
                except ValueError:
                    return 0.0
        return 0.0

@dataclass
class ChartConfig:
    """Configuration class for chart styling"""
    # Font sizes
    title_font_size: int = 18
    label_font_size: int = 15
    legend_font_size: int = 15
    tick_font_size: int = 15
    value_font_size: int = 15
    
    # Bar styling
    bar_width: float = 0.7
    
    # Figure settings
    figure_width: int = 10
    figure_height: int = 8
    dpi: int = 300
    
    # Text customization
    title_prefix: str = "Comparative"
    y_axis_prefix: str = "Annual Cost"
    show_title: bool = True
    
    # Unit scale settings
    unit_scale: str = "€"  # Options: €, k€, t€, m€
    scale_factors = {
        "€": 1,
        "k€": 1e-3,
        "m€": 1e-6
    }

class ChartGenerator:
    """Class to handle chart generation for multiple processes"""
    
    def __init__(self, output_dir: str, config: Optional[ChartConfig] = None):
        self.output_dir = output_dir
        self.config = config or ChartConfig()
        os.makedirs(output_dir, exist_ok=True)
        plt.rcParams['font.family'] = 'DejaVu Sans'  # Use a font that supports the euro symbol
        
    def create_comparative_chart(self, 
                               data: Dict[str, Dict[str, float]], 
                               title: str, 
                               ylabel: str,
                               filename: str):
        """Create comparative bar chart"""
        if not data:
            return

        processes = list(data.keys())
        categories = list(set().union(*[d.keys() for d in data.values()]))
        
        # Sort categories by total value while maintaining process order
        category_totals = {cat: sum(data[proc].get(cat, 0) for proc in processes) for cat in categories}
        categories = sorted(categories, key=lambda x: category_totals[x], reverse=True)
        
        x = np.arange(len(categories))
        width = 0.8 / len(processes)

        fig, ax = plt.subplots(figsize=(self.config.figure_width, self.config.figure_height), dpi=self.config.dpi)
        
        # Disable scientific notation
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: format(int(x), ',')))
        
        # Apply unit scale if not unit production chart
        scale_factor = self.config.scale_factors[self.config.unit_scale]
        
        # Plot bars in original process order to maintain consistency
        bar_width = self.config.bar_width / len(processes)
        for i, process in enumerate(processes):
            values = [data[process].get(cat, 0) * scale_factor for cat in categories]
            ax.bar(x + i*bar_width, values, bar_width, label=process)

        # Update ylabel with unit scale, removing any existing currency symbol
        ylabel_base = ylabel.replace('(€)', '').strip()
        ylabel_with_unit = f"{ylabel_base} ({self.config.unit_scale})"
        ax.set_ylabel(ylabel_with_unit, fontsize=self.config.label_font_size)
        if self.config.show_title:
            ax.set_title(title, fontsize=self.config.title_font_size, fontweight='bold')
        ax.set_xticks(x + bar_width * (len(processes) - 1) / 2)
        ax.set_xticklabels(categories, rotation=45, ha='right', fontsize=self.config.tick_font_size)
        ax.legend(fontsize=self.config.legend_font_size)
        
        # Set y-axis tick label font size
        ax.tick_params(axis='y', labelsize=self.config.tick_font_size)
        
        plt.tight_layout()
        plt.savefig(os.path.join(self.output_dir, filename))
        plt.close()

    def create_stacked_bar_chart(self, processes: List[ProcessData]):
        """Create stacked bar chart for unit production costs"""
        categories = [
            'Raw materials (OPEX)', 'Labor (OPEX)', 'Utilities (OPEX)',
            'Consumables (OPEX)', 'Wastewater treatment (OPEX)', 
            'Laboratory/QC/QA (OPEX)', 'Facility-dependent (CAPEX)'
        ]
        colors = ['skyblue', 'orange', 'navy', 'green', 'red', 'purple', 'gray']
        
        fig, ax = plt.subplots(figsize=(self.config.figure_width, self.config.figure_height), dpi=self.config.dpi)
        x = np.arange(len(processes))
        width = self.config.bar_width
        bottom = np.zeros(len(processes))
        
        for cat, color in zip(categories, colors):
            values = []
            for process in processes:
                cat_cost = process.operating_costs.get(cat, 0)
                annual_rate = process.annual_rate
                unit_cost = cat_cost / annual_rate if annual_rate else 0
                values.append(unit_cost)
            
            ax.bar(x, values, width, label=cat, bottom=bottom, 
                color=color, edgecolor='white', linewidth=0.5)
            
            # Add value labels for significant contributions
            for i, v in enumerate(values):
                if v >= 300:  # Only show labels for categories >= 300
                    ax.text(i, bottom[i] + v/2, f'{v:.0f}', 
                        ha='center', va='center',
                        fontweight='bold', color='white', fontsize=self.config.value_font_size)
            
            bottom += values
        
        # Add total cost labels
        for i, process in enumerate(processes):
            total_cost = sum(process.operating_costs.values()) / process.annual_rate if process.annual_rate else 0
            ax.text(i, bottom[i], f'Total: {total_cost:.0f}',
                    ha='center', va='bottom',
                    fontsize=self.config.value_font_size, fontweight='bold', color='black')
        
        # Customize appearance
        ax.set_ylabel(f'Unit Production Cost [{processes[0].currency} kg⁻¹]', fontsize=self.config.label_font_size)
        if self.config.show_title:
            ax.set_title(f'{self.config.title_prefix} Unit Production Cost', fontsize=self.config.title_font_size, fontweight='bold')
        ax.set_xticks(x)
        ax.set_xticklabels([p.name for p in processes], fontsize=self.config.tick_font_size, rotation=45, ha='right')
        ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=self.config.legend_font_size)
        
        # Set y-axis tick label font size
        ax.tick_params(axis='y', labelsize=self.config.tick_font_size)
        
        # Remove top and right spines
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        
        # Adjust layout
        ax.set_xlim(-0.5, len(processes) - 0.5)
        plt.subplots_adjust(left=0.1, right=0.85, bottom=0.15, top=0.9)
        plt.tight_layout()
        
        # Save chart
        plt.savefig(os.path.join(self.output_dir, 'stacked_bar_chart.png'), 
                    bbox_inches='tight')
        plt.close()

def main(json_files: List[str], scenario_names: List[str], output_dir: str, config: Optional[ChartConfig] = None):
    """Main function to process multiple JSON files and generate charts"""
    
    processes = []
    
    # Extract data from all process files
    for file_path, scenario_name in zip(json_files, scenario_names):
        try:
            extractor = ProcessDataExtractor(file_path, scenario_name)
            process_data = extractor.extract_process_data()
            processes.append(process_data)
        except Exception as e:
            print(f"Error processing {file_path}: {str(e)}")
            continue

    if not processes:
        print("No valid process data found")
        return

    # Generate charts with custom settings
    chart_gen = ChartGenerator(output_dir, config=config)
    
    # Create comparative charts for each cost category
    categories = {
        'Operating Costs': (lambda p: p.operating_costs, 'AOC.png'),
        'Material Costs': (lambda p: p.material_costs, 'Materials.png'),
        'Consumable Costs': (lambda p: p.consumable_costs, 'Consumables.png'),
        'Utility Costs': (lambda p: p.utility_costs, 'Utilities.png')
    }
    
    # Generate individual comparative charts
    for title, (getter, filename) in categories.items():
        data = {p.name: getter(p) for p in processes}
        chart_gen.create_comparative_chart(
            data,
            f'Comparative {title}',
            'Annual Cost',
            filename
        )
    
    # Generate stacked bar chart
    chart_gen.create_stacked_bar_chart(processes)

import pandas as pd
import json
import sys
import os
from openpyxl import load_workbook

def read_excel_for_llm(file_path):
    print(f"Attempting to read file: {file_path}")
    
    try:
        # Determine file extension
        _, ext = os.path.splitext(file_path)
        
        if ext.lower() in ['.xlsx', '.xls']:
            sheets = {}
            
            if ext.lower() == '.xls':
                print("Detected .xls format, attempting to read with xlrd engine")
                try:
                    # For .xls files, try xlrd first
                    sheets = pd.read_excel(file_path, sheet_name=None, engine='xlrd')
                    print("Successfully read .xls file with xlrd engine")
                except Exception as e:
                    print(f"xlrd engine failed: {str(e)}")
                    try:
                        # Fallback to openpyxl
                        print("Attempting fallback to openpyxl engine")
                        sheets = pd.read_excel(file_path, sheet_name=None, engine='openpyxl')
                        print("Successfully read file with openpyxl engine")
                    except Exception as e2:
                        print(f"openpyxl engine also failed: {str(e2)}")
                        raise Exception(f"Failed to read .xls file with both engines. xlrd error: {str(e)}, openpyxl error: {str(e2)}")
            else:  # .xlsx file
                print("Detected .xlsx format, attempting to read with openpyxl engine")
                try:
                    # Use openpyxl for .xlsx files
                    xlsx = load_workbook(filename=file_path, read_only=True, data_only=True)
                    for sheet_name in xlsx.sheetnames:
                        try:
                            df = pd.read_excel(file_path, sheet_name=sheet_name, engine='openpyxl')
                            sheets[sheet_name] = df
                        except UnicodeDecodeError:
                            df = pd.read_excel(file_path, sheet_name=sheet_name, engine='openpyxl', encoding='latin1')
                            sheets[sheet_name] = df
                    print("Successfully read .xlsx file")
                except Exception as e:
                    print(f"Failed to read .xlsx file: {str(e)}")
                    raise
            
            print(f"Successfully read the Excel file: {file_path}")
            
            file_data = {}
            
            for sheet_name, df in sheets.items():
                print(f"Processing sheet: {sheet_name}")
                
                # Prepare the data structure
                data = {
                    "sheet_name": sheet_name,
                    "max_row": df.shape[0],
                    "max_column": df.shape[1],
                    "cells": []
                }
                
                # Iterate through the dataframe
                for row in range(df.shape[0]):
                    for col in range(df.shape[1]):
                        value = df.iat[row, col]
                        if pd.notna(value):  # Check if the cell is not empty
                            # Convert value to string with error handling
                            try:
                                str_value = str(value)
                            except UnicodeEncodeError:
                                str_value = str(value).encode('ascii', 'replace').decode('ascii')
                            
                            cell_data = {
                                "row": row + 1,  # Adding 1 to match Excel's 1-based indexing
                                "column": col + 1,
                                "column_letter": chr(65 + col % 26),  # Convert column number to letter (A, B, C, etc.)
                                "value": str_value
                            }
                            data["cells"].append(cell_data)
                
                file_data[sheet_name] = data
                print(f"Processed {len(data['cells'])} non-empty cells in sheet {sheet_name}")
            
            return file_data
        else:
            print(f"Unsupported file format: {ext}")
            return None
    
    except Exception as e:
        print(f"Error reading Excel file {file_path}: {str(e)}")
        raise  # Re-raise the exception to ensure proper error handling

def excel_to_json(input_file):
    try:
        # Read and convert Excel to structured JSON
        json_data = read_excel_for_llm(input_file)
        
        if json_data is None:
            raise Exception("Failed to read Excel file")
        
        # Create output filename in the same directory as the input file
        output_file = os.path.splitext(input_file)[0] + '_output.json'
        
        # Write JSON to file with UTF-8 encoding
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, indent=2, ensure_ascii=False)
        
        print(f"Successfully created JSON output file: {output_file}")
        return output_file
    except Exception as e:
        print(f"Error in excel_to_json: {str(e)}")
        raise

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python excel_reader_for_llm.py <excel_file_path>")
        sys.exit(1)
    
    input_file = sys.argv[1]
    try:
        output_file = excel_to_json(input_file)
        print(f"Successfully processed {input_file} to {output_file}")
    except Exception as e:
        print(f"Error processing file: {str(e)}")
        sys.exit(1)

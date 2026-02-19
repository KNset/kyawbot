#!/usr/bin/env python3
"""
Convert a cookies.json file to a pickle (.pkl) file.
Usage: python json_to_pkl.py <input.json> <output.pkl>
"""

import sys
import json
import pickle

def convert_json_to_pkl(input_path, output_path):
    """
    Load cookies from a JSON file and save them as a pickled list of dictionaries.
    """
    # Read JSON file
    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            cookies = json.load(f)
    except Exception as e:
        print(f"Error reading JSON file {input_path}: {e}", file=sys.stderr)
        sys.exit(1)

    # Ensure the loaded data is a list (optional check)
    if not isinstance(cookies, list):
        print("Warning: JSON root is not a list. Pickling as is.", file=sys.stderr)

    # Write to pickle file
    try:
        with open(output_path, 'wb') as f:
            pickle.dump(cookies, f)
        print(f"Successfully wrote {len(cookies) if isinstance(cookies, list) else '?'} cookies to {output_path}")
    except Exception as e:
        print(f"Error writing pickle file {output_path}: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python json_to_pkl.py <input.json> <output.pkl>")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2]
    convert_json_to_pkl(input_file, output_file)
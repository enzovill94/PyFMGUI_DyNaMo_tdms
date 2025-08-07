#!/usr/bin/env python3
"""
Simple script to open the generated visualization images
"""

import subprocess
import sys
from pathlib import Path

def open_images():
    """Open the generated visualization images"""
    current_dir = Path(__file__).parent
    
    # List of image files to open
    image_files = [
        "nn_mock_visualization.png",
        "nn_plateau_visualization.png"
    ]
    
    for image_file in image_files:
        image_path = current_dir / image_file
        if image_path.exists():
            print(f"Opening {image_file}...")
            try:
                # On macOS, use 'open' command
                subprocess.run(['open', str(image_path)], check=True)
            except subprocess.CalledProcessError:
                print(f"Could not open {image_file}")
            except FileNotFoundError:
                print("'open' command not found. Please open the image manually.")
        else:
            print(f"{image_file} not found in {current_dir}")

if __name__ == "__main__":
    open_images()

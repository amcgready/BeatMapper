"""
Utility functions for BeatMapper processing
"""
import logging
import math
import os
import re
from pathlib import Path

logger = logging.getLogger(__name__)

def format_safe(value, precision=2, unit=None):
    """
    Safely format a numeric value with consistent precision
    
    Args:
        value: Numeric value to format
        precision: Number of decimal places (default: 2)
        unit: Optional unit string to append
    
    Returns:
        str: Formatted string
    """
    try:
        if math.isnan(float(value)):
            return "0.00"
        
        formatted = f"{float(value):.{precision}f}"
        if unit:
            formatted = f"{formatted} {unit}"
        return formatted
    except (ValueError, TypeError):
        return str(value)

def format_time(seconds, precision=2):
    """
    Format time value in seconds with appropriate unit
    
    Args:
        seconds: Time in seconds
        precision: Number of decimal places (default: 2)
    
    Returns:
        str: Formatted time string with units
    """
    return format_safe(seconds, precision, "s")

def format_bpm(tempo, precision=1):
    """
    Format a tempo value with BPM unit
    
    Args:
        tempo: Tempo in beats per minute
        precision: Number of decimal places (default: 1)
    
    Returns:
        str: Formatted BPM string
    """
    return format_safe(tempo, precision, "BPM")

def format_percentage(value, precision=1):
    """
    Format a percentage value with appropriate symbol
    
    Args:
        value: Percentage value (0-100)
        precision: Number of decimal places (default: 1)
    
    Returns:
        str: Formatted percentage string
    """
    return format_safe(value, precision, "%")

def create_formatignore_file(directory=None):
    """
    Create a .formatignore file with patterns to ignore in formatter checks
    
    Args:
        directory: Directory for the ignore file (default: current module directory)
    """
    if directory is None:
        directory = os.path.dirname(os.path.abspath(__file__))
    
    ignore_path = os.path.join(directory, '.formatignore')
    
    ignore_patterns = [
        # CSV operations
        r'f"{.*:.2f}".*writerow\(',
        r'f"{.*:.2f}".*append\(',
        r'row\[\d+\]\s*=\s*f"{.*:.2f}"',
        # Log messages with units
        r'f".*{.*:.2f}\s*seconds"',
        r'f".*{.*:.1f}\s*BPM"',
        r'f".*{.*:.2f}%"',
    ]
    
    try:
        with open(ignore_path, 'w') as f:
            f.write("# Formatting patterns to ignore\n")
            for pattern in ignore_patterns:
                f.write(f"{pattern}\n")
                
        logger.info(f"Created formatter ignore file at {ignore_path}")
        
    except Exception as e:
        logger.error(f"Error creating formatter ignore file: {str(e)}")

def ensure_directory_exists(directory_path):
    """
    Ensure a directory exists, creating it if necessary
    
    Args:
        directory_path: Path to the directory
        
    Returns:
        bool: True if successful
    """
    try:
        os.makedirs(directory_path, exist_ok=True)
        return True
    except Exception as e:
        logger.error(f"Failed to create directory {directory_path}: {e}")
        return False

def find_files_with_extension(directory, extension=".py"):
    """
    Find all files with the specified extension in a directory and subdirectories
    
    Args:
        directory: Base directory to search
        extension: File extension to find
        
    Returns:
        list: List of file paths
    """
    extension = extension.lower()
    file_paths = []
    
    for root, _, files in os.walk(directory):
        for file in files:
            if file.lower().endswith(extension):
                file_paths.append(os.path.join(root, file))
                
    return file_paths

# For command-line usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Create the formatignore file in the current directory
    create_formatignore_file()
    
    logger.info("Utils module initialized")
"""
Main entry point for note generation across different generators.
Provides a simple interface to generate notes using any available generator.
"""
import os
import sys
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Try to import our common utilities
try:
    from .note_generator_common import (
        generate_notes,
        GENERATOR_PATTERN,
        GENERATOR_STANDARD,
        GENERATOR_HIGH_DENSITY
    )
except ImportError:
    # Define constants if import fails
    GENERATOR_PATTERN = "pattern"
    GENERATOR_STANDARD = "standard" 
    GENERATOR_HIGH_DENSITY = "high_density"
    
    # Define fallback generate_notes function
    def generate_notes(song_path, template_path, output_path, generator_type=None):
        """Fallback generate_notes function when import fails"""
        logger.error("Failed to import note_generator_common, using fallback")
        
        # Try to directly import pattern_notes_generator
        try:
            from .pattern_notes_generator import generate_notes_csv
            return generate_notes_csv(song_path, template_path, output_path)
        except ImportError:
            logger.error("Failed to import pattern_notes_generator")
            
        # Last resort - generate a basic pattern
        try:
            import csv
            with open(output_path, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(["Time [s]", "Enemy Type", "Aux Color 1", "Aux Color 2", "Nº Enemies", "interval", "Aux"])
                # Generate a very basic pattern - one note every 0.5 seconds
                for i in range(360):  # 3 minutes of content at 2 notes per second
                    time = i * 0.5
                    writer.writerow([f"{time:.2f}", "1", "2", "2", "1", "", "7"])
            return True
        except Exception as e:
            logger.error(f"Failed to generate basic pattern: {e}")
            return False

def generate_notes_for_song(song_path, output_path, template_path=None, generator_type=None):
    """
    User-friendly interface for generating notes for a song.
    
    Parameters:
    song_path: Path to the audio file
    output_path: Path where the notes.csv will be saved
    template_path: Optional path to a template file
    generator_type: Which generator to use (pattern, standard, high_density)
    
    Returns:
    Boolean indicating success
    """
    logger.info(f"Generating notes for {song_path} using {generator_type or 'auto'} generator")
    
    # Make sure paths exist
    if not os.path.exists(song_path):
        logger.error(f"Song file not found: {song_path}")
        return False
    
    # Create output directory if it doesn't exist
    output_dir = os.path.dirname(output_path)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)
    
    # Call the common generator function
    return generate_notes(song_path, template_path, output_path, generator_type)

# Command line interface
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate note patterns for songs")
    parser.add_argument("song_path", help="Path to the song file")
    parser.add_argument("output_path", help="Path where the notes.csv will be saved")
    parser.add_argument("-t", "--template", help="Optional template file")
    parser.add_argument("-g", "--generator", 
                        choices=["pattern", "standard", "high_density"],
                        help="Generator type to use")
    
    args = parser.parse_args()
    
    # Convert generator type string to constant
    generator_type = None
    if args.generator == "pattern":
        generator_type = GENERATOR_PATTERN
    elif args.generator == "standard":
        generator_type = GENERATOR_STANDARD
    elif args.generator == "high_density":
        generator_type = GENERATOR_HIGH_DENSITY
    
    success = generate_notes_for_song(
        args.song_path, 
        args.output_path, 
        args.template, 
        generator_type
    )
    
    if success:
        print(f"Successfully generated notes at {args.output_path}")
    else:
        print("Failed to generate notes")
        sys.exit(1)
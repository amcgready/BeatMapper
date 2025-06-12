"""
Main entry point for note generation across different generators.
Provides a simple interface to generate notes using any available generator.
"""
from pathlib import Path
import os
import logging
import argparse

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
    
    # Import our new beat matcher
    try:
        from .beat_matched_generator import generate_notes_csv as generate_beat_matched_notes
        BEAT_MATCHER_AVAILABLE = True
    except ImportError as e:
        logger.warning(f"Beat matcher not available: {e}")
        BEAT_MATCHER_AVAILABLE = False
        
    # Import advanced MP3 analyzer if available
    try:
        from .advanced_mp3_analyzer import generate_enhanced_notes
        ADVANCED_ANALYZER_AVAILABLE = True
    except ImportError:
        logger.warning("Advanced MP3 analyzer not available")
        ADVANCED_ANALYZER_AVAILABLE = False
        
except ImportError as e:
    logger.error(f"Failed to import note_generator_common: {e}")
    
    # Define constants if import fails
    GENERATOR_PATTERN = "pattern"
    GENERATOR_STANDARD = "standard" 
    GENERATOR_HIGH_DENSITY = "high_density"
    BEAT_MATCHER_AVAILABLE = False
    ADVANCED_ANALYZER_AVAILABLE = False

# Add new generator type constants
GENERATOR_BEAT_MATCHED = "beat_matched"
GENERATOR_ADVANCED_MP3 = "advanced_mp3"

def generate_notes_for_song(song_path, output_path, template_path=None, generator_type=None, 
                           midi_reference=None):
    """
    User-friendly interface for generating notes for a song.
    
    Parameters:
    song_path: Path to the audio file
    output_path: Path where the notes.csv will be saved
    template_path: Optional path to a template file
    generator_type: Which generator to use (pattern, standard, high_density, beat_matched, advanced_mp3)
    midi_reference: Optional path to a MIDI reference file
    
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
    
    # Use advanced MP3 analyzer if requested
    if generator_type == GENERATOR_ADVANCED_MP3 and ADVANCED_ANALYZER_AVAILABLE:
        logger.info("Using advanced MP3 analyzer for high-accuracy mapping")
        return generate_enhanced_notes(song_path, output_path)
    
    # Use beat-matched generator if requested
    if generator_type == GENERATOR_BEAT_MATCHED and BEAT_MATCHER_AVAILABLE:
        logger.info("Using beat-matched generator for accurate tempo synchronization")
        return generate_beat_matched_notes(song_path, template_path, output_path)
    
    # Otherwise call the common generator function
    return generate_notes(song_path, template_path, output_path, generator_type)

# Command line interface
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate note patterns for songs")
    parser.add_argument("song_path", help="Path to the song file")
    parser.add_argument("output_path", help="Path where the notes.csv will be saved")
    parser.add_argument("-t", "--template", help="Optional template file")
    parser.add_argument("-g", "--generator", 
                        choices=["pattern", "standard", "high_density", "beat_matched", "advanced_mp3"],
                        default="advanced_mp3",  # Make advanced the default
                        help="Generator type to use")
    parser.add_argument("-m", "--midi-reference", 
                        help="Path to MIDI reference file (for comparison)")
    
    args = parser.parse_args()
    
    # Convert generator type string to constant
    generator_type = None
    if args.generator == "pattern":
        generator_type = GENERATOR_PATTERN
    elif args.generator == "standard":
        generator_type = GENERATOR_STANDARD
    elif args.generator == "high_density":
        generator_type = GENERATOR_HIGH_DENSITY
    elif args.generator == "beat_matched":
        generator_type = GENERATOR_BEAT_MATCHED
    elif args.generator == "advanced_mp3":
        generator_type = GENERATOR_ADVANCED_MP3
    
    success = generate_notes_for_song(
        args.song_path, 
        args.output_path, 
        args.template, 
        generator_type,
        args.midi_reference
    )
    
    if success:
        print(f"Successfully generated notes at {args.output_path}")
        
        # If MIDI reference provided, compare results
        if args.midi_reference and os.path.exists(args.midi_reference):
            try:
                from .test_accuracy import compare_notes
                compare_notes(args.output_path, args.midi_reference)
            except ImportError:
                print("Note comparison not available")
    else:
        print("Failed to generate notes")
        sys.exit(1)
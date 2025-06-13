"""
Main entry point for note generation across different generators.
Provides a simple interface to generate notes using any available generator.
"""
from pathlib import Path
import os
import logging
import argparse
import sys

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
        
    # Import MIDI-aligned beat matcher if available
    try:
        from .midi_beat_matcher import generate_notes_csv as generate_midi_aligned_notes
        MIDI_ALIGNED_AVAILABLE = True
    except ImportError as e:
        logger.warning(f"MIDI-aligned beat matcher not available: {e}")
        MIDI_ALIGNED_AVAILABLE = False
        
except ImportError as e:
    logger.error(f"Failed to import note_generator_common: {e}")
    
    # Define constants if import fails
    GENERATOR_PATTERN = "pattern"
    GENERATOR_STANDARD = "standard" 
    GENERATOR_HIGH_DENSITY = "high_density"
    BEAT_MATCHER_AVAILABLE = False
    ADVANCED_ANALYZER_AVAILABLE = False
    MIDI_ALIGNED_AVAILABLE = False

# Add new generator type constants
GENERATOR_BEAT_MATCHED = "beat_matched"
GENERATOR_ADVANCED_MP3 = "advanced_mp3"
GENERATOR_MIDI_ALIGNED = "midi_aligned"

def generate_notes_for_song(song_path, output_path, template_path=None, generator_type=None, 
                           midi_reference=None):
    """
    User-friendly interface for generating notes for a song.
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
    
    # If we have a MIDI reference, use the advanced_mp3_analyzer by default
    if midi_reference and os.path.exists(midi_reference):
        logger.info("Using enhanced MP3 analysis with MIDI calibration")
        try:
            from .advanced_mp3_analyzer import generate_enhanced_notes
            result = generate_enhanced_notes(song_path, output_path, midi_reference)
            
            # Apply additional enhancements
            if result:
                try:
                    from .midi_timing_enhancer import enhance_notes_with_midi_timing
                    enhance_notes_with_midi_timing(output_path, output_path, midi_reference)
                except ImportError:
                    logger.warning("Timing enhancer not available")
            
            return result
        except ImportError:
            logger.warning("Advanced MP3 analyzer not available")
    
    # Use midi_beat_matcher if available (regardless of generator_type)
    try:
        from .midi_beat_matcher import generate_notes_csv as generate_midi_aligned_notes
        logger.info("Using MIDI-aligned beat matcher")
        return generate_midi_aligned_notes(song_path, template_path, output_path, midi_reference)
    except ImportError:
        logger.warning("MIDI-aligned beat matcher not available")
    
    # Use beat-matched generator if requested
    if generator_type == GENERATOR_BEAT_MATCHED and BEAT_MATCHER_AVAILABLE:
        logger.info("Using beat-matched generator for accurate tempo synchronization")
        return generate_beat_matched_notes(song_path, template_path, output_path)
    
    # Otherwise call the common generator function
    try:
        if midi_reference and generator_type is None:
            # If we have a MIDI reference but not using advanced generator,
            # use high density as it produces more notes
            logger.info("Using high density generator with MIDI reference")
            result = generate_notes(song_path, template_path, output_path, GENERATOR_HIGH_DENSITY)
            
            # Try to enhance notes with MIDI reference if generate_notes succeeded
            if result:
                try:
                    from .midi_style_enhancer import enhance_generated_notes
                    logger.info("Enhancing generated notes with MIDI reference")
                    enhance_generated_notes(output_path, None, midi_reference)
                except ImportError:
                    logger.warning("MIDI enhancer not available")
                    
            return result
        else:
            return generate_notes(song_path, template_path, output_path, generator_type)
    except Exception as e:
        logger.error(f"Note generation failed: {str(e)}")
        return False

# Command line interface
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate note patterns for songs")
    parser.add_argument("song_path", help="Path to the song file")
    parser.add_argument("output_path", help="Path where the notes.csv will be saved")
    parser.add_argument("-t", "--template", help="Optional template file")
    parser.add_argument("-g", "--generator", 
                        choices=["pattern", "standard", "high_density", "beat_matched", "advanced_mp3", "midi_aligned"],
                        default=None,
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
    elif args.generator == "midi_aligned":
        generator_type = GENERATOR_MIDI_ALIGNED
    
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
                from .midi_reference_matcher import compare_note_density
                comparison = compare_note_density(args.output_path, args.midi_reference)
                
                print("\nNote generation statistics:")
                print(f"Generated: {comparison['generated_count']} notes")
                print(f"Reference: {comparison['reference_count']} notes")
                print(f"Difference: {comparison['difference']} notes")
                print(f"Ratio: {comparison['ratio']:.2f}x")
                
                # Show density by section
                print("\nDensity by 10-second sections:")
                for section, stats in comparison['sections'].items():
                    if stats['reference'] > 0:  # Only show sections with reference notes
                        print(f"{section}s: Generated {stats['generated']} vs Reference {stats['reference']} ({stats['ratio']:.2f}x)")
                
            except ImportError:
                print("Note comparison not available")
    else:
        print("Failed to generate notes")
        sys.exit(1)
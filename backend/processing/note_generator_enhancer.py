"""
Module to enhance existing note generators by applying multiple improvements
"""
import os
import logging
import argparse

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def enhance_generated_notes(input_notes_path, output_notes_path=None, audio_path=None, midi_reference_path=None):
    """
    Apply all available enhancements to an existing notes.csv file
    
    Args:
        input_notes_path: Path to input notes.csv
        output_notes_path: Path for enhanced output (defaults to overwrite input)
        audio_path: Path to audio file (for audio analysis enhancements)
        midi_reference_path: Path to MIDI reference file (for timing patterns)
        
    Returns:
        bool: Success or failure
    """
    if output_notes_path is None:
        output_notes_path = input_notes_path
        
    # Get temporary path for intermediate files
    temp_dir = os.path.dirname(output_notes_path)
    temp_file1 = os.path.join(temp_dir, "_temp1_notes.csv")
    temp_file2 = os.path.join(temp_dir, "_temp2_notes.csv")
    
    success = True
    current_input = input_notes_path
    
    # 1. Apply MIDI timing enhancement
    try:
        from .midi_timing_enhancer import enhance_notes_with_midi_timing
        logger.info("Applying MIDI-like timing variations")
        
        if enhance_notes_with_midi_timing(current_input, temp_file1, midi_reference_path):
            current_input = temp_file1
        else:
            logger.warning("MIDI timing enhancement failed, continuing with original")
    except ImportError:
        logger.info("MIDI timing enhancer not available")
    
    # 2. Apply pattern enhancement
    try:
        from .pattern_enhancer import enhance_pattern
        logger.info("Enhancing note patterns")
        
        if enhance_pattern(current_input, temp_file2):
            current_input = temp_file2
        else:
            logger.warning("Pattern enhancement failed, continuing with previous")
    except ImportError:
        logger.info("Pattern enhancer not available")
    
    # 3. Apply any audio analysis based enhancements if audio file provided
    if audio_path and os.path.exists(audio_path):
        try:
            # Try to use advanced audio analysis for density modulation
            # (Implementation would go here, but simplified for now)
            pass
        except Exception as e:
            logger.warning(f"Audio analysis enhancement failed: {e}")
    
    # 4. Write final result to output path
    try:
        import shutil
        if current_input != output_notes_path:
            shutil.copy(current_input, output_notes_path)
    except Exception as e:
        logger.error(f"Failed to write final output: {e}")
        success = False
    
    # Clean up temp files
    for temp_file in [temp_file1, temp_file2]:
        if os.path.exists(temp_file):
            try:
                os.remove(temp_file)
            except:
                pass
    
    return success

def generate_and_enhance_notes(song_path, output_path, template_path=None, 
                               generator_type=None, midi_reference_path=None):
    """
    Generate notes and apply all enhancements
    
    Args:
        song_path: Path to audio file
        output_path: Path for output notes.csv
        template_path: Optional template path
        generator_type: Generator type (standard, pattern, etc.)
        midi_reference_path: Optional MIDI reference path
        
    Returns:
        bool: Success or failure
    """
    try:
        # 1. First generate base notes using existing generator
        from .note_generator import generate_notes_for_song
        
        temp_output = output_path + ".temp"
        if not generate_notes_for_song(song_path, temp_output, template_path, generator_type):
            logger.error("Failed to generate base notes")
            return False
        
        # 2. Enhance the generated notes
        success = enhance_generated_notes(
            temp_output, output_path, song_path, midi_reference_path
        )
        
        # Clean up temp file
        if os.path.exists(temp_output):
            try:
                os.remove(temp_output)
            except:
                pass
        
        return success
        
    except Exception as e:
        logger.error(f"Error in generate_and_enhance_notes: {e}")
        return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Enhance generated notes")
    
    # Mode selection
    subparsers = parser.add_subparsers(dest="mode", help="Mode of operation")
    
    # Enhance existing notes
    enhance_parser = subparsers.add_parser("enhance", help="Enhance existing notes.csv")
    enhance_parser.add_argument("input_notes", help="Path to input notes.csv")
    enhance_parser.add_argument("--output", help="Path for output (defaults to overwriting input)")
    enhance_parser.add_argument("--audio", help="Path to audio file for additional enhancements")
    enhance_parser.add_argument("--midi", help="Path to MIDI reference file")
    
    # Generate and enhance
    generate_parser = subparsers.add_parser("generate", help="Generate and enhance notes")
    generate_parser.add_argument("song_path", help="Path to audio file")
    generate_parser.add_argument("output_path", help="Path for output notes.csv")
    generate_parser.add_argument("--template", help="Path to optional template file")
    generate_parser.add_argument("--generator", 
                              choices=["standard", "pattern", "high_density", "beat_matched"],
                              default="standard",
                              help="Generator type")
    generate_parser.add_argument("--midi", help="Path to MIDI reference file")
    
    args = parser.parse_args()
    
    if args.mode == "enhance":
        success = enhance_generated_notes(
            args.input_notes,
            args.output,
            args.audio,
            args.midi
        )
    elif args.mode == "generate":
        success = generate_and_enhance_notes(
            args.song_path,
            args.output_path,
            args.template,
            args.generator,
            args.midi
        )
    else:
        parser.print_help()
        exit(1)
    
    if success:
        print(f"Successfully {'enhanced' if args.mode == 'enhance' else 'generated'} notes")
    else:
        print(f"Failed to {'enhance' if args.mode == 'enhance' else 'generate'} notes")
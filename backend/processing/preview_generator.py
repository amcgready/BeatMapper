import os
import logging
import csv
from pydub import AudioSegment

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def generate_preview(input_path, output_path, start_sec=30, duration_sec=30):
    """
    Generate a shorter preview clip from an audio file.
    
    Args:
        input_path: Path to the input audio file (ogg format)
        output_path: Path to save the preview audio file
        start_sec: Start position in seconds (default: 30s)
        duration_sec: Duration of the preview in seconds (default: 30s)
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        logger.info(f"Generating preview from {input_path} to {output_path}")
        logger.info(f"Starting at {start_sec}s for {duration_sec}s duration")
        
        # Ensure the input file exists
        if not os.path.exists(input_path):
            logger.error(f"Input file does not exist: {input_path}")
            return False
            
        # Load the audio file
        audio = AudioSegment.from_file(input_path)
        logger.info(f"Loaded audio file: {len(audio)/1000}s duration")
        
        # Calculate positions in milliseconds
        start_ms = start_sec * 1000
        duration_ms = duration_sec * 1000
        
        # If audio is shorter than start position, start from beginning
        if len(audio) <= start_ms:
            logger.warning(f"Audio file is shorter than start position ({len(audio)/1000}s < {start_sec}s)")
            start_ms = 0
            
        # Calculate end position, ensuring we don't go beyond the audio length
        end_ms = min(start_ms + duration_ms, len(audio))
        
        # Extract the preview segment
        preview = audio[start_ms:end_ms]
        logger.info(f"Extracted preview segment: {len(preview)/1000}s")
        
        # Create output directory if it doesn't exist
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Export the preview
        preview.export(output_path, format="ogg")
        logger.info(f"Preview saved to {output_path}")
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to generate preview: {str(e)}")
        return False

def generate_notes_csv(song_path, template_path, output_path):
    """
    Generate a notes.csv file that matches the Drums Rock template format
    
    Args:
        song_path: Path to the audio file
        template_path: Path to a template file (optional)
        output_path: Path to save the notes.csv file
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        logger.info(f"Generating notes.csv for preview: {os.path.basename(song_path)}")
        
        # Try to use our existing note generator
        try:
            from .note_generator import generate_notes_for_song
            logger.info("Using note_generator for preview notes generation")
            return generate_notes_for_song(
                song_path=song_path,
                output_path=output_path,
                template_path=template_path,
                generator_type="standard"
            )
        except ImportError:
            # Fallback to direct import of pattern generator
            try:
                from .pattern_notes_generator import generate_notes_csv as pattern_generate
                logger.info("Using pattern_notes_generator directly")
                return pattern_generate(song_path, template_path, output_path)
            except ImportError:
                logger.warning("Could not import generators, using basic pattern")
        
        # Fallback to a simple pattern if no generators are available
        with open(output_path, 'w', newline='') as f:
            writer = csv.writer(f)
            # Write header (time, note_type, enemy_type, color1, color2, aux)
            writer.writerow(["time", "note", "enemy", "color1", "color2", "aux"])
            
            # Create a simple pattern for the preview
            song_duration = 30  # Default to 30 seconds for preview
            pattern_duration = 2.0  # 2 seconds per pattern
            current_time = 0.0
            
            while current_time < song_duration:
                # Basic kick drum on 1 and 3
                writer.writerow([round(current_time, 2), "kick", 1, 1, 3, 1])
                writer.writerow([round(current_time + 1.0, 2), "kick", 1, 1, 3, 1])
                
                # Snare on 2 and 4
                writer.writerow([round(current_time + 0.5, 2), "snare", 1, 2, 4, 1])
                writer.writerow([round(current_time + 1.5, 2), "snare", 1, 2, 4, 1])
                
                # Hi-hats on eighth notes
                for i in range(8):
                    writer.writerow([round(current_time + i*0.25, 2), "hihat", 1, 3, 5, 1])
                
                # Add crash at the beginning
                if current_time == 0.0:
                    writer.writerow([0.0, "crash", 2, 5, 6, 5])
                
                current_time += pattern_duration
        
        logger.info(f"Generated simple notes.csv for preview at {output_path}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to generate notes.csv for preview: {str(e)}")
        return False

def generate_preview_package(song_path, output_dir=None, start_sec=30, duration_sec=30):
    """
    Generate a complete preview package with both audio and notes.csv
    
    Args:
        song_path: Path to the input audio file
        output_dir: Directory to save the preview files (defaults to song directory)
        start_sec: Start position in seconds
        duration_sec: Duration in seconds
        
    Returns:
        tuple: (success, preview_audio_path, preview_notes_path)
    """
    try:
        # If output_dir is not specified, use the song directory
        if not output_dir:
            output_dir = os.path.dirname(song_path)
        
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        # Define output paths
        song_name = os.path.splitext(os.path.basename(song_path))[0]
        preview_audio_path = os.path.join(output_dir, f"{song_name}_preview.ogg")
        preview_notes_path = os.path.join(output_dir, f"{song_name}_notes.csv")
        
        # Generate audio preview
        audio_success = generate_preview(song_path, preview_audio_path, start_sec, duration_sec)
        
        # Generate notes.csv
        notes_success = generate_notes_csv(song_path, None, preview_notes_path)
        
        success = audio_success and notes_success
        
        if success:
            logger.info(f"Preview package generated successfully")
        else:
            logger.error("Failed to generate complete preview package")
            
        return (success, preview_audio_path, preview_notes_path)
        
    except Exception as e:
        logger.error(f"Failed to generate preview package: {str(e)}")
        return (False, None, None)

if __name__ == "__main__":
    import argparse
        
    parser = argparse.ArgumentParser(description="Generate audio previews for songs")
    parser.add_argument("input_path", help="Path to the input audio file")
    parser.add_argument("output_path", help="Path to save the preview audio file")
    parser.add_argument("--start", type=float, default=30.0, help="Start position in seconds (default: 30s)")
    parser.add_argument("--duration", type=float, default=30.0, help="Duration of preview in seconds (default: 30s)")
    parser.add_argument("--package", action="store_true", help="Generate a complete preview package with notes.csv")
    
    args = parser.parse_args()
    
    if args.package:
        success, audio_path, notes_path = generate_preview_package(
            args.input_path, 
            os.path.dirname(args.output_path),
            args.start, 
            args.duration
        )
        if success:
            print(f"Preview package generated successfully:")
            print(f" - Audio: {audio_path}")
            print(f" - Notes: {notes_path}")
    else:
        if generate_preview(args.input_path, args.output_path, args.start, args.duration):
            print(f"Preview generated successfully: {args.output_path}")
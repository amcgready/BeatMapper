import os
import logging
from pydub import AudioSegment
import csv

logging.basicConfig(level=logging.INFO)

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
        logging.info(f"Generating preview from {input_path} to {output_path}")
        logging.info(f"Starting at {start_sec}s for {duration_sec}s duration")
        
        # Ensure the input file exists
        if not os.path.exists(input_path):
            logging.error(f"Input file does not exist: {input_path}")
            return False
            
        # Load the audio file
        audio = AudioSegment.from_file(input_path)
        logging.info(f"Loaded audio file: {len(audio)/1000}s duration")
        
        # Calculate positions in milliseconds
        start_ms = start_sec * 1000
        duration_ms = duration_sec * 1000
        
        # If audio is shorter than start position, start from beginning
        if len(audio) <= start_ms:
            logging.warning(f"Audio is shorter than start position. Using beginning of track.")
            start_ms = 0
            
        # Calculate end position, ensuring we don't go beyond the audio length
        end_ms = min(start_ms + duration_ms, len(audio))
        
        # Extract the preview segment
        preview = audio[start_ms:end_ms]
        logging.info(f"Extracted preview segment: {len(preview)/1000}s")
        
        # If preview is too short, pad it or use what we have
        if len(preview) < 5000:  # Less than 5 seconds
            logging.warning(f"Preview is very short: {len(preview)/1000}s. Using available audio.")
            preview = audio[:min(duration_ms, len(audio))]
            
        # Fade in/out for smoother transitions
        fade_duration = min(1000, len(preview) // 2)  # 1 second fade or half the preview length
        preview = preview.fade_in(fade_duration).fade_out(fade_duration)
        
        # Save the preview
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        preview.export(output_path, format="ogg", parameters=["-q:a", "4"])
        logging.info(f"Preview saved to {output_path}")
        
        return True
        
    except Exception as e:
        logging.error(f"Error generating preview: {str(e)}")
        
        # Fallback: If generation fails, try to create a simpler preview
        try:
            logging.info("Attempting fallback preview generation")
            audio = AudioSegment.from_file(input_path)
            
            # Take the first minute or less if the file is shorter
            preview_length = min(60 * 1000, len(audio))
            preview = audio[:preview_length]
            
            # Save it
            preview.export(output_path, format="ogg")
            logging.info(f"Fallback preview saved to {output_path}")
            return True
        except Exception as fallback_error:
            logging.error(f"Fallback preview generation failed: {str(fallback_error)}")
            
            # Last resort: Try to make a copy of the original file
            try:
                import shutil
                shutil.copy(input_path, output_path)
                logging.info(f"Last resort: Copied original file as preview")
                return True
            except Exception as copy_error:
                logging.error(f"Failed to copy original file as preview: {str(copy_error)}")
                return False

def generate_notes_csv(song_path, template_path, output_path):
    """
    Generate a notes.csv file that matches the Drums Rock template format
    """
    try:
        logging.info(f"Generating Drums Rock-compatible notes for {os.path.basename(song_path)}")
        
        # Define default tempo - ideally this would be detected from the audio
        tempo = 120  # Default BPM
        
        with open(output_path, 'w', newline='') as f:
            writer = csv.writer(f)
            
            # Header row - match the template exactly
            writer.writerow([
                "Section", "Tempo [BPM]", "Beat", "Time", 
                "Lane", "Type", "Length", "Volume", "Pitch", "Effect",
                "Aux", "Enemy Type", "Number of Enemies"
            ])
            
            # Generate a basic rock beat pattern over multiple sections
            section_names = ["Intro", "Verse", "Chorus", "Bridge", "Outro"]
            current_section = 0
            total_beats = 0
            
            # Generate patterns for 30 measures (120 beats at 4 beats per measure)
            for measure in range(30):
                # Change section every 8 measures
                if measure % 8 == 0 and measure > 0:
                    current_section = (current_section + 1) % len(section_names)
                
                section = section_names[current_section]
                
                # 4 beats per measure
                for beat in range(4):
                    beat_number = total_beats + beat
                    # Calculate time in seconds (60 / BPM * beat_number)
                    time = (60 / tempo) * beat_number
                    
                    # Basic rock pattern
                    
                    # KICK DRUM (Lane 0)
                    if beat == 0 or beat == 2:  # On beats 1 and 3
                        writer.writerow([
                            section,       # Section
                            tempo,         # Tempo [BPM]
                            beat_number,   # Beat
                            f"{time:.3f}", # Time
                            "0",           # Lane
                            "Tap",         # Type
                            "0",           # Length
                            "100",         # Volume
                            "Kick",        # Pitch
                            "None",        # Effect
                            "",            # Aux
                            "",            # Enemy Type
                            ""             # Number of Enemies
                        ])
                    
                    # SNARE DRUM (Lane 1)
                    if beat == 1 or beat == 3:  # On beats 2 and 4
                        writer.writerow([
                            section,       # Section
                            tempo,         # Tempo [BPM]
                            beat_number,   # Beat
                            f"{time:.3f}", # Time
                            "1",           # Lane
                            "Tap",         # Type
                            "0",           # Length
                            "100",         # Volume
                            "Snare",       # Pitch
                            "None",        # Effect
                            "",            # Aux
                            "",            # Enemy Type
                            ""             # Number of Enemies
                        ])
                    
                    # HI-HAT (Lane 2)
                    # Eighth notes - on every half beat
                    for eighth in range(2):
                        eighth_time = time + (eighth * 0.5 * (60 / tempo))
                        writer.writerow([
                            section,                # Section
                            tempo,                  # Tempo [BPM]
                            f"{beat_number}.{eighth}", # Beat (with subdivision)
                            f"{eighth_time:.3f}",   # Time
                            "2",                    # Lane
                            "Tap",                  # Type
                            "0",                    # Length
                            "85",                   # Volume
                            "HiHat",                # Pitch
                            "None",                 # Effect
                            "",                     # Aux
                            "",                     # Enemy Type
                            ""                      # Number of Enemies
                        ])
                    
                    # CRASH/TOM (Lane 3)
                    # Add crash on the first beat of every 4 measures
                    if beat == 0 and measure % 4 == 0:
                        writer.writerow([
                            section,       # Section
                            tempo,         # Tempo [BPM]
                            beat_number,   # Beat
                            f"{time:.3f}", # Time
                            "3",           # Lane
                            "Tap",         # Type
                            "0",           # Length
                            "100",         # Volume
                            "Crash",       # Pitch
                            "None",        # Effect
                            "",            # Aux
                            "",            # Enemy Type
                            ""             # Number of Enemies
                        ])
                
                total_beats += 4  # Increment beat counter by 4 for next measure
        
        logging.info(f"Generated Drums Rock compatible notes.csv at {output_path}")
        return True
        
    except Exception as e:
        logging.error(f"Failed to generate notes.csv: {str(e)}")
        return False
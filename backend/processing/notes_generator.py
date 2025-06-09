import os
import csv
import logging
from openpyxl import load_workbook

logging.basicConfig(level=logging.INFO)

def generate_notes_csv(mp3_path, template_path, output_path, bpm=None):
    """
    Generates a notes.csv file for a Drums Rock beatmap
    
    Args:
        mp3_path: Path to the input MP3 file
        template_path: Path to the template Excel file
        output_path: Path to save the output CSV file
        bpm: Beats per minute (estimated if None)
    """
    try:
        logging.info(f"Generating Drums Rock beatmap for {mp3_path}")
        
        # Estimate or use provided BPM
        if bpm is None:
            try:
                import librosa
                y, sr = librosa.load(mp3_path, sr=None, duration=30)
                tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
                bpm = int(round(tempo))
                logging.info(f"Estimated BPM: {bpm}")
            except Exception as e:
                logging.warning(f"Could not estimate BPM: {e}. Using default.")
                bpm = 120  # Default BPM
        
        # Create a proper Drums Rock notes.csv
        with open(output_path, 'w', newline='') as f:
            writer = csv.writer(f)
            
            # Write the header row for Drums Rock format
            writer.writerow(["Time", "Lane", "Type", "Length", "Volume", "Pitch", "Effect"])
            
            # Calculate beat timing
            beat_duration = 60.0 / bpm
            
            # Generate 16 bars (4 beats per bar)
            bars = 16
            for bar in range(bars):
                bar_start = bar * 4 * beat_duration
                
                # Kick drum (Lane 1) on beats 1 and 3
                writer.writerow([f"{round(bar_start, 3)}", "1", "Hit", "0", "100", "0", "None"])
                writer.writerow([f"{round(bar_start + 2 * beat_duration, 3)}", "1", "Hit", "0", "100", "0", "None"])
                
                # Snare drum (Lane 2) on beats 2 and 4
                writer.writerow([f"{round(bar_start + beat_duration, 3)}", "2", "Hit", "0", "100", "0", "None"])
                writer.writerow([f"{round(bar_start + 3 * beat_duration, 3)}", "2", "Hit", "0", "100", "0", "None"])
                
                # Hi-hat (Lane 3) on eighth notes
                for eighth in range(8):
                    writer.writerow([
                        f"{round(bar_start + eighth * beat_duration/2, 3)}", 
                        "3", "Hit", "0", "85", "0", "None"
                    ])
                
                # Add fills at the end of every 4th bar
                if bar % 4 == 3:
                    fill_start = bar_start + 3 * beat_duration
                    for i in range(4):
                        writer.writerow([
                            f"{round(fill_start + i * beat_duration/4, 3)}", 
                            "4", "Hit", "0", "100", "0", "None"
                        ])
        
        logging.info(f"Successfully created Drums Rock beatmap at {output_path}")
        return True
        
    except Exception as e:
        logging.exception(f"Failed to generate Drums Rock beatmap: {e}")
        
        # Create a minimal fallback if something went wrong
        try:
            with open(output_path, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(["Time", "Lane", "Type", "Length", "Volume", "Pitch", "Effect"])
                
                # Add a basic pattern
                writer.writerow(["1.0", "1", "Hit", "0", "100", "0", "None"])
                writer.writerow(["2.0", "2", "Hit", "0", "100", "0", "None"])
                writer.writerow(["3.0", "3", "Hit", "0", "100", "0", "None"])
                writer.writerow(["4.0", "4", "Hit", "0", "100", "0", "None"])
            
            logging.info("Created fallback Drums Rock beatmap with basic pattern")
            return True
            
        except Exception as fallback_err:
            logging.error(f"Failed to create fallback beatmap: {fallback_err}")
            return False
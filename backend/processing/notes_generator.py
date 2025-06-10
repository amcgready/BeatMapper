import os
import csv
import logging
import random

def generate_notes_csv(song_path, template_path, output_path):
    """
    Generate a notes.csv file in the exact format Drums Rock expects.
    Based on the enemyData CSV format from the template.
    
    Args:
        song_path: Path to the audio file
        template_path: Path to template (can be None)
        output_path: Path where notes.csv will be saved
    """
    try:
        logging.info(f"Generating Drums Rock-compatible notes for {os.path.basename(song_path)}")
        
        # Determine song duration (ideally from audio file, but using a default for now)
        song_duration = 180.0  # 3 minutes in seconds
        
        # Create the notes.csv file with the exact format from the enemyData template
        with open(output_path, 'w', newline='') as f:
            writer = csv.writer(f)
            
            # Header row - exactly as in the template
            writer.writerow(["Time [s]", "Enemy Type", "Aux Color 1", "Aux Color 2", "Nº Enemies", "interval", "Aux"])
            
            # Generate a basic pattern based on the template
            # Most common pattern from template: Regular beat with enemy type 1, colors 2,2, and Aux 7
            
            # Place enemies every 2.5 seconds for the basic rhythm
            current_time = 0.0
            while current_time < song_duration:
                # Regular enemies (type 1, colors 2,2, Aux 7)
                writer.writerow([f"{current_time:.2f}", "1", "2", "2", "1", "", "7"])
                current_time += 2.5
                
                # Every 10 seconds, add a special enemy (type 2, colors 5,6, Aux 5)
                if int(current_time) % 10 == 0:
                    writer.writerow([f"{current_time:.2f}", "2", "5", "6", "1", "", "5"])
                    current_time += 0.5
                
                # Every 20 seconds, add a sequence of timed enemies (type 3 with interval)
                if int(current_time) % 20 == 0:
                    writer.writerow([f"{current_time:.2f}", "3", "2", "2", "1", "2", "7"])
                    current_time += 2.0
                
                # Add variety with some random enemy types
                if random.random() < 0.3:  # 30% chance
                    writer.writerow([f"{(current_time + 0.63):.2f}", "1", "1", "1", "1", "", "6"])
                
                # Add occasional clusters of enemies
                if random.random() < 0.1 and current_time > 30:  # 10% chance after 30 seconds
                    base = current_time
                    writer.writerow([f"{base:.2f}", "2", "2", "4", "1", "", "7"])
                    writer.writerow([f"{(base + 0.32):.2f}", "2", "2", "4", "1", "", "7"])
                    writer.writerow([f"{(base + 0.63):.2f}", "2", "2", "4", "1", "", "7"])
        
        logging.info(f"Generated Drums Rock compatible notes.csv at {output_path}")
        return True
        
    except Exception as e:
        logging.error(f"Failed to generate notes.csv: {str(e)}")
        return False
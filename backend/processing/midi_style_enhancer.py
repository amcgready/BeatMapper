"""
Main script for enhancing note generation with MIDI-like characteristics
"""
import os
import logging
import argparse
import csv

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Import our enhancement modules
try:
    from .midi_timing_enhancer import enhance_notes_with_midi_patterns
    from .pattern_enhancer import add_fills_and_variations
except ImportError:
    # Handle relative import when running as script
    try:
        import sys
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from backend.processing.midi_timing_enhancer import enhance_notes_with_midi_patterns
        from backend.processing.pattern_enhancer import add_fills_and_variations
    except ImportError as e:
        logger.error(f"Failed to import enhancement modules: {e}")
        enhance_notes_with_midi_patterns = None
        add_fills_and_variations = None

def enhance_generated_notes(notes_csv_path, midi_reference_path=None):
    """
    Enhance a notes.csv file with MIDI-like characteristics
    
    Args:
        notes_csv_path: Path to the notes.csv file to enhance
        midi_reference_path: Optional path to a reference MIDI CSV file
        
    Returns:
        bool: True if enhancements were applied successfully
    """
    try:
        logger.info(f"Enhancing notes at {notes_csv_path}")
        
        if not os.path.exists(notes_csv_path):
            logger.error(f"Notes file not found: {notes_csv_path}")
            return False
            
        # Make backup of original file
        backup_path = notes_csv_path + ".bak"
        with open(notes_csv_path, 'r') as src, open(backup_path, 'w') as dst:
            dst.write(src.read())
            
        # Apply enhancements
        success = True
        
        # 1. Add fills and pattern variations
        if add_fills_and_variations:
            if not add_fills_and_variations(notes_csv_path):
                logger.warning("Failed to add fills and variations")
                success = False
        
        # 2. Add micro-timing variations based on MIDI reference
        if enhance_notes_with_midi_patterns:
            if not enhance_notes_with_midi_patterns(notes_csv_path, midi_reference_path):
                logger.warning("Failed to add MIDI-like timing")
                success = False
        
        if success:
            logger.info("Successfully enhanced notes with MIDI-like characteristics")
        else:
            logger.warning("Some enhancements failed")
            
        return success
    
    except Exception as e:
        logger.error(f"Error enhancing notes: {e}")
        return False

def post_process_notes_csv(notes_csv_path):
    """
    Apply post-processing to a notes.csv file to ensure it meets game requirements
    """
    try:
        # Read all notes
        all_rows = []
        with open(notes_csv_path, 'r') as f:
            reader = csv.reader(f)
            header = next(reader)
            all_rows = list(reader)
        
        if not all_rows:
            logger.warning("No notes found in file")
            return False
        
        # Track changes
        changes = {
            "spacing_fixed": 0,
            "invalid_removed": 0
        }
        
        # Sort by time
        all_rows.sort(key=lambda row: float(row[0]) if row and len(row) > 0 and row[0].replace('.', '').isdigit() else 0)
        
        # Ensure minimum spacing (50ms) between notes
        processed_rows = []
        prev_time = 0
        
        for row in all_rows:
            if len(row) >= 7:
                try:
                    time = float(row[0])
                    
                    # Fix spacing if needed
                    if prev_time > 0 and time - prev_time < 0.05:
                        time = prev_time + 0.05
                        row[0] = f"{time:.2f}"
                        changes["spacing_fixed"] += 1
                    
                    prev_time = time
                    processed_rows.append(row)
                except ValueError:
                    changes["invalid_removed"] += 1
            else:
                changes["invalid_removed"] += 1
        
        # Write back to file
        with open(notes_csv_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(header)
            writer.writerows(processed_rows)
        
        logger.info(f"Post-processing complete: {changes['spacing_fixed']} spacing issues fixed, {changes['invalid_removed']} invalid rows removed")
        return True
        
    except Exception as e:
        logger.error(f"Error in post-processing: {e}")
        return False

# Command line interface
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Enhance notes.csv files with MIDI-like characteristics")
    parser.add_argument("notes_csv_path", help="Path to the notes.csv file to enhance")
    parser.add_argument("--midi-reference", help="Optional path to a reference MIDI CSV file")
    
    args = parser.parse_args()
    
    if enhance_notes_with_midi_patterns and add_fills_and_variations:
        success = enhance_generated_notes(args.notes_csv_path, args.midi_reference)
        if success:
            post_process_notes_csv(args.notes_csv_path)
            print("Enhancement completed successfully!")
        else:
            print("Enhancement failed.")
    else:
        print("Required enhancement modules not available.")
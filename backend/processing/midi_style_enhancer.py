"""
Main script for enhancing note generation with MIDI-like characteristics
"""
import os
import sys
import logging
import argparse
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Import our enhancement modules
try:
    from .midi_timing_enhancer import enhance_notes_with_midi_timing
    from .midi_reference_matcher import load_midi_reference, apply_midi_reference_patterns
    from .midi_pattern_extractor import extract_patterns, rebuild_patterns_as_notes
    
    ENHANCERS_AVAILABLE = True
except ImportError:
    logger.warning("MIDI enhancer modules not available, using limited functionality")
    ENHANCERS_AVAILABLE = False

def enhance_generated_notes(notes_csv_path, output_path=None, midi_reference_path=None):
    """
    Apply MIDI-like characteristics to generated note files
    
    Args:
        notes_csv_path: Path to generated notes.csv
        output_path: Path for enhanced output (defaults to overwrite input)
        midi_reference_path: Optional path to MIDI reference file
        
    Returns:
        bool: True if successful
    """
    if not output_path:
        output_path = notes_csv_path
        
    if not ENHANCERS_AVAILABLE:
        logger.error("MIDI enhancer modules not available")
        return False
        
    try:
        logger.info(f"Enhancing notes with MIDI characteristics: {notes_csv_path}")
        
        # Create temporary files for each stage
        temp_dir = os.path.dirname(output_path)
        temp_density = os.path.join(temp_dir, "temp_density.csv")
        temp_timing = os.path.join(temp_dir, "temp_timing.csv")
        
        # Step 1: First adjust note density based on MIDI reference
        if midi_reference_path and Path(midi_reference_path).exists():
            logger.info("Loading MIDI reference patterns")
            midi_patterns = load_midi_reference(midi_reference_path)
            
            if midi_patterns:
                logger.info(f"Applying MIDI reference patterns (target: {midi_patterns['total_notes']} notes)")
                
                # Load the original notes
                import csv
                notes = []
                with open(notes_csv_path, 'r') as f:
                    reader = csv.reader(f)
                    headers = next(reader)
                    for row in reader:
                        if len(row) >= 6:
                            notes.append(row)
                
                # Apply pattern matching
                enhanced_notes = apply_midi_reference_patterns(notes, midi_patterns)
                
                # Write to temp file for next stage
                with open(temp_density, 'w', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow(headers)
                    writer.writerows(enhanced_notes)
                    
                density_file = temp_density
            else:
                logger.warning("No MIDI patterns found in reference, skipping density matching")
                density_file = notes_csv_path
        else:
            logger.info("No MIDI reference provided, skipping density matching")
            density_file = notes_csv_path
            
        # Step 2: Apply MIDI-like timing variations
        logger.info("Applying MIDI-like timing variations")
        timing_success = enhance_notes_with_midi_timing(
            density_file, 
            temp_timing, 
            midi_reference_path
        )
        
        if not timing_success:
            logger.warning("Timing enhancement failed, using density-only result")
            timing_file = density_file
        else:
            timing_file = temp_timing
            
        # Step 3: Final post-processing
        success = post_process_notes_csv(timing_file, output_path)
        
        # Clean up temp files
        try:
            if os.path.exists(temp_density) and temp_density != notes_csv_path:
                os.remove(temp_density)
            if os.path.exists(temp_timing) and temp_timing != output_path:
                os.remove(temp_timing)
        except Exception as e:
            logger.warning(f"Failed to clean up temp files: {e}")
        
        logger.info(f"Enhanced notes saved to: {output_path}")
        return success
        
    except Exception as e:
        logger.error(f"Failed to enhance notes: {e}")
        return False

def post_process_notes_csv(notes_csv_path, output_path=None):
    """
    Perform final post-processing on notes.csv
    - Ensure proper formatting
    - Remove any duplicate timestamps
    - Check for any issues
    
    Args:
        notes_csv_path: Path to input notes.csv
        output_path: Path to save processed notes (defaults to overwrite)
        
    Returns:
        bool: True if successful
    """
    if not output_path:
        output_path = notes_csv_path
        
    try:
        import csv
        
        # Read notes
        notes = []
        with open(notes_csv_path, 'r') as f:
            reader = csv.reader(f)
            headers = next(reader)
            
            for row in reader:
                if len(row) >= 6:
                    notes.append(row)
                    
        if not notes:
            logger.warning(f"No valid notes found in {notes_csv_path}")
            return False
            
        # Sort by time
        notes.sort(key=lambda x: float(x[0]))
        
        # Remove duplicates
        processed = []
        last_time = -1.0
        for note in notes:
            time = float(note[0])
            
            # Skip exact duplicates
            if abs(time - last_time) < 0.001:
                continue
                
            # Format time to 2 decimal places
            note[0] = f"{time:.2f}"
            
            processed.append(note)
            last_time = time
            
        # Write to output
        with open(output_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            writer.writerows(processed)
            
        logger.info(f"Post-processed {len(processed)} notes")
        return True
        
    except Exception as e:
        logger.error(f"Error in post-processing: {e}")
        return False

# Command line interface
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Enhance notes with MIDI-like characteristics")
    parser.add_argument("input", help="Path to input notes.csv")
    parser.add_argument("-o", "--output", help="Path to output (defaults to overwrite input)")
    parser.add_argument("-m", "--midi", help="Path to MIDI reference file")
    parser.add_argument("--analyze-only", action="store_true", help="Only analyze MIDI file, don't enhance notes")
    parser.add_argument("--rebuild-patterns", help="Rebuild patterns as CSV at specified path")
    
    args = parser.parse_args()
    
    # Handle analyze-only mode
    if args.analyze_only and args.midi:
        # Just analyze the MIDI file
        from .midi_pattern_extractor import extract_patterns
        
        output_json = os.path.splitext(args.midi)[0] + "_patterns.json"
        patterns = extract_patterns(args.midi, output_json)
        
        # Rebuild patterns if requested
        if args.rebuild_patterns:
            rebuild_patterns_as_notes(patterns, args.rebuild_patterns)
            
        sys.exit(0)
    
    # Normal enhancement mode
    if not args.midi:
        print("Warning: No MIDI reference provided. Enhancement will be limited.")
    
    if enhance_generated_notes(args.input, args.output, args.midi):
        print("Successfully enhanced notes with MIDI-like characteristics")
    else:
        print("Failed to enhance notes")
        sys.exit(1)
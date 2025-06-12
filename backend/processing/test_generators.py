"""
Test utility to verify that all note generators are working properly.
"""
import os
import logging
import tempfile
import argparse
import sys

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_generator(generator_name, input_audio):
    """
    Test a specific generator with the given audio file.
    
    Args:
        generator_name: Name of the generator ('pattern', 'standard', 'high_density')
        input_audio: Path to an audio file
        
    Returns:
        bool: True if successful, False if failed
    """
    try:
        # Create a temporary output directory
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create output path for notes
            output_path = os.path.join(temp_dir, f"{generator_name}_test_notes.csv")
            
            logger.info(f"Testing {generator_name} generator with {os.path.basename(input_audio)}")
            
            # Import the appropriate generator
            if generator_name == "pattern":
                from backend.processing.pattern_notes_generator import generate_notes_csv
            elif generator_name == "standard":
                from backend.processing.notes_generator import generate_notes_csv
            elif generator_name == "high_density":
                from backend.processing.high_density_notes_generator import generate_notes_csv
            else:
                from backend.processing.note_generator import generate_notes_for_song
                return generate_notes_for_song(input_audio, output_path, generator_type=generator_name)
            
            # Call the generator
            success = generate_notes_csv(input_audio, None, output_path)
            
            # Check results
            if success and os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                # Count lines in the output file
                with open(output_path, 'r') as f:
                    line_count = sum(1 for _ in f)
                
                logger.info(f"Success! Generated {line_count-1} notes with {generator_name} generator")
                return True
            else:
                logger.error(f"Failed to generate notes with {generator_name} generator")
                return False
                
    except Exception as e:
        logger.error(f"Error testing {generator_name} generator: {e}")
        return False

def test_all_generators(input_audio):
    """
    Test all available generators with the given audio file.
    
    Args:
        input_audio: Path to an audio file
        
    Returns:
        dict: Results for each generator
    """
    results = {}
    
    # Test each generator
    generators = ["pattern", "standard", "high_density"]
    for generator in generators:
        results[generator] = test_generator(generator, input_audio)
    
    # Test the integrated generator
    try:
        from backend.processing.note_generator import generate_notes_for_song
        
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = os.path.join(temp_dir, "integrated_test_notes.csv")
            success = generate_notes_for_song(input_audio, output_path)
            results["integrated"] = success
    except Exception as e:
        logger.error(f"Error testing integrated generator: {e}")
        results["integrated"] = False
    
    return results

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test note generators")
    parser.add_argument("input_audio", help="Path to an audio file for testing")
    parser.add_argument("--generator", choices=["pattern", "standard", "high_density", "all"],
                      default="all", help="Which generator to test")
    
    args = parser.parse_args()
    
    if not os.path.exists(args.input_audio):
        logger.error(f"Input audio file not found: {args.input_audio}")
        sys.exit(1)
    
    if args.generator == "all":
        results = test_all_generators(args.input_audio)
        
        # Print summary
        print("\n=== Generator Test Results ===")
        for generator, success in results.items():
            status = "✓ PASSED" if success else "✗ FAILED"
            print(f"{generator:12} {status}")
        
        # Exit with error code if any generator failed
        if not all(results.values()):
            sys.exit(1)
    else:
        success = test_generator(args.generator, args.input_audio)
        if not success:
            sys.exit(1)
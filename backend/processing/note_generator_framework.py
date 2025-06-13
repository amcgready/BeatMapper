"""
Improved framework for managing multiple note generators with fallbacks and error handling
"""
import os
import logging
import importlib
import traceback
from enum import Enum
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class GeneratorType(Enum):
    ADVANCED_MP3 = "advanced_mp3"
    BEAT_MATCHED = "beat_matched"
    HIGH_DENSITY = "high_density"
    STANDARD = "standard"
    PATTERN = "pattern"
    FALLBACK = "fallback"

class GeneratorManager:
    """
    Manages multiple note generators with fallback mechanisms
    """
    
    def __init__(self, song_path, output_path=None, template_path=None):
        """
        Initialize the generator manager
        
        Args:
            song_path: Path to audio file
            output_path: Path for output notes.csv (defaults to song dir)
            template_path: Optional path to template file
        """
        self.song_path = Path(song_path)
        self.song_name = self.song_path.stem
        
        if output_path:
            self.output_path = Path(output_path)
        else:
            self.output_path = self.song_path.parent / f"{self.song_name}_notes.csv"
            
        self.template_path = template_path
        
        # Keep track of attempted generators
        self.attempted = set()
        self.succeeded = None
        
    def generate_notes(self, generator_type=None, fallback=True):
        """
        Generate notes using specified generator with fallbacks if needed
        
        Args:
            generator_type: Type of generator to use (None for auto-select)
            fallback: Whether to use fallbacks if specified generator fails
            
        Returns:
            bool: Success or failure
        """
        # Auto-select if not specified
        if not generator_type:
            generator_type = self._auto_select_generator()
        
        # Convert string to enum if needed
        if isinstance(generator_type, str):
            try:
                generator_type = GeneratorType(generator_type)
            except ValueError:
                logger.warning(f"Unknown generator type: {generator_type}")
                generator_type = GeneratorType.BEAT_MATCHED
        
        # Try the specified generator
        success = self._try_generator(generator_type)
        
        # If failed and fallbacks are enabled, try alternatives
        if not success and fallback:
            return self._try_fallbacks(generator_type)
            
        return success
    
    def _auto_select_generator(self):
        """Select the best generator based on available libraries and song characteristics"""
        # Check for required libraries
        advanced_available = self._check_module_available("librosa")
        
        # Default order based on quality
        if advanced_available:
            return GeneratorType.ADVANCED_MP3
        else:
            return GeneratorType.BEAT_MATCHED
    
    def _try_generator(self, generator_type):
        """Try to use a specific generator"""
        if generator_type in self.attempted:
            logger.debug(f"Already attempted {generator_type.value}")
            return False
            
        self.attempted.add(generator_type)
        
        try:
            logger.info(f"Trying {generator_type.value} generator for {self.song_name}")
            
            # Import the appropriate generator module
            if generator_type == GeneratorType.ADVANCED_MP3:
                from .advanced_mp3_analyzer import generate_enhanced_notes
                success = generate_enhanced_notes(self.song_path, self.output_path)
                
            elif generator_type == GeneratorType.BEAT_MATCHED:
                from .beat_matched_generator import generate_notes_csv
                success = generate_notes_csv(self.song_path, self.template_path, self.output_path)
                
            elif generator_type == GeneratorType.HIGH_DENSITY:
                from .high_density_notes_generator import generate_notes_csv
                success = generate_notes_csv(self.song_path, self.template_path, self.output_path)
                
            elif generator_type == GeneratorType.STANDARD:
                from .notes_generator import generate_notes_csv
                success = generate_notes_csv(self.song_path, self.template_path, self.output_path)
                
            elif generator_type == GeneratorType.PATTERN:
                from .pattern_notes_generator import generate_notes_csv
                success = generate_notes_csv(self.song_path, self.template_path, self.output_path)
                
            elif generator_type == GeneratorType.FALLBACK:
                success = self._generate_fallback_notes()
            
            else:
                logger.error(f"Unknown generator type: {generator_type}")
                return False
            
            if success:
                logger.info(f"Successfully generated notes using {generator_type.value}")
                self.succeeded = generator_type
            else:
                logger.warning(f"Failed to generate notes using {generator_type.value}")
                
            return success
            
        except Exception as e:
            logger.error(f"Error using {generator_type.value} generator: {str(e)}")
            logger.debug(traceback.format_exc())
            return False
    
    def _try_fallbacks(self, failed_type):
        """Try fallback generators in order of preference"""
        # Define fallback chain based on which generator failed
        fallback_chain = self._get_fallback_chain(failed_type)
        
        # Try each fallback in sequence
        for fallback_type in fallback_chain:
            if fallback_type not in self.attempted:
                success = self._try_generator(fallback_type)
                if success:
                    return True
        
        # If all else fails, use the most basic fallback
        if GeneratorType.FALLBACK not in self.attempted:
            return self._try_generator(GeneratorType.FALLBACK)
            
        logger.error("All generators failed")
        return False
    
    def _get_fallback_chain(self, failed_type):
        """Get the appropriate fallback chain based on which generator failed"""
        if failed_type == GeneratorType.ADVANCED_MP3:
            return [
                GeneratorType.BEAT_MATCHED,
                GeneratorType.STANDARD,
                GeneratorType.PATTERN
            ]
        elif failed_type == GeneratorType.BEAT_MATCHED:
            return [
                GeneratorType.STANDARD,
                GeneratorType.PATTERN
            ]
        elif failed_type in (GeneratorType.HIGH_DENSITY, GeneratorType.STANDARD):
            return [
                GeneratorType.PATTERN
            ]
        else:
            return [GeneratorType.FALLBACK]
    
    def _generate_fallback_notes(self):
        """Generate a very basic set of notes that requires no dependencies"""
        try:
            import csv
            
            # Create output directory if it doesn't exist
            os.makedirs(os.path.dirname(self.output_path), exist_ok=True)
            
            # Write a simple pattern to CSV
            with open(self.output_path, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(["Time [s]", "Enemy Type", "Aux Color 1", "Aux Color 2", "Nº Enemies", "interval", "Aux"])
                
                # Create a basic pattern repeating every 2 seconds
                for t in range(3, 180, 1):  # 3 minutes from 3s to 180s
                    time = t
                    if t % 2 == 0:  # Every 2 seconds
                        writer.writerow([f"{time:.2f}", "1", "2", "2", "1", "", "7"])  # Kick/snare
                    
                    if t % 4 == 0:  # Every 4 seconds
                        writer.writerow([f"{time:.2f}", "2", "5", "6", "1", "", "5"])  # Crash
                    
                    # Add hihat
                    if t % 1 == 0:  # Every second
                        writer.writerow([f"{time:.2f}", "1", "1", "1", "1", "", "6"])  # Hihat
            
            logger.info(f"Generated fallback pattern at {self.output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to generate fallback pattern: {e}")
            return False
    
    @staticmethod
    def _check_module_available(module_name):
        """Check if a Python module is available"""
        try:
            importlib.import_module(module_name)
            return True
        except ImportError:
            return False

def generate_notes_with_framework(song_path, output_path=None, template_path=None, generator_type=None):
    """
    Generate notes using the framework
    
    Args:
        song_path: Path to audio file
        output_path: Path for output notes.csv
        template_path: Optional path to template file
        generator_type: Type of generator to use (None for auto-select)
        
    Returns:
        bool: Success or failure
    """
    manager = GeneratorManager(song_path, output_path, template_path)
    return manager.generate_notes(generator_type)

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate beat-mapped notes using improved framework")
    parser.add_argument("song_path", help="Path to audio file")
    parser.add_argument("--output", help="Path for output notes.csv")
    parser.add_argument("--template", help="Path to template file")
    parser.add_argument("--generator", choices=[t.value for t in GeneratorType], 
                        help="Generator type (default: auto-select)")
    
    args = parser.parse_args()
    
    success = generate_notes_with_framework(
        args.song_path,
        args.output,
        args.template,
        args.generator
    )
    
    if success:
        print("Successfully generated notes")
    else:
        print("Failed to generate notes")
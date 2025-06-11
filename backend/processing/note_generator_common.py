"""
Common utilities and interfaces for note generators.
"""
import os
import csv
import logging
import warnings
import sys
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Try to import numpy
try:
    import numpy as np
except ImportError:
    logger.warning("NumPy not available - some features will be limited")
    # Define a minimal numpy-like module
    class NumpyStub:
        def ceil(self, x):
            return int(x) + (1 if x > int(x) else 0)
        
        def mean(self, x, *args, **kwargs):
            if not x:
                return 0
            return sum(x) / len(x)
            
    np = NumpyStub()

# Generator types
GENERATOR_PATTERN = "pattern"
GENERATOR_STANDARD = "standard"
GENERATOR_HIGH_DENSITY = "high_density"

def check_librosa_available():
    """Check if librosa is available for audio processing"""
    try:
        import librosa
        return True
    except ImportError:
        logger.warning("librosa not available - some features will be limited")
        return False

def get_song_duration(song_path):
    """Get song duration using librosa if available"""
    try:
        import librosa
        y, sr = librosa.load(song_path, sr=None)
        return librosa.get_duration(y=y, sr=sr)
    except:
        logger.warning("Couldn't detect song duration, using default")
        return 180.0  # Default 3 minutes

def get_song_tempo(song_path):
    """Get song tempo using librosa if available"""
    try:
        import librosa
        y, sr = librosa.load(song_path, sr=None)
        tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
        return tempo
    except:
        logger.warning("Couldn't detect song tempo, using default")
        return 120.0  # Default 120 BPM

def select_generator(generator_type=None, song_path=None):
    """
    Select appropriate note generator based on type or song characteristics
    
    Parameters:
    generator_type: String specifying generator type
    song_path: Path to audio file for analysis-based selection
    
    Returns:
    Function reference to the appropriate generator
    """
    # Define a fallback generator function in case we can't find any real ones
    def fallback_generator(song_path, template_path, output_path):
        logger.error("No note generators available - using simple fallback")
        try:
            with open(output_path, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(["Time [s]", "Enemy Type", "Aux Color 1", "Aux Color 2", "Nº Enemies", "interval", "Aux"])
                
                # Generate very basic pattern - one note every 0.5 seconds
                for i in range(360):  # 3 minutes of content at 2 notes per second
                    time = i * 0.5
                    writer.writerow([f"{time:.2f}", "1", "2", "2", "1", "", "7"])
            return True
        except Exception as e:
            logger.error(f"Fallback generator failed: {e}")
            return False

    # Import checking with proper error handling
    def check_module(module_name):
        try:
            __import__(module_name)
            return True
        except ImportError:
            return False
    
    # Check for available generators
    pattern_generator_available = check_module("pattern_notes_generator")
    standard_generator_available = check_module("notes_generator")
    high_density_generator_available = check_module("high_density_notes_generator")
    
    # If type is explicitly specified
    if generator_type:
        if generator_type == GENERATOR_PATTERN and pattern_generator_available:
            try:
                from pattern_notes_generator import generate_notes_csv
                return generate_notes_csv
            except ImportError:
                logger.error("Failed to import pattern_notes_generator")
                
        elif generator_type == GENERATOR_HIGH_DENSITY and high_density_generator_available:
            try:
                from high_density_notes_generator import generate_notes_csv
                return generate_notes_csv
            except ImportError:
                logger.error("Failed to import high_density_notes_generator")
                
        elif generator_type == GENERATOR_STANDARD and standard_generator_available:
            try:
                from notes_generator import generate_notes_csv
                return generate_notes_csv
            except ImportError:
                logger.error("Failed to import notes_generator")
    
    # Auto-select based on song characteristics if song_path provided
    if song_path:
        # Try to detect if the song has a lot of percussion, in which case high density might be better
        try:
            import librosa
            y, sr = librosa.load(song_path, sr=None)
            y_harmonic, y_percussive = librosa.effects.hpss(y)
            
            # If percussive content is high relative to harmonic, use high density
            perc_energy = np.mean(y_percussive**2)
            harm_energy = np.mean(y_harmonic**2)
            
            if perc_energy > harm_energy * 0.8 and high_density_generator_available:
                try:
                    from high_density_notes_generator import generate_notes_csv
                    logger.info("Auto-selected high density generator based on audio analysis")
                    return generate_notes_csv
                except ImportError:
                    pass
        except:
            # If analysis fails, just fall through to default selection
            pass
    
    # Default fallback chain
    if pattern_generator_available:
        try:
            from pattern_notes_generator import generate_notes_csv
            return generate_notes_csv
        except ImportError:
            logger.error("Failed to import pattern_notes_generator")
            
    elif standard_generator_available:
        try:
            from notes_generator import generate_notes_csv
            return generate_notes_csv
        except ImportError:
            logger.error("Failed to import notes_generator")
            
    elif high_density_generator_available:
        try:
            from high_density_notes_generator import generate_notes_csv
            return generate_notes_csv
        except ImportError:
            logger.error("Failed to import high_density_notes_generator")
    
    logger.warning("Using fallback generator as no suitable generators were found")
    return fallback_generator

def generate_notes(song_path, template_path, output_path, generator_type=None):
    """
    Main entry point for note generation.
    Selects and calls the appropriate generator.
    
    Parameters:
    song_path: Path to audio file
    template_path: Path to template file (optional)
    output_path: Where to save the notes.csv
    generator_type: Which generator to use (optional)
    
    Returns:
    Boolean indicating success
    """
    try:
        generator = select_generator(generator_type, song_path)
        return generator(song_path, template_path, output_path)
    except Exception as e:
        logger.error(f"Note generation failed: {str(e)}")
        return False
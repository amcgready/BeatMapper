"""
Common utilities and interfaces for note generators.
"""
from pathlib import Path
import logging
import numpy as np
from .utils import format_time, format_bpm, format_percentage, format_safe

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Generator type constants
GENERATOR_PATTERN = "pattern"
GENERATOR_STANDARD = "standard"
GENERATOR_HIGH_DENSITY = "high_density"
GENERATOR_BEAT_MATCHED = "beat_matched"
GENERATOR_ADVANCED_MP3 = "advanced_mp3"

def format_safe(value, format_spec=''):
    """
    Safely format a value that might be a numpy array or other non-standard type
    
    Args:
        value: The value to format (could be numpy array, float, etc.)
        format_spec: Format specification string
        
    Returns:
        str: Formatted value
    """
    # Handle numpy arrays and numpy scalars
    if isinstance(value, (np.ndarray, np.number)):
        # Convert to Python scalar type
        try:
            return format(value.item(), format_spec)
        except (AttributeError, ValueError):
            # If it's an array with multiple values, convert to list
            if hasattr(value, 'tolist'):
                return format(value.tolist(), format_spec)
            return str(value)
    
    # Try to apply format, fall back to string conversion if that fails
    try:
        return format(value, format_spec)
    except (TypeError, ValueError):
        return str(value)

def select_generator(audio_path=None, specified_generator=None):
    """
    Select the most appropriate generator based on availability and audio characteristics
    
    Args:
        audio_path: Path to audio file (optional)
        specified_generator: Explicitly specified generator type (optional)
        
    Returns:
        str: Selected generator type
    """
    # If generator explicitly specified, use it
    if specified_generator:
        logger.info(f"Using explicitly specified {specified_generator} generator")
        return specified_generator
    
    # Try to determine best generator based on audio file
    if audio_path:
        try:
            # Import here to avoid circular imports
            from .audio_analyzer import analyze_audio_complexity
            complexity = analyze_audio_complexity(audio_path)
            
            if complexity > 0.7:
                logger.info(f"Complex audio detected, using {GENERATOR_BEAT_MATCHED} generator")
                return GENERATOR_BEAT_MATCHED
            elif complexity > 0.4:
                logger.info(f"Moderate complexity audio detected, using {GENERATOR_PATTERN} generator")
                return GENERATOR_PATTERN
            else:
                logger.info(f"Simple audio detected, using {GENERATOR_STANDARD} generator")
                return GENERATOR_STANDARD
                
        except Exception as e:
            logger.warning(f"Failed to analyze audio complexity: {e}")
    
    # Default to beat_matched as it has the best performance
    logger.info(f"Using {GENERATOR_BEAT_MATCHED} generator (default)")
    return GENERATOR_BEAT_MATCHED

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

def add_micro_timing_variations(time_value, amount=0.03):
    """
    Add small timing variations to make notes feel more human
    """
    import random
    variation = random.uniform(-amount, amount)
    return round(time_value + variation, 2)
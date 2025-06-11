"""
Processing package for BeatMapper application.
Contains modules for audio conversion, preview generation and more.
"""

import os
import sys
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
logger.info(f"Processing package initialized from {__file__}")

# Make sure this directory is in the Python path
package_dir = os.path.dirname(os.path.abspath(__file__))
if package_dir not in sys.path:
    sys.path.append(package_dir)
    logger.info(f"Added processing directory to Python path: {package_dir}")

# Import the main function from note_generator
try:
    from .note_generator import generate_notes_for_song
except ImportError as e:
    logger.warning(f"Could not import note_generator: {e}")
    
    # Define a fallback function
    def generate_notes_for_song(song_path, output_path, template_path=None, generator_type=None):
        """Fallback function when note_generator is not available"""
        logger.error("Note generator module not available")
        return False
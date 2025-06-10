"""
Processing package for BeatMapper application.
Contains modules for audio conversion, preview generation and more.
"""

import os
import sys
import logging

logger = logging.getLogger(__name__)
logger.info(f"Processing package initialized from {__file__}")

# Make sure this directory is in the Python path
package_dir = os.path.dirname(os.path.abspath(__file__))
if package_dir not in sys.path:
    sys.path.append(package_dir)
    logger.info(f"Added processing directory to Python path: {package_dir}")
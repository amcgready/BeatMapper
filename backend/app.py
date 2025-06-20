import os
import json
import time
import uuid
import shutil
import logging
import sys
import traceback
import tempfile
import sqlite3
from datetime import datetime
import csv
from flask import Flask, request, jsonify, send_file, send_from_directory
from werkzeug.utils import secure_filename
from processing.audio_converter import mp3_to_ogg, convert_to_mp3
from processing.preview_generator import generate_preview
from processing.notes_generator import generate_notes_csv
from processing.info_generator import generate_info_csv
from flask_cors import CORS

# Set up log file path with absolute path
log_file = os.path.abspath(os.path.join(os.path.dirname(__file__), 'beatmapper.log'))
print(f"Setting up logging to file: {log_file}")

# Make sure the directory exists
os.makedirs(os.path.dirname(log_file), exist_ok=True)

# Clear log file on startup
try:
    # Remove the existing log file to start fresh
    if os.path.exists(log_file):
        os.remove(log_file)
        print(f"Previous log file cleared: {log_file}")
    
    # Create a fresh empty log file
    with open(log_file, 'w') as f:
        f.write(f"BeatMapper log started at {datetime.now().isoformat()}\n")
    print(f"Created new log file: {log_file}")
except Exception as e:
    print(f"Error clearing log file: {e}")

# Configure logging with both file and console output
logging.basicConfig(
    level=logging.DEBUG,  # Set to DEBUG for maximum verbosity during troubleshooting
    format='%(asctime)s %(levelname)s %(name)s %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8', mode='a'),
        logging.StreamHandler(sys.stdout)
    ]
)

# Add a test log message
logger = logging.getLogger(__name__)
logger.info("Logging initialized - New session started")
logger.info(f"Log file location: {log_file}")

app = Flask(__name__)
CORS(app)

# Configure Flask logger to use the same handlers
app.logger.handlers = logger.handlers
app.logger.setLevel(logger.level)

app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100 MB upload limit

OUTPUT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../output'))
TEMPLATE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), 'templates/notes_template.xlsx'))

def cleanup_output_dir(days=7):
    """Clean up old temporary files"""
    now = time.time()
    cutoff = now - days * 86400
    for filename in os.listdir(OUTPUT_DIR):
        file_path = os.path.join(OUTPUT_DIR, filename)
        if os.path.isfile(file_path) and ('temp_' in filename or filename.endswith('.zip')):
            if os.path.getmtime(file_path) < cutoff:
                try:
                    os.remove(file_path)
                    logger.info(f"Deleted old file: {filename}")
                except Exception as e:                    logger.error(f"Failed to delete {filename}: {e}")

def parse_artist_title_metadata(title, artist):
    """
    Parse metadata that might have artist and title combined in the title field.
    Handles formats like "Artist - Title" or "Artist: Title"
    
    Args:
        title (str): The title field from metadata
        artist (str): The artist field from metadata
        
    Returns:
        tuple: (parsed_title, parsed_artist)
    """
    # If we already have both title and artist, return as-is
    if title and artist and artist.strip() and not ("unknown" in artist.lower()):
        return title.strip(), artist.strip()
    
    # If title contains common separators, try to split
    if title and any(sep in title for sep in [' - ', ' – ', ' — ', ': ']):
        for separator in [' - ', ' – ', ' — ', ': ']:
            if separator in title:
                parts = title.split(separator, 1)  # Split only on first occurrence
                if len(parts) == 2:
                    potential_artist = parts[0].strip()
                    potential_title = parts[1].strip()
                    
                    # Make sure both parts are not empty and seem reasonable
                    if potential_artist and potential_title and len(potential_artist) > 0 and len(potential_title) > 0:
                        logger.info(f"Parsed '{title}' into artist: '{potential_artist}', title: '{potential_title}'")
                        return potential_title, potential_artist
                break
    
    # If we can't parse or don't have the format, return original values
    return title.strip() if title else "", artist.strip() if artist else ""

def get_db_connection():
    """Create a connection to the SQLite database."""
    db_path = os.path.join(os.path.dirname(__file__), 'beatmapper.db')
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/api/health')
def health():
    return jsonify({"status": "ok"})

@app.route('/api/upload', methods=['POST'])
def upload_file():
    """Handle MP3 upload and beatmap generation"""
    temp_dir = None
    beatmap_dir = None
    
    try:
        logger.info("Upload endpoint called")
        logger.info(f"Request data: {request.form.keys()}")  # Log form data keys
        
        # Check if file was included in the request
        if 'file' not in request.files:
            logger.error("No file part in request")
            return jsonify({"status": "error", "error": "No file part"}), 400
            
        file = request.files['file']
        logger.info(f"Received file: {file.filename}")
        
        if file.filename == '':
            logger.error("No selected file")
            return jsonify({"status": "error", "error": "No selected file"}), 400
          # Check file extension - support multiple audio formats
        supported_extensions = ['.mp3', '.flac', '.wav', '.ogg']
        file_extension = None
        for ext in supported_extensions:
            if file.filename.lower().endswith(ext):
                file_extension = ext
                break
        
        if not file_extension:
            logger.error(f"Invalid file format: {file.filename}")
            return jsonify({"status": "error", "error": "Invalid file format, must be MP3, FLAC, WAV, or OGG"}), 400
            
        # Generate a unique ID for this beatmap
        beatmap_id = str(uuid.uuid4())
        logger.info(f"Generated beatmap ID: {beatmap_id}")
        
        # Create output directory if it doesn't exist
        if not os.path.exists(OUTPUT_DIR):
            logger.info(f"Creating output directory: {OUTPUT_DIR}")
            os.makedirs(OUTPUT_DIR, exist_ok=True)
        
        # Create a directory for this beatmap
        beatmap_dir = os.path.join(OUTPUT_DIR, beatmap_id)
        logger.info(f"Creating beatmap directory: {beatmap_dir}")
        os.makedirs(beatmap_dir, exist_ok=True)
        
        # Create a temp directory for processing
        temp_dir = os.path.join(OUTPUT_DIR, f"temp_{beatmap_id}")
        logger.info(f"Creating temp directory: {temp_dir}")
        os.makedirs(temp_dir, exist_ok=True)
          # First save the audio file to temp directory
        original_audio_path = os.path.join(temp_dir, f'song{file_extension}')
        logger.info(f"Saving audio file to: {original_audio_path}")
        file.save(original_audio_path)
        logger.info(f"Audio file saved successfully: {os.path.getsize(original_audio_path)} bytes")
        
        # Convert to MP3 if needed (for consistent processing)
        mp3_path = os.path.join(temp_dir, 'song.mp3')
        if file_extension != '.mp3':
            logger.info(f"Converting {file_extension} to MP3 for processing")
            try:
                from processing.audio_converter import convert_to_mp3
                convert_to_mp3(original_audio_path, mp3_path)
                logger.info("Audio conversion to MP3 completed")
            except Exception as e:
                logger.error(f"Failed to convert audio to MP3: {e}", exc_info=True)
                return jsonify({"status": "error", "error": f"Failed to convert audio format: {str(e)}"}), 500
        else:
            # If it's already MP3, just copy it
            import shutil
            shutil.copy2(original_audio_path, mp3_path)# Extract metadata from the form
        title = request.form.get('title', '')
        artist = request.form.get('artist', '')
        
        # Parse and clean up title/artist metadata in case they're combined
        parsed_title, parsed_artist = parse_artist_title_metadata(title, artist)
        
        logger.info(f"Original metadata: title='{title}', artist='{artist}'")
        logger.info(f"Parsed metadata: title='{parsed_title}', artist='{parsed_artist}'")
        
        # Use parsed values
        title = parsed_title
        artist = parsed_artist
        
        # Process album art if provided
        artwork_path = os.path.join(beatmap_dir, 'album.jpg')
        if 'artwork' in request.files and request.files['artwork'].filename:
            try:
                artwork_file = request.files['artwork']
                logger.info(f"Saving artwork: {artwork_file.filename}")
                artwork_file.save(artwork_path)
                logger.info(f"Artwork saved to {artwork_path}")
            except Exception as e:
                logger.error(f"Failed to save artwork: {e}", exc_info=True)
                # Create default artwork
                create_default_artwork(artwork_path)
        else:
            logger.info("No artwork provided, creating default")
            create_default_artwork(artwork_path)
        
        # Convert MP3 to OGG and save directly to beatmap directory
        ogg_path = os.path.join(beatmap_dir, 'song.ogg')
        try:
            logger.info(f"Converting MP3 to OGG: {mp3_path} -> {ogg_path}")
            mp3_to_ogg(mp3_path, ogg_path)
            logger.info(f"Converted to OGG: {os.path.getsize(ogg_path)} bytes")
        except Exception as e:
            logger.error(f"Failed to convert MP3 to OGG: {e}", exc_info=True)
            return jsonify({"status": "error", "error": f"Failed to convert MP3 to OGG: {str(e)}"}), 500
        
        # Generate preview OGG
        preview_path = os.path.join(beatmap_dir, 'preview.ogg')
        try:
            logger.info(f"Generating preview OGG: {preview_path}")
            generate_preview(ogg_path, preview_path)
            logger.info(f"Preview generated: {os.path.getsize(preview_path)} bytes")
        except Exception as e:
            logger.error(f"Failed to generate preview: {e}", exc_info=True)
            return jsonify({"status": "error", "error": f"Failed to generate preview: {str(e)}"}), 500
        
        # Generate notes.csv
        notes_path = os.path.join(beatmap_dir, 'notes.csv')
        try:
            logger.info(f"Generating notes.csv: {notes_path}")
            generate_notes_csv(mp3_path, None, notes_path)
            logger.info(f"Notes CSV generated: {os.path.getsize(notes_path)} bytes")
        except Exception as e:
            logger.error(f"Failed to generate notes.csv: {e}", exc_info=True)
            return jsonify({"status": "error", "error": f"Failed to generate notes.csv: {str(e)}"}), 500
          # Generate info.csv with metadata
        info_path = os.path.join(beatmap_dir, 'info.csv')
        song_metadata = {
            "title": title or os.path.splitext(file.filename)[0],            "artist": artist or "Unknown Artist",
            "difficulty": "EASY",  # Default difficulty
            "song_map": "VULCAN"   # Default song map
        }
        
        try:
            logger.info(f"Generating info.csv: {info_path}")
            generate_info_csv(song_metadata, info_path, ogg_path, notes_path, auto_detect_difficulty=True)  # Pass audio path and notes path for difficulty detection
            logger.info(f"Info CSV generated: {os.path.getsize(info_path)} bytes")
        except Exception as e:
            logger.error(f"Failed to generate info.csv: {e}", exc_info=True)
            return jsonify({"status": "error", "error": f"Failed to generate info.csv: {str(e)}"}), 500
        
        # Read back the generated info.csv to get the actual detected difficulty and song_map
        try:
            with open(info_path, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    song_metadata["difficulty"] = str(row['Difficulty'])  # Convert to string for beatmaps.json
                    song_metadata["song_map"] = str(row['Song Map'])      # Convert to string for beatmaps.json
                    break  # Only need the first (and only) row
        except Exception as e:
            logger.warning(f"Could not read back generated info.csv: {e}")
            # Keep the original metadata if reading fails
          # Add to beatmaps.json
        beatmaps_path = os.path.join(OUTPUT_DIR, 'beatmaps.json')
        beatmap = {
            "id": beatmap_id,
            "title": song_metadata["title"],
            "artist": song_metadata["artist"],
            "difficulty": song_metadata["difficulty"],
            "song_map": song_metadata["song_map"],
            "createdAt": datetime.now().isoformat()
        }
        
        # Add to beatmaps.json
        try:
            logger.info(f"Updating beatmaps.json: {beatmaps_path}")
            beatmaps = []
            if os.path.exists(beatmaps_path):
                try:
                    with open(beatmaps_path, 'r') as f:
                        beatmaps = json.load(f)
                except json.JSONDecodeError:
                    logger.warning("Could not parse beatmaps.json, starting with empty list")
            
            beatmaps.append(beatmap)
            
            with open(beatmaps_path, 'w') as f:
                json.dump(beatmaps, f)
                
            logger.info(f"Successfully updated beatmaps.json")
        except Exception as e:
            logger.error(f"Failed to update beatmaps.json: {e}", exc_info=True)
            # Continue anyway since the beatmap files are created
              # Clean up temp directory
        try:
            logger.info(f"Cleaning up temp directory: {temp_dir}")
            shutil.rmtree(temp_dir)
            logger.info(f"Temp directory removed")
        except Exception as e:
            logger.warning(f"Failed to clean up temp directory: {e}")
        
        logger.info(f"Successfully created beatmap: {beatmap_id}")
        return jsonify({
            "status": "success",
            "id": beatmap_id,
            "title": song_metadata["title"],
            "artist": song_metadata["artist"],
            "difficulty": song_metadata["difficulty"],
            "song_map": song_metadata["song_map"]
        })
                
    except Exception as e:
        logger.error(f"Unexpected error in upload_file: {e}", exc_info=True)
        error_traceback = traceback.format_exc()
        logger.error(f"Traceback: {error_traceback}")
        
        # Clean up in case of error
        try:
            if temp_dir and os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
                logger.info(f"Cleaned up temp directory after error: {temp_dir}")
            
            if beatmap_dir and os.path.exists(beatmap_dir):
                shutil.rmtree(beatmap_dir)
                logger.info(f"Cleaned up beatmap directory after error: {beatmap_dir}")
        except Exception as cleanup_error:
            logger.error(f"Error during cleanup: {cleanup_error}")
            
        return jsonify({
            "status": "error", 
            "error": str(e),
            "traceback": error_traceback
        }), 500


# Helper function for default artwork
def create_default_artwork(artwork_path):
    try:
        from PIL import Image
        logger.info("Creating default artwork")
        img = Image.new('RGB', (500, 500), color=(73, 109, 137))
        img.save(artwork_path)
        logger.info(f"Default artwork created: {artwork_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to create default artwork: {e}", exc_info=True)
        return False

@app.route('/api/download_beatmap/<beatmap_id>', methods=['GET'])
def download_beatmap(beatmap_id):
    """Download a beatmap with the required files"""
    temp_dir = None
    zip_path = None
    try:
        app.logger.info(f"Download requested for beatmap: {beatmap_id}")
        
        # Path to beatmap directory
        beatmap_dir = os.path.join(OUTPUT_DIR, beatmap_id)
        
        # Check if beatmap directory exists
        if not os.path.exists(beatmap_dir):
            app.logger.error(f"Beatmap directory not found: {beatmap_dir}")
            return jsonify({"error": "Beatmap not found"}), 404
        
        # Create temporary directory for the zip contents
        temp_dir = tempfile.mkdtemp(prefix=f"beatmap_dl_{beatmap_id}_")
        app.logger.info(f"Created temporary directory: {temp_dir}")
        
        # Define the required files
        required_files = [
            "song.ogg",
            "preview.ogg",
            "info.csv",
            "notes.csv",
            "album.jpg"
        ]
        
        # Copy existing files to temp directory
        for filename in required_files:
            src_path = os.path.join(beatmap_dir, filename)
            dest_path = os.path.join(temp_dir, filename)
            
            if os.path.exists(src_path):
                try:
                    shutil.copy2(src_path, dest_path)
                    app.logger.info(f"Copied {filename} to temp directory")
                except Exception as e:
                    app.logger.error(f"Error copying {filename}: {str(e)}")
            else:
                app.logger.warning(f"File not found, will create placeholder: {filename}")
                
                # Create placeholder files for missing files
                if filename == "notes.csv":
                    with open(dest_path, 'w', newline='') as f:
                        writer = csv.writer(f)
                        writer.writerow(["Time", "Lane", "Type", "Length", "Volume", "Pitch", "Effect"])                        # Generate a simple pattern for 60 seconds
                        for i in range(60):
                            # Basic pattern: kick, snare, hihat
                            if i % 2 == 0:
                                writer.writerow([f"{i}.000", "1", "Hit", "0", "100", "Kick", "None"])
                                writer.writerow([f"{i}.000", "3", "Hit", "0", "85", "HiHat", "None"])
                            else:
                                writer.writerow([f"{i}.000", "2", "Hit", "0", "100", "Snare", "None"])
                                writer.writerow([f"{i}.000", "3", "Hit", "0", "85", "HiHat", "None"])
                            writer.writerow([f"{i}.500", "3", "Hit", "0", "85", "HiHat", "None"])
                
                elif filename == "info.csv":
                    # Try to get metadata from beatmaps.json
                    metadata_path = os.path.join(OUTPUT_DIR, 'beatmaps.json')
                    title = "Unknown"
                    artist = "Unknown"
                    difficulty = 0  # EASY
                    duration = 0
                    song_map = 0  # VULCAN
                    
                    if os.path.exists(metadata_path):
                        try:
                            with open(metadata_path, 'r') as f:
                                beatmaps = json.load(f)
                                for bm in beatmaps:
                                    if bm.get("id") == beatmap_id:
                                        title = bm.get("title", "Unknown")
                                        artist = bm.get("artist", "Unknown")
                                        difficulty = bm.get("difficulty", 0)
                                        song_map = bm.get("song_map", 0)
                                        break
                        except Exception as e:
                            app.logger.error(f"Error reading metadata: {str(e)}")
                    
                    # Try to get duration from audio file if available
                    song_ogg_path = os.path.join(beatmap_dir, "song.ogg")
                    if os.path.exists(song_ogg_path):
                        try:
                            import librosa
                            duration = round(librosa.get_duration(path=song_ogg_path), 2)
                        except Exception as e:
                            app.logger.error(f"Error getting audio duration: {str(e)}")
                            duration = 0
                    
                    with open(dest_path, 'w', newline='') as f:
                        writer = csv.writer(f)
                        writer.writerow(["Song Name", "Author Name", "Difficulty", "Song Duration", "Song Map"])
                        writer.writerow([title, artist, difficulty, duration, song_map])
                
                elif filename == "album.jpg":
                    try:
                        from PIL import Image
                        img = Image.new('RGB', (500, 500), color=(73, 109, 137))
                        img.save(dest_path)
                        app.logger.info(f"Created placeholder album art")
                    except Exception as e:
                        app.logger.error(f"Error creating placeholder album art: {str(e)}")
                
                elif filename == "preview.ogg" and os.path.exists(os.path.join(beatmap_dir, "song.ogg")):
                    try:
                        from processing.preview_generator import generate_preview
                        generate_preview(
                            os.path.join(beatmap_dir, "song.ogg"),
                            dest_path
                        )
                        app.logger.info(f"Generated missing preview.ogg")
                    except Exception as e:
                        app.logger.error(f"Error generating preview.ogg: {str(e)}")
        
        # Create the zip file
        file_name = f"beatmap_{beatmap_id}_{int(time.time())}.zip"
        zip_path = os.path.join(OUTPUT_DIR, file_name)
        
        # Make sure we can write to the output directory
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        
        # Make the archive
        try:
            app.logger.info(f"Creating zip archive from {temp_dir} to {zip_path}")
            shutil.make_archive(
                os.path.splitext(zip_path)[0],  # Base name without extension
                'zip',                          # Format
                temp_dir                        # Root directory to compress
            )
            app.logger.info(f"Created zip archive at {zip_path}")
        except Exception as e:
            app.logger.error(f"Error creating zip archive: {str(e)}", exc_info=True)
            return jsonify({"error": f"Failed to create zip file: {str(e)}"}), 500
        
        # Verify zip file exists
        if not os.path.exists(zip_path):
            app.logger.error(f"Expected zip file not found: {zip_path}")
            return jsonify({"error": "Failed to create zip file"}), 500
            
        # Get beatmap title for better download name
        title = "beatmap"
        metadata_path = os.path.join(OUTPUT_DIR, 'beatmaps.json')
        if os.path.exists(metadata_path):
            try:
                with open(metadata_path, 'r') as f:
                    beatmaps = json.load(f)
                    for bm in beatmaps:
                        if bm.get("id") == beatmap_id:
                            title = bm.get("title", "beatmap")
                            break
            except Exception as e:
                app.logger.error(f"Error getting beatmap title: {str(e)}")
        
        # Sanitize filename
        safe_title = "".join(c for c in title if c.isalnum() or c == ' ')
        safe_title = safe_title.replace(" ", "_")
        
        # Return the file
        try:
            app.logger.info(f"Sending zip file: {zip_path}")
            response = send_file(
                zip_path,
                mimetype='application/zip',
                as_attachment=True,
                download_name=f"{safe_title}.zip"
            )
            
            # Clean up the zip file after request completed
            @response.call_on_close
            def cleanup_zip():
                try:
                    os.remove(zip_path)
                    app.logger.info(f"Cleaned up zip file: {zip_path}")
                except Exception as e:
                    app.logger.error(f"Error cleaning up zip file: {str(e)}")
            
            return response
        except Exception as e:
            app.logger.error(f"Error sending zip file: {str(e)}", exc_info=True)
            return jsonify({"error": f"Error sending file: {str(e)}"}), 500
    
    except Exception as e:
        app.logger.error(f"Error in download_beatmap: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500
    
    finally:
        # Clean up temporary directory
        if temp_dir and os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir)
                app.logger.info(f"Cleaned up temp directory: {temp_dir}")
            except Exception as e:
                app.logger.error(f"Error cleaning up temp directory: {str(e)}")

@app.route('/api/clear_all_beatmaps', methods=['DELETE'])
def clear_all_beatmaps():
    """Delete all beatmaps and reset the application state"""
    try:
        app.logger.info(f"Clearing all beatmaps from directory: {OUTPUT_DIR}")
        
        # List all items before deletion for debugging
        if os.path.exists(OUTPUT_DIR):
            items_before = os.listdir(OUTPUT_DIR)
            app.logger.info(f"Items in output directory before clearing: {items_before}")
            deleted_count = 0
            errors = []
            
            # Delete all items except beatmaps.json
            for item in items_before:
                item_path = os.path.join(OUTPUT_DIR, item)
                
                # Skip beatmaps.json file - we'll reset this separately
                if item == 'beatmaps.json':
                    app.logger.info(f"Skipping beatmaps.json file")
                    continue
                
                # Log item analysis for debugging
                app.logger.info(f"Analyzing item: {item}")
                app.logger.info(f"  Is directory: {os.path.isdir(item_path)}")
                app.logger.info(f"  Is file: {os.path.isfile(item_path)}")
                
                try:
                    # Delete any file or directory that is NOT beatmaps.json
                    if os.path.isdir(item_path):
                        app.logger.info(f"Removing directory: {item_path}")
                        # Try to remove with retry logic for Windows file locking issues
                        max_retries = 3
                        for attempt in range(max_retries):
                            try:
                                shutil.rmtree(item_path)
                                app.logger.info(f"Successfully removed directory: {item_path}")
                                deleted_count += 1
                                break
                            except PermissionError as pe:
                                if attempt < max_retries - 1:
                                    app.logger.warning(f"Permission error on attempt {attempt + 1}, retrying: {pe}")
                                    time.sleep(0.5)  # Wait 500ms before retry
                                else:
                                    raise pe
                            except Exception as e:
                                if attempt < max_retries - 1:
                                    app.logger.warning(f"Error on attempt {attempt + 1}, retrying: {e}")
                                    time.sleep(0.5)
                                else:
                                    raise e
                    elif os.path.isfile(item_path):
                        app.logger.info(f"Removing file: {item_path}")
                        # Try to remove with retry logic
                        max_retries = 3
                        for attempt in range(max_retries):
                            try:
                                os.unlink(item_path)
                                app.logger.info(f"Successfully removed file: {item_path}")
                                deleted_count += 1
                                break
                            except PermissionError as pe:
                                if attempt < max_retries - 1:
                                    app.logger.warning(f"Permission error on attempt {attempt + 1}, retrying: {pe}")
                                    time.sleep(0.5)
                                else:
                                    raise pe
                            except Exception as e:
                                if attempt < max_retries - 1:
                                    app.logger.warning(f"Error on attempt {attempt + 1}, retrying: {e}")
                                    time.sleep(0.5)
                                else:
                                    raise e
                    else:
                        app.logger.warning(f"Unknown item type, skipping: {item_path}")
                except Exception as e:
                    error_msg = f"Error deleting {item_path}: {str(e)}"
                    app.logger.error(error_msg, exc_info=True)
                    errors.append(error_msg)
            
            # Reset the beatmaps.json file to an empty array
            beatmaps_json_path = os.path.join(OUTPUT_DIR, 'beatmaps.json')
            try:
                with open(beatmaps_json_path, 'w') as f:
                    json.dump([], f)
                app.logger.info("Reset beatmaps.json to empty array")
            except Exception as e:
                error_msg = f"Error resetting beatmaps.json: {str(e)}"
                app.logger.error(error_msg, exc_info=True)
                errors.append(error_msg)
            
            # Verify everything was removed correctly
            remaining_items = os.listdir(OUTPUT_DIR)
            app.logger.info(f"Items remaining in output directory: {remaining_items}")
            
            if len(remaining_items) > 1 or (len(remaining_items) == 1 and remaining_items[0] != 'beatmaps.json'):
                unexpected_items = [i for i in remaining_items if i != 'beatmaps.json']
                warning = f"Unexpected items still remain in output directory: {unexpected_items}"
                app.logger.warning(warning)
            
            return jsonify({
                "status": "success",
                "message": f"Cleared all beatmaps ({deleted_count} items deleted)",
                "itemsDeleted": deleted_count,
                "errors": errors if errors else None
            })
        else:
            app.logger.warning(f"Output directory not found: {OUTPUT_DIR}")
            os.makedirs(OUTPUT_DIR, exist_ok=True)
            app.logger.info(f"Created output directory: {OUTPUT_DIR}")
            
            # Create empty beatmaps.json
            try:
                with open(os.path.join(OUTPUT_DIR, 'beatmaps.json'), 'w') as f:
                    json.dump([], f)
                app.logger.info("Created empty beatmaps.json")
            except Exception as e:
                app.logger.error(f"Error creating empty beatmaps.json: {e}")
            
            return jsonify({
                "status": "success",
                "message": "Output directory was empty or missing, created fresh directory",
                "itemsDeleted": 0            })
    except Exception as e:
        app.logger.error(f"Error in clear_all_beatmaps: {str(e)}", exc_info=True)
        return jsonify({
            "status": "error",
            "message": f"Failed to clear beatmaps: {str(e)}"
        }), 500

@app.route('/api/update_beatmap/<beatmap_id>', methods=['PUT'])
def update_beatmap(beatmap_id):
    """Update beatmap metadata"""
    try:
        logger.info(f"Update requested for beatmap: {beatmap_id}")
        logger.info(f"Request data: {request.json}")
        
        # Get updated metadata from request
        data = request.json
        
        if not data:
            logger.error("No data provided in request")
            return jsonify({"status": "error", "error": "No data provided"}), 400
              # Required fields
        title = data.get('title')
        artist = data.get('artist')
        difficulty = data.get('difficulty', 'EASY')  # Default to EASY if not provided
        song_map = data.get('song_map', 'VULCAN')    # Default to VULCAN if not provided
        
        if not all([title, artist]):
            logger.error("Missing required metadata fields")
            return jsonify({"status": "error", "error": "Title and artist are required"}), 400
        
        # Path to beatmap directory
        beatmap_dir = os.path.join(OUTPUT_DIR, beatmap_id)
        
        # Check if beatmap exists
        if not os.path.exists(beatmap_dir):
            logger.error(f"Beatmap directory not found: {beatmap_dir}")
            return jsonify({"status": "error", "error": "Beatmap not found"}), 404
              # Update info.csv
        info_path = os.path.join(beatmap_dir, 'info.csv')
        try:
            logger.info(f"Updating info.csv: {info_path}")
            
            # Create updated metadata dictionary
            song_metadata = {
                "title": title,
                "artist": artist,
                "difficulty": difficulty,
                "song_map": song_map
            }
              # Get audio file path for duration calculation
            ogg_path = os.path.join(beatmap_dir, 'song.ogg')
            notes_csv_path = os.path.join(beatmap_dir, 'notes.csv')
            
            # Generate/update info.csv file (don't auto-detect since user is manually setting)
            generate_info_csv(song_metadata, info_path, ogg_path, notes_csv_path, auto_detect_difficulty=False)
            logger.info(f"Updated info.csv")
        except Exception as e:
            logger.error(f"Failed to update info.csv: {e}", exc_info=True)
            return jsonify({"status": "error", "error": f"Failed to update info.csv: {str(e)}"}), 500
            
        # Update beatmaps.json
        beatmaps_path = os.path.join(OUTPUT_DIR, 'beatmaps.json')
        try:
            logger.info(f"Updating beatmap in beatmaps.json")
            
            # Read current beatmaps data
            beatmaps = []
            if os.path.exists(beatmaps_path):
                try:
                    with open(beatmaps_path, 'r') as f:
                        beatmaps = json.load(f)
                except json.JSONDecodeError:
                    logger.warning("Could not parse beatmaps.json, starting with empty list")
              # Find and update the specified beatmap
            updated = False
            for i, beatmap in enumerate(beatmaps):
                if beatmap.get('id') == beatmap_id:
                    # Update fields
                    beatmaps[i]['title'] = title
                    beatmaps[i]['artist'] = artist
                    beatmaps[i]['difficulty'] = difficulty
                    beatmaps[i]['song_map'] = song_map
                    beatmaps[i]['updatedAt'] = datetime.now().isoformat()
                    updated = True
                    break
            
            if not updated:
                logger.warning(f"Beatmap {beatmap_id} not found in beatmaps.json")
                # Add it as a new entry
                beatmaps.append({
                    "id": beatmap_id,
                    "title": title,
                    "artist": artist,
                    "difficulty": difficulty,
                    "song_map": song_map,
                    "createdAt": datetime.now().isoformat(),
                    "updatedAt": datetime.now().isoformat()
                })
            
            # Save updated beatmaps data
            with open(beatmaps_path, 'w') as f:
                json.dump(beatmaps, f)
                
            logger.info(f"Successfully updated beatmap in beatmaps.json")
              # Return the updated beatmap data
            return jsonify({
                "status": "success",
                "id": beatmap_id,
                "title": title,
                "artist": artist,
                "difficulty": difficulty,
                "song_map": song_map
            })
            
        except Exception as e:
            logger.error(f"Failed to update beatmaps.json: {e}", exc_info=True)
            return jsonify({"status": "error", "error": f"Failed to update metadata: {str(e)}"}), 500
        
    except Exception as e:
        logger.error(f"Error in update_beatmap: {e}", exc_info=True)
        return jsonify({"status": "error", "error": f"Server error: {str(e)}"}), 500

# Call at startup
if __name__ == '__main__':
    logger.info("BeatMapper server starting up...")
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    cleanup_output_dir(days=7)
    logger.info(f"Output directory: {OUTPUT_DIR}")
    logger.info("Server initialization complete, starting Flask...")
    app.run(debug=False)
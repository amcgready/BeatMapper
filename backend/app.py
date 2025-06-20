import os
import json
import time
import uuid
import shutil
import logging
import sys
import traceback
import tempfile
from datetime import datetime
import csv
from flask import Flask, request, jsonify, send_file
from processing.audio_converter import audio_to_ogg
from processing.preview_generator import generate_preview
from processing.notes_generator import generate_notes_csv
from processing.info_generator import generate_info_csv, DIFFICULTY_MAP, SONG_MAP_MAP, INFO_HEADER
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
        logging.StreamHandler(sys.stdout)    ]
)

# Progress tracking for note generation
progress_tracker = {}

def update_progress(task_id, progress, message, status='in_progress'):
    """Update progress for a task"""
    progress_tracker[task_id] = {
        'progress': progress,
        'message': message,
        'status': status,
        'timestamp': time.time()
    }
    logger = logging.getLogger(__name__)
    logger.info(f"Progress {task_id}: {progress}% - {message}")

def cleanup_old_progress():
    """Clean up old progress entries (older than 1 hour)"""
    current_time = time.time()
    to_remove = []
    for task_id, info in progress_tracker.items():
        if current_time - info.get('timestamp', 0) > 3600:  # 1 hour
            to_remove.append(task_id)
    for task_id in to_remove:
        del progress_tracker[task_id]

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

@app.route('/api/progress/<task_id>', methods=['GET'])
def get_progress(task_id):
    """Get progress status for a long-running task"""
    progress_info = progress_tracker.get(task_id, {
        'status': 'not_found',
        'progress': 0,
        'message': 'Task not found'
    })
    return jsonify(progress_info)

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
        os.makedirs(temp_dir, exist_ok=True)          # Save the audio file to temp directory with original format
        audio_path = os.path.join(temp_dir, f'song{file_extension}')
        logger.info(f"Saving audio file to: {audio_path}")
        file.save(audio_path)
        logger.info(f"Audio file saved successfully: {os.path.getsize(audio_path)} bytes")

        # Handle optional MIDI file
        midi_path = None
        if 'midi_file' in request.files:
            midi_file = request.files['midi_file']
            if midi_file.filename and midi_file.filename != '':
                logger.info(f"Received MIDI file: {midi_file.filename}")
                
                # Check MIDI file extension
                if midi_file.filename.lower().endswith(('.mid', '.midi')):
                    midi_path = os.path.join(temp_dir, f'song.mid')
                    logger.info(f"Saving MIDI file to: {midi_path}")
                    midi_file.save(midi_path)
                    logger.info(f"MIDI file saved successfully: {os.path.getsize(midi_path)} bytes")
                else:
                    logger.warning(f"Invalid MIDI file format: {midi_file.filename}")
            else:
                logger.info("Empty MIDI file received, skipping")
        else:
            logger.info("No MIDI file provided")        # Extract metadata from the form
        title = request.form.get('title', '')
        artist = request.form.get('artist', '')
        difficulty = request.form.get('difficulty', '')  # User's difficulty override
        song_map = request.form.get('song_map', 'VULCAN')  # User's stage selection
          # Parse and clean up title/artist metadata in case they're combined
        # Simple implementation since parse_artist_title_metadata is missing
        parsed_title = title.strip() if title else ""
        parsed_artist = artist.strip() if artist else ""
        
        logger.info(f"Original metadata: title='{title}', artist='{artist}', difficulty='{difficulty}', song_map='{song_map}'")
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
          # Convert audio to OGG and save directly to beatmap directory
        ogg_path = os.path.join(beatmap_dir, 'song.ogg')
        try:
            logger.info(f"Converting audio to OGG: {audio_path} -> {ogg_path}")
            audio_to_ogg(audio_path, ogg_path)
            logger.info(f"Converted to OGG: {os.path.getsize(ogg_path)} bytes")
        except Exception as e:
            logger.error(f"Failed to convert audio to OGG: {e}", exc_info=True)
            return jsonify({"status": "error", "error": f"Failed to convert audio to OGG: {str(e)}"}), 500
        
        # Generate preview OGG
        preview_path = os.path.join(beatmap_dir, 'preview.ogg')
        try:
            logger.info(f"Generating preview OGG: {preview_path}")
            generate_preview(ogg_path, preview_path)
            logger.info(f"Preview generated: {os.path.getsize(preview_path)} bytes")
        except Exception as e:
            logger.error(f"Failed to generate preview: {e}", exc_info=True)
            return jsonify({"status": "error", "error": f"Failed to generate preview: {str(e)}"}), 500          # Generate notes.csv using original audio file
        notes_path = os.path.join(beatmap_dir, 'notes.csv')        # Determine target difficulty for note generation
        target_difficulty = difficulty if (difficulty and difficulty != "AUTO") else "EASY"  # Default to EASY if no difficulty specified
        
        # Convert numeric difficulty to string if needed for notes generator
        if target_difficulty is not None:
            difficulty_string_map = {0: "EASY", 1: "MEDIUM", 2: "HARD", 3: "EXTREME"}
            if isinstance(target_difficulty, int):
                target_difficulty = difficulty_string_map.get(target_difficulty, "EASY")
            elif isinstance(target_difficulty, str) and target_difficulty.isdigit():
                target_difficulty = difficulty_string_map.get(int(target_difficulty), "EASY")
        
        try:
            logger.info(f"Generating notes.csv: {notes_path}")
            if midi_path:
                logger.info(f"Using MIDI file for enhanced beat detection: {midi_path}")
            if target_difficulty:
                logger.info(f"Using difficulty override for note generation: {target_difficulty}")
            
            generate_notes_csv(audio_path, midi_path, notes_path, target_difficulty=target_difficulty)
            logger.info(f"Notes CSV generated: {os.path.getsize(notes_path)} bytes")
        except Exception as e:
            logger.error(f"Failed to generate notes.csv: {e}", exc_info=True)
            return jsonify({"status": "error", "error": f"Failed to generate notes.csv: {str(e)}"}), 500          # Generate info.csv with metadata
        info_path = os.path.join(beatmap_dir, 'info.csv')
        
        # Determine if user provided an explicit difficulty override
        user_difficulty_override = difficulty and difficulty != "AUTO"
        
        song_metadata = {
            "title": title or os.path.splitext(file.filename)[0],            
            "artist": artist or "Unknown Artist",
            "difficulty": difficulty if user_difficulty_override else "EASY",  # Use override or default
            "song_map": song_map   # Use user's stage selection
        }
        
        try:
            logger.info(f"Generating info.csv: {info_path}")
            # Only auto-detect difficulty if user didn't provide an override
            auto_detect = not user_difficulty_override
            logger.info(f"User difficulty override: {user_difficulty_override}, auto-detect: {auto_detect}")
            
            generate_info_csv(song_metadata, info_path, ogg_path, notes_path, auto_detect_difficulty=auto_detect)# Pass audio path and notes path for difficulty detection
            logger.info(f"Info CSV generated: {os.path.getsize(info_path)} bytes")
        except Exception as e:
            logger.error(f"Failed to generate info.csv: {e}", exc_info=True)
            return jsonify({"status": "error", "error": f"Failed to generate info.csv: {str(e)}"}), 500
          # Read back the generated info.csv to get the actual detected difficulty and song_map
        try:
            # Debug logging
            debug_file = "c:/temp/beatmapper_debug.txt"
            try:
                with open(debug_file, "a") as f:
                    f.write(f"\n=== UPLOAD READBACK DEBUG {beatmap_id} ===\n")
                    f.write(f"About to read info.csv from: {info_path}\n")
            except:
                pass
                
            with open(info_path, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    old_difficulty = song_metadata["difficulty"]
                    # Store numeric values for consistency
                    song_metadata["difficulty"] = int(row['Difficulty'])  # Keep as numeric
                    song_metadata["song_map"] = int(row['Song Map'])       # Keep as numeric
                    
                    # Debug logging
                    try:
                        with open(debug_file, "a") as f:
                            f.write(f"Read from info.csv - Difficulty: {row['Difficulty']}\n")
                            f.write(f"song_metadata difficulty changed: {old_difficulty} -> {song_metadata['difficulty']}\n")
                    except:
                        pass
                    break  # Only need the first (and only) row
        except Exception as e:
            logger.warning(f"Could not read back generated info.csv: {e}")
            # Keep the original metadata if reading fails        # Add to beatmaps.json
        beatmaps_path = os.path.join(OUTPUT_DIR, 'beatmaps.json')
        
        beatmap = {
            "id": beatmap_id,
            "title": song_metadata["title"],
            "artist": song_metadata["artist"],
            # song_metadata now contains numeric values after readback from info.csv
            "difficulty": song_metadata["difficulty"] if isinstance(song_metadata["difficulty"], int) else DIFFICULTY_MAP.get(song_metadata["difficulty"].upper(), 0),
            "song_map": song_metadata["song_map"] if isinstance(song_metadata["song_map"], int) else SONG_MAP_MAP.get(song_metadata["song_map"].upper(), 0),
            "createdAt": datetime.now().isoformat()
        }
        
        # Debug logging for beatmap object
        try:
            with open(debug_file, "a") as f:
                f.write(f"Created beatmap object: {beatmap}\n")
        except:
            pass

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
              # Clean up temp directory        try:
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
            # song_metadata now contains numeric values after readback from info.csv
            "difficulty": song_metadata["difficulty"] if isinstance(song_metadata["difficulty"], int) else DIFFICULTY_MAP.get(song_metadata["difficulty"].upper(), 0),
            "song_map": song_metadata["song_map"] if isinstance(song_metadata["song_map"], int) else SONG_MAP_MAP.get(song_metadata["song_map"].upper(), 0)
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
          # Debug: Write to file since logging might not be visible
        debug_file = "c:/temp/beatmapper_debug.txt"
        try:
            os.makedirs(os.path.dirname(debug_file), exist_ok=True)
            with open(debug_file, "a") as f:
                f.write(f"\n=== UPDATE ENDPOINT DEBUG {beatmap_id} ===\n")
                f.write(f"Raw request data: {request.json}\n")
                f.write(f"data.get('difficulty'): {data.get('difficulty')}\n")
                f.write(f"data.get('difficulty') is not None: {data.get('difficulty') is not None}\n")
        except:
            pass
        
        # Get updated metadata from request
        data = request.json
        
        if not data:
            logger.error("No data provided in request")
            return jsonify({"status": "error", "error": "No data provided"}), 400        # Required fields
        title = data.get('title')
        artist = data.get('artist')
        difficulty = data.get('difficulty')  # Don't default here
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
            
        # If difficulty is not provided, read the current difficulty from info.csv to preserve it
        if difficulty is None:
            try:
                with open(debug_file, "a") as f:
                    f.write(f"No difficulty provided, preserving existing\n")
            except:
                pass
                
            info_path = os.path.join(beatmap_dir, 'info.csv')
            if os.path.exists(info_path):
                try:
                    with open(info_path, 'r') as f:
                        reader = csv.DictReader(f)
                        for row in reader:
                            current_difficulty = int(row['Difficulty'])
                            # Convert numeric back to string for consistency
                            difficulty_names = ['EASY', 'MEDIUM', 'HARD', 'EXTREME']
                            difficulty = difficulty_names[current_difficulty] if 0 <= current_difficulty < 4 else 'EASY'
                            break
                    
                    # Debug logging
                    try:
                        with open(debug_file, "a") as f:
                            f.write(f"Preserved difficulty from info.csv: {current_difficulty} -> {difficulty}\n")
                    except:
                        pass
                except Exception as e:
                    logger.warning(f"Could not read current difficulty from info.csv: {e}")
                    difficulty = 'EASY'  # Fallback
            else:
                difficulty = 'EASY'  # Fallback if no info.csv exists
        else:
            # Debug logging  
            try:
                with open(debug_file, "a") as f:
                    f.write(f"Using provided difficulty override: {difficulty}\n")
            except:
                pass
        
        # Update info.csv
        info_path = os.path.join(beatmap_dir, 'info.csv')
        try:
            logger.info(f"Updating info.csv: {info_path}")
            
            # Read current info.csv to preserve existing values
            current_data = {}
            if os.path.exists(info_path):
                with open(info_path, 'r') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        current_data = dict(row)
                        break
            
            # Update only the fields that were provided, preserve others
            current_data['Song Name'] = title
            current_data['Author Name'] = artist
            current_data['Song Map'] = str(SONG_MAP_MAP.get(song_map.upper(), 0) if isinstance(song_map, str) else song_map)
              # Only update difficulty if it was explicitly provided in the request
            if data.get('difficulty') is not None:
                current_data['Difficulty'] = str(DIFFICULTY_MAP.get(difficulty.upper(), 0) if isinstance(difficulty, str) else difficulty)
            # Otherwise, keep the existing difficulty value from current_data (no change needed)
            
            # Write the updated info.csv
            with open(info_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(INFO_HEADER)
                writer.writerow([
                    current_data.get('Song Name', ''),
                    current_data.get('Author Name', ''),
                    current_data.get('Difficulty', '0'),
                    current_data.get('Song Duration', '0'),
                    current_data.get('Song Map', '0')
                ])
                
            logger.info(f"Updated info.csv - preserved difficulty: {current_data.get('Difficulty', '0')}")
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
                    logger.warning("Could not parse beatmaps.json, starting with empty list")              # Find and update the specified beatmap
            updated = False
            for i, beatmap in enumerate(beatmaps):
                if beatmap.get('id') == beatmap_id:
                    # Update fields
                    beatmaps[i]['title'] = title
                    beatmaps[i]['artist'] = artist
                    # Convert difficulty string to numeric for frontend compatibility
                    beatmaps[i]['difficulty'] = DIFFICULTY_MAP.get(difficulty.upper(), 0) if isinstance(difficulty, str) else difficulty
                    # Convert song_map string to numeric for frontend compatibility
                    beatmaps[i]['song_map'] = SONG_MAP_MAP.get(song_map.upper(), 0) if isinstance(song_map, str) else song_map
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
                    # Convert difficulty string to numeric for frontend compatibility
                    "difficulty": DIFFICULTY_MAP.get(difficulty.upper(), 0) if isinstance(difficulty, str) else difficulty,
                    # Convert song_map string to numeric for frontend compatibility
                    "song_map": SONG_MAP_MAP.get(song_map.upper(), 0) if isinstance(song_map, str) else song_map,
                    "createdAt": datetime.now().isoformat(),
                    "updatedAt": datetime.now().isoformat()
                })
              # Save updated beatmaps data
            with open(beatmaps_path, 'w') as f:
                json.dump(beatmaps, f)
                
            logger.info(f"Successfully updated beatmap in beatmaps.json")            # Check if we need to regenerate notes.csv (if difficulty changed)
            should_regenerate_notes = False
            regeneration_reason = ""
            
            # Debug logging for difficulty analysis
            try:
                with open(debug_file, "a") as f:
                    f.write(f"\n=== DIFFICULTY CHANGE ANALYSIS ===\n")
                    f.write(f"User provided difficulty: {data.get('difficulty')}\n")
                    f.write(f"Final difficulty string: {difficulty}\n")
            except:
                pass
            
            # Case 1: User explicitly provided a difficulty
            if data.get('difficulty') is not None:
                should_regenerate_notes = True
                regeneration_reason = f"User provided explicit difficulty: {difficulty}"
                try:
                    with open(debug_file, "a") as f:
                        f.write(f"CASE 1: User provided difficulty - REGENERATING\n")
                except:
                    pass
            
            # Case 2: Check if the computed difficulty differs from current info.csv
            try:
                current_info_difficulty = None;
                with open(info_path, 'r') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        current_info_difficulty = int(row['Difficulty'])
                        break
                
                computed_difficulty_numeric = DIFFICULTY_MAP.get(difficulty.upper(), 0) if isinstance(difficulty, str) else difficulty
                
                if current_info_difficulty is not None and current_info_difficulty != computed_difficulty_numeric:
                    should_regenerate_notes = True
                    regeneration_reason = f"Difficulty changed from {current_info_difficulty} to {computed_difficulty_numeric}"
                    
                # Debug logging
                try:
                    with open(debug_file, "a") as f:
                        f.write(f"Current info.csv difficulty: {current_info_difficulty}\n")
                        f.write(f"Computed difficulty: {computed_difficulty_numeric}\n")
                        f.write(f"Should regenerate: {should_regenerate_notes}\n")
                        f.write(f"Reason: {regeneration_reason}\n")
                except:
                    pass
                    
            except Exception as e:
                logger.warning(f"Could not read current info.csv for comparison: {e}")
                # If we can't read the current difficulty, regenerate to be safe
                if data.get('difficulty') is not None:
                    should_regenerate_notes = True
                    regeneration_reason = "Could not read current difficulty, regenerating to be safe"            # Regenerate notes.csv if needed
            if should_regenerate_notes:
                try:
                    logger.info(f"Regenerating notes.csv: {regeneration_reason}")
                    
                    # Generate task ID for progress tracking
                    task_id = f"regenerate_{beatmap_id}_{int(time.time())}"
                    update_progress(task_id, 0, "Starting note regeneration...", "in_progress")
                    
                    # Debug logging
                    try:
                        with open(debug_file, "a") as f:
                            f.write(f"REGENERATING notes.csv: {regeneration_reason}\n")
                            f.write(f"Target difficulty: {difficulty}\n")
                            f.write(f"Progress task ID: {task_id}\n")
                    except:
                        pass
                    
                    update_progress(task_id, 10, "Finding audio files...")
                    
                    # Find the audio file in the beatmap directory
                    audio_file = None
                    midi_file = None
                    
                    for filename in os.listdir(beatmap_dir):
                        if filename.lower().endswith(('.mp3', '.wav', '.flac', '.ogg')):
                            audio_file = os.path.join(beatmap_dir, filename)
                        elif filename.lower().endswith(('.mid', '.midi')):
                            midi_file = os.path.join(beatmap_dir, filename)
                    
                    update_progress(task_id, 20, "Audio files located, starting note generation...")
                    
                    if audio_file and os.path.exists(audio_file):
                        notes_path = os.path.join(beatmap_dir, 'notes.csv')
                        
                        # Import the notes generator
                        from processing.notes_generator import generate_notes_csv
                        
                        update_progress(task_id, 30, "Initializing note generator...")
                        
                        # Convert numeric difficulty back to string for notes generator
                        difficulty_string_map = {0: "EASY", 1: "MEDIUM", 2: "HARD", 3: "EXTREME"}
                        target_difficulty_string = difficulty_string_map.get(difficulty, "EASY") if isinstance(difficulty, int) else difficulty
                        
                        # Debug logging
                        try:
                            with open(debug_file, "a") as f:
                                f.write(f"Converting difficulty {difficulty} to {target_difficulty_string}\n")
                        except:
                            pass
                        
                        update_progress(task_id, 40, f"Generating notes for {target_difficulty_string} difficulty...")
                        
                        # Regenerate notes.csv with the new difficulty
                        success = generate_notes_csv(
                            song_path=audio_file,
                            midi_path=midi_file if midi_file and os.path.exists(midi_file) else None,
                            output_path=notes_path,
                            target_difficulty=target_difficulty_string,
                            progress_callback=lambda p, msg: update_progress(task_id, 40 + int(p * 0.5), msg)
                        )
                        
                        if success:
                            update_progress(task_id, 90, "Note generation completed, finalizing...")
                            logger.info(f"Successfully regenerated notes.csv with difficulty: {difficulty}")
                            update_progress(task_id, 100, "Notes regeneration completed successfully!", "completed")
                        else:
                            update_progress(task_id, 0, "Note generation failed", "error")
                            logger.error("Note generation failed")
                            
                    else:
                        update_progress(task_id, 0, "Audio file not found", "error")
                        logger.error(f"Audio file not found in beatmap directory: {beatmap_dir}")
                        
                    # Return task ID so frontend can track progress
                    return jsonify({
                        "status": "success",
                        "title": title,
                        "artist": artist,
                        "difficulty": DIFFICULTY_MAP.get(difficulty.upper(), 0) if isinstance(difficulty, str) else difficulty,
                        "song_map": SONG_MAP_MAP.get(song_map.upper(), 0) if isinstance(song_map, str) else song_map,
                        "regenerating": True,                        "progress_task_id": task_id
                    })
                    
                except Exception as e:
                    logger.error(f"Failed to regenerate notes.csv: {e}", exc_info=True)
                    update_progress(task_id, 0, f"Regeneration failed: {str(e)}", "error")
                    # Don't fail the entire update if notes regeneration fails
                    try:
                        with open(debug_file, "a") as f:
                            f.write(f"Notes regeneration failed: {e}\n")
                    except:
                        pass
              
            # Return the updated beatmap data
            return jsonify({
                "status": "success",
                "id": beatmap_id,
                "title": title,
                "artist": artist,
                # Return numeric difficulty and song_map for frontend compatibility
                "difficulty": DIFFICULTY_MAP.get(difficulty.upper(), 0) if isinstance(difficulty, str) else difficulty,
                "song_map": SONG_MAP_MAP.get(song_map.upper(), 0) if isinstance(song_map, str) else song_map
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
    # cleanup_output_dir(days=7)  # Function not implemented yet
    logger.info(f"Output directory: {OUTPUT_DIR}")
    logger.info("Server initialization complete, starting Flask...")
    app.run(debug=False)
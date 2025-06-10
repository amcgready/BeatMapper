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
from flask import Flask, request, jsonify, send_file, send_from_directory
from werkzeug.utils import secure_filename
from processing.audio_converter import mp3_to_ogg
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
                except Exception as e:
                    logger.error(f"Failed to delete {filename}: {e}")

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
        
        # Check file extension
        if not file.filename.lower().endswith('.mp3'):
            logger.error(f"Invalid file format: {file.filename}")
            return jsonify({"status": "error", "error": "Invalid file format, must be MP3"}), 400
            
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
        
        # First save the MP3 file to temp directory
        mp3_path = os.path.join(temp_dir, 'song.mp3')
        logger.info(f"Saving MP3 to: {mp3_path}")
        file.save(mp3_path)
        logger.info(f"MP3 saved successfully: {os.path.getsize(mp3_path)} bytes")
        
        # Extract metadata from the form
        title = request.form.get('title', '')
        artist = request.form.get('artist', '')
        album = request.form.get('album', '')
        year = request.form.get('year', '')
        logger.info(f"Metadata from request: title='{title}', artist='{artist}', album='{album}', year='{year}'")
        
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
            "title": title or os.path.splitext(file.filename)[0],
            "artist": artist or "Unknown Artist",
            "album": album or "Unknown Album",
            "year": year or str(datetime.now().year)
        }
        
        try:
            logger.info(f"Generating info.csv: {info_path}")
            generate_info_csv(song_metadata, info_path)
            logger.info(f"Info CSV generated: {os.path.getsize(info_path)} bytes")
        except Exception as e:
            logger.error(f"Failed to generate info.csv: {e}", exc_info=True)
            return jsonify({"status": "error", "error": f"Failed to generate info.csv: {str(e)}"}), 500
        
        # Add to beatmaps.json
        beatmaps_path = os.path.join(OUTPUT_DIR, 'beatmaps.json')
        beatmap = {
            "id": beatmap_id,
            "title": song_metadata["title"],
            "artist": song_metadata["artist"],
            "album": song_metadata["album"],
            "year": song_metadata["year"],
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
            "album": song_metadata["album"],
            "year": song_metadata["year"]
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
                        writer.writerow(["Time", "Lane", "Type", "Length", "Volume", "Pitch", "Effect"])
                        # Generate a simple pattern for 60 seconds
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
                    album = "Unknown"
                    year = ""
                    
                    if os.path.exists(metadata_path):
                        try:
                            with open(metadata_path, 'r') as f:
                                beatmaps = json.load(f)
                                for bm in beatmaps:
                                    if bm.get("id") == beatmap_id:
                                        title = bm.get("title", "Unknown")
                                        artist = bm.get("artist", "Unknown")
                                        album = bm.get("album", "Unknown")
                                        year = bm.get("year", "")
                                        break
                        except Exception as e:
                            app.logger.error(f"Error reading metadata: {str(e)}")
                    
                    with open(dest_path, 'w', newline='') as f:
                        writer = csv.writer(f)
                        writer.writerow(["Title", "Artist", "Album", "Year"])
                        writer.writerow([title, artist, album, year])
                
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
        app.logger.info("Clearing all beatmaps")
        
        # Get all items in output directory
        items_deleted = 0
        
        if os.path.exists(OUTPUT_DIR):
            for item in os.listdir(OUTPUT_DIR):
                item_path = os.path.join(OUTPUT_DIR, item)
                
                # Skip beatmaps.json, we'll reset it separately
                if item == 'beatmaps.json':
                    continue
                
                try:
                    if os.path.isfile(item_path):
                        os.unlink(item_path)
                        app.logger.info(f"Deleted file: {item_path}")
                        items_deleted += 1
                    elif os.path.isdir(item_path):
                        shutil.rmtree(item_path)
                        app.logger.info(f"Deleted directory: {item_path}")
                        items_deleted += 1
                except Exception as e:
                    app.logger.error(f"Error deleting {item_path}: {e}")
            
            # Reset the beatmaps.json file
            try:
                with open(os.path.join(OUTPUT_DIR, 'beatmaps.json'), 'w') as f:
                    json.dump([], f)
                app.logger.info("Reset beatmaps.json to empty array")
            except Exception as e:
                app.logger.error(f"Error resetting beatmaps.json: {e}")
                
            app.logger.info(f"Successfully deleted {items_deleted} items from output directory")
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
            "message": f"Cleared all beatmaps ({items_deleted} items deleted)",
            "itemsDeleted": items_deleted
        })
        
    except Exception as e:
        app.logger.error(f"Error in clear_all_beatmaps: {e}", exc_info=True)
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
        album = data.get('album')
        year = data.get('year')
        
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
                "album": album or "Unknown Album",
                "year": year or ""
            }
            
            # Generate/update info.csv file
            generate_info_csv(song_metadata, info_path)
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
                    beatmaps[i]['album'] = album or beatmap.get('album', "Unknown Album")
                    beatmaps[i]['year'] = year or beatmap.get('year', "")
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
                    "album": album or "Unknown Album",
                    "year": year or "",
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
                "album": album or "Unknown Album",
                "year": year or ""
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
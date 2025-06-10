import os
import json
import time
import uuid
import shutil
import tempfile
import csv
import logging
import sqlite3
import warnings
from flask import Flask, request, jsonify, send_file
from werkzeug.utils import secure_filename
from processing.audio_converter import mp3_to_ogg
from processing.preview_generator import generate_preview
from processing.notes_generator import generate_notes_csv
from processing.info_generator import generate_info_csv
from flask_cors import CORS

log_file = os.path.join(os.path.dirname(__file__), 'beatmapper.log')
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(name)s %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler()
    ]
)

app = Flask(__name__)
CORS(app)

app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100 MB upload limit

OUTPUT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../output'))
TEMPLATE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), 'templates/notes_template.xlsx'))

def cleanup_output_dir(days=7):
    now = time.time()
    cutoff = now - days * 86400
    for filename in os.listdir(OUTPUT_DIR):
        file_path = os.path.join(OUTPUT_DIR, filename)
        if os.path.isfile(file_path):
            if os.path.getmtime(file_path) < cutoff:
                try:
                    os.remove(file_path)
                    app.logger.info(f"Deleted old file: {filename}")
                except Exception as e:
                    app.logger.error(f"Failed to delete {filename}: {e}")

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
    try:
        app.logger.info("Upload endpoint called")
        
        # Check if file was included in the request
        if 'file' not in request.files:
            app.logger.error("No file part in request")
            return jsonify({"status": "error", "error": "No file part"}), 400
            
        file = request.files['file']
        if file.filename == '':
            app.logger.error("No selected file")
            return jsonify({"status": "error", "error": "No selected file"}), 400
            
        if file and file.filename.endswith('.mp3'):
            # Generate a unique ID for this beatmap
            beatmap_id = str(uuid.uuid4())
            
            # Create output directory if it doesn't exist
            os.makedirs(OUTPUT_DIR, exist_ok=True)
            
            # Create a directory for this beatmap
            beatmap_dir = os.path.join(OUTPUT_DIR, beatmap_id)
            os.makedirs(beatmap_dir, exist_ok=True)
            
            # Create a temp directory for processing
            temp_dir = os.path.join(OUTPUT_DIR, f"temp_{beatmap_id}")
            os.makedirs(temp_dir, exist_ok=True)
            
            try:
                # First save the MP3 file to temp directory
                mp3_path = os.path.join(temp_dir, 'song.mp3')
                file.save(mp3_path)
                app.logger.info(f"MP3 saved to temp directory: {mp3_path}")
                
                # Extract metadata from the form
                title = request.form.get('title', '')
                artist = request.form.get('artist', '')
                album = request.form.get('album', '')
                year = request.form.get('year', '')
                
                # Process album art if provided
                artwork_path = os.path.join(beatmap_dir, 'album.jpg')
                if 'artwork' in request.files and request.files['artwork'].filename:
                    try:
                        artwork = request.files['artwork']
                        artwork.save(artwork_path)
                        app.logger.info(f"Artwork saved to {artwork_path}")
                    except Exception as e:
                        app.logger.error(f"Failed to save artwork: {e}")
                        # Create a simple placeholder album art
                        try:
                            from PIL import Image
                            img = Image.new('RGB', (500, 500), color=(73, 109, 137))
                            img.save(artwork_path)
                            app.logger.info("Created placeholder album art")
                        except Exception as e:
                            app.logger.error(f"Failed to create placeholder artwork: {e}")
                
                # Convert MP3 to OGG and save directly to beatmap directory
                ogg_path = os.path.join(beatmap_dir, 'song.ogg')
                try:
                    mp3_to_ogg(mp3_path, ogg_path)
                    app.logger.info(f"Converted MP3 to OGG: {ogg_path}")
                except Exception as e:
                    app.logger.error(f"Failed to convert MP3 to OGG: {e}")
                    return jsonify({"status": "error", "error": f"Failed to convert MP3 to OGG: {str(e)}"}), 500
                
                # Generate preview OGG
                preview_path = os.path.join(beatmap_dir, 'preview.ogg')
                try:
                    generate_preview(ogg_path, preview_path)
                    app.logger.info(f"Generated preview OGG: {preview_path}")
                except Exception as e:
                    app.logger.error(f"Failed to generate preview: {e}")
                    return jsonify({"status": "error", "error": f"Failed to generate preview: {str(e)}"}), 500
                
                # Generate notes.csv
                notes_path = os.path.join(beatmap_dir, 'notes.csv')
                try:
                    generate_notes_csv(mp3_path, None, notes_path)
                    app.logger.info(f"Generated notes.csv: {notes_path}")
                except Exception as e:
                    app.logger.error(f"Failed to generate notes.csv: {e}")
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
                    generate_info_csv(song_metadata, info_path)
                    app.logger.info(f"Generated info.csv: {info_path}")
                except Exception as e:
                    app.logger.error(f"Failed to generate info.csv: {e}")
                    return jsonify({"status": "error", "error": f"Failed to generate info.csv: {str(e)}"}), 500
                
                # Verify all required files exist
                required_files = [
                    'song.ogg',
                    'preview.ogg',
                    'info.csv',
                    'notes.csv',
                    'album.jpg'
                ]
                
                missing_files = []
                for req_file in required_files:
                    if not os.path.exists(os.path.join(beatmap_dir, req_file)):
                        missing_files.append(req_file)
                        app.logger.warning(f"Missing required file: {req_file}")
                
                # Create any missing files with placeholders
                if missing_files:
                    app.logger.warning(f"Creating placeholders for missing files: {missing_files}")
                    
                    if 'album.jpg' in missing_files:
                        try:
                            from PIL import Image
                            img = Image.new('RGB', (500, 500), color=(73, 109, 137))
                            img.save(os.path.join(beatmap_dir, 'album.jpg'))
                            app.logger.info("Created placeholder album art")
                        except Exception as e:
                            app.logger.error(f"Failed to create placeholder artwork: {e}")
                
                # Create a beatmap entry for tracking
                beatmap = {
                    "id": beatmap_id,
                    "title": song_metadata["title"],
                    "artist": song_metadata["artist"],
                    "album": song_metadata["album"],
                    "year": song_metadata["year"],
                    "createdAt": datetime.now().isoformat()
                }
                
                # Add to beatmaps.json
                beatmaps_path = os.path.join(OUTPUT_DIR, 'beatmaps.json')
                beatmaps = []
                if os.path.exists(beatmaps_path):
                    try:
                        with open(beatmaps_path, 'r') as f:
                            beatmaps = json.load(f)
                    except json.JSONDecodeError:
                        app.logger.warning("Could not parse beatmaps.json, starting with empty list")
                
                beatmaps.append(beatmap)
                
                with open(beatmaps_path, 'w') as f:
                    json.dump(beatmaps, f)
                
                # Clean up temp directory
                try:
                    shutil.rmtree(temp_dir)
                    app.logger.info(f"Cleaned up temp directory: {temp_dir}")
                except Exception as e:
                    app.logger.warning(f"Failed to clean up temp directory: {e}")
                
                # Verify final output directory has only required files
                final_files = os.listdir(beatmap_dir)
                
                for f in final_files:
                    if f not in required_files:
                        try:
                            file_path = os.path.join(beatmap_dir, f)
                            if os.path.isfile(file_path):
                                os.remove(file_path)
                                app.logger.info(f"Removed unnecessary file: {f}")
                            elif os.path.isdir(file_path):
                                shutil.rmtree(file_path)
                                app.logger.info(f"Removed unnecessary directory: {f}")
                        except Exception as e:
                            app.logger.warning(f"Failed to remove unnecessary file {f}: {e}")
                
                app.logger.info(f"Successfully created beatmap: {beatmap_id}")
                return jsonify({
                    "status": "success",
                    "id": beatmap_id,
                    "title": song_metadata["title"],
                    "artist": song_metadata["artist"],
                    "album": song_metadata["album"],
                    "year": song_metadata["year"]
                })
                
            except Exception as e:
                app.logger.error(f"Error processing beatmap: {e}", exc_info=True)
                
                # Clean up in case of error
                try:
                    if os.path.exists(temp_dir):
                        shutil.rmtree(temp_dir)
                    
                    if os.path.exists(beatmap_dir):
                        shutil.rmtree(beatmap_dir)
                except Exception as cleanup_error:
                    app.logger.error(f"Error during cleanup: {cleanup_error}")
                    
                return jsonify({"status": "error", "error": str(e)}), 500
                
        else:
            app.logger.error("Invalid file format, must be MP3")
            return jsonify({"status": "error", "error": "Invalid file format, must be MP3"}), 400
            
    except Exception as e:
        app.logger.error(f"Upload failed: {e}", exc_info=True)
        return jsonify({"status": "error", "error": str(e)}), 500

@app.route('/api/upload_notes', methods=['POST'])
def upload_notes():
    try:
        if 'file' not in request.files:
            app.logger.warning("No notes.csv uploaded in request.")
            return jsonify({'error': 'No file uploaded'}), 400
        file = request.files['file']
        filename = secure_filename(file.filename)
        if not filename.lower().endswith('.csv'):
            app.logger.warning(f"Rejected notes file with invalid extension: {filename}")
            return jsonify({'error': 'Only CSV files are supported'}), 400
        notes_path = os.path.join(OUTPUT_DIR, 'notes.csv')
        file.save(notes_path)
        app.logger.info("notes.csv updated by user upload.")
        return jsonify({'status': 'notes.csv updated'})
    except Exception as e:
        app.logger.error(f"Unexpected error in upload_notes: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/upload_artwork', methods=['POST'])
def upload_artwork():
    try:
        if 'file' not in request.files:
            app.logger.warning("No artwork uploaded in request.")
            return jsonify({'error': 'No file uploaded'}), 400
            
        file = request.files['file']
        filename = secure_filename(file.filename)
        if not filename.lower().endswith(('.jpg', '.jpeg', '.png')):
            app.logger.warning(f"Rejected artwork file with invalid extension: {filename}")
            return jsonify({'error': 'Only JPG and PNG files are supported'}), 400
            
        album_path = os.path.join(OUTPUT_DIR, 'album.jpg')
        file.save(album_path)
        app.logger.info("Album artwork updated by user upload.")
        
        return jsonify({'status': 'Album artwork updated'})
    except Exception as e:
        app.logger.error(f"Unexpected error in upload_artwork: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/download/<filename>')
def download(filename):
    try:
        safe_filename = secure_filename(filename)
        file_path = os.path.join(OUTPUT_DIR, safe_filename)
        if not os.path.exists(file_path):
            app.logger.warning(f"Requested file does not exist: {safe_filename}")
            return jsonify({'error': 'File not found'}), 404
        return send_from_directory(OUTPUT_DIR, safe_filename, as_attachment=True)
    except Exception as e:
        app.logger.error(f"Unexpected error in download: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/beatmaps', methods=['GET'])
def get_beatmaps():
    """Get all beatmaps in the output directory"""
    try:
        beatmaps = []
        # Check for a metadata file that stores beatmap info
        metadata_path = os.path.join(OUTPUT_DIR, 'beatmaps.json')
        
        if os.path.exists(metadata_path):
            with open(metadata_path, 'r') as f:
                beatmaps = json.load(f)
        
        return jsonify({'beatmaps': beatmaps})
    except Exception as e:
        app.logger.error(f"Failed to get beatmaps: {e}")
        return jsonify({'error': 'Failed to get beatmaps'}), 500

@app.route('/api/beatmap/<beatmap_id>', methods=['DELETE'])
def delete_beatmap(beatmap_id):
    """Delete a beatmap and its associated files"""
    try:
        # Parse request data if available
        request_data = request.get_json() if request.is_json else {}
        delete_files = request_data.get('deleteFiles', True)  # Default to true
        
        app.logger.info(f"Deleting beatmap {beatmap_id}, delete_files={delete_files}")
        
        # Get metadata file path
        metadata_path = os.path.join(OUTPUT_DIR, 'beatmaps.json')
        beatmaps = []
        
        if os.path.exists(metadata_path):
            with open(metadata_path, 'r') as f:
                beatmaps = json.load(f)
        
        # Find the beatmap to be deleted
        beatmap_to_delete = None
        updated_beatmaps = []
        
        for beatmap in beatmaps:
            if beatmap.get('id') == beatmap_id:
                beatmap_to_delete = beatmap
            else:
                updated_beatmaps.append(beatmap)
        
        if not beatmap_to_delete:
            app.logger.warning(f"Beatmap {beatmap_id} not found for deletion")
            return jsonify({'status': 'error', 'message': 'Beatmap not found'}), 404
        
        # Update the metadata file
        with open(metadata_path, 'w') as f:
            json.dump(updated_beatmaps, f)
        
        # Delete associated files if requested
        deleted_files = []
        
        if delete_files:
            # Delete beatmap directory if it exists
            beatmap_dir = os.path.join(OUTPUT_DIR, beatmap_id)
            if os.path.exists(beatmap_dir) and os.path.isdir(beatmap_dir):
                shutil.rmtree(beatmap_dir)
                deleted_files.append(f"Directory: {beatmap_id}")
            
            # Delete individual files
            file_patterns = [
                f"{beatmap_id}.mp3",
                f"{beatmap_id}.ogg",
                f"{beatmap_id}_artwork.jpg",
                f"{beatmap_id}_beatmap.zip",
                # Add any other file patterns associated with beatmaps
            ]
            
            for pattern in file_patterns:
                file_path = os.path.join(OUTPUT_DIR, pattern)
                if os.path.exists(file_path):
                    os.remove(file_path)
                    deleted_files.append(f"File: {pattern}")
        
        app.logger.info(f"Deleted beatmap {beatmap_id} and {len(deleted_files)} associated files")
        return jsonify({
            'status': 'success', 
            'message': 'Beatmap deleted',
            'deleted_files': deleted_files
        })
    
    except Exception as e:
        app.logger.error(f"Error deleting beatmap {beatmap_id}: {str(e)}")
        return jsonify({
            'status': 'error', 
            'message': f'Failed to delete beatmap: {str(e)}'
        }), 500


@app.route('/api/clear_beatmaps', methods=['POST'])
def clear_beatmaps():
    """Clear all beatmaps and associated files"""
    try:
        # Parse request data if available
        request_data = request.get_json() if request.is_json else {}
        delete_files = request_data.get('deleteFiles', True)  # Default to true
        
        app.logger.info(f"Clearing all beatmaps, delete_files={delete_files}")
        
        # Get metadata file path
        metadata_path = os.path.join(OUTPUT_DIR, 'beatmaps.json')
        
        # Save empty beatmaps list
        with open(metadata_path, 'w') as f:
            json.dump([], f)
        
        deleted_items = []
        
        # Delete files if requested
        if delete_files:
            # Create a list to store files/directories to preserve
            preserve = ['beatmaps.json', '.gitkeep']
            
            for item in os.listdir(OUTPUT_DIR):
                if item in preserve:
                    continue
                    
                item_path = os.path.join(OUTPUT_DIR, item)
                try:
                    if os.path.isdir(item_path):
                        shutil.rmtree(item_path)
                        deleted_items.append(f"Directory: {item}")
                    else:
                        os.remove(item_path)
                        deleted_items.append(f"File: {item}")
                except Exception as e:
                    app.logger.error(f"Error deleting {item_path}: {str(e)}")
        
        app.logger.info(f"Cleared all beatmaps and {len(deleted_items)} associated files")
        return jsonify({
            'status': 'success', 
            'message': 'All beatmaps cleared',
            'deleted_items': deleted_items
        })
    
    except Exception as e:
        app.logger.error(f"Error clearing beatmaps: {str(e)}")
        return jsonify({
            'status': 'error', 
            'message': f'Failed to clear beatmaps: {str(e)}'
        }), 500

@app.route('/api/update_metadata', methods=['POST'])
def update_metadata():
    """Update beatmap metadata using the JSON file system"""
    try:
        app.logger.info("Update metadata endpoint called")
        
        # Get data from JSON request
        data = request.get_json()
        if not data:
            return jsonify({"status": "error", "message": "No JSON data received"}), 400
            
        beatmap_id = data.get('id')
        if not beatmap_id:
            return jsonify({"status": "error", "message": "Missing beatmap ID"}), 400
            
        title = data.get('title', '')
        artist = data.get('artist', '')
        album = data.get('album', '')
        year = data.get('year', '')
        
        app.logger.info(f"Updating metadata for beatmap: {beatmap_id}")
        app.logger.info(f"New metadata: title='{title}', artist='{artist}', album='{album}', year='{year}'")
        
        # Update the metadata in the JSON file
        try:
            # Read existing beatmaps
            metadata_path = os.path.join(OUTPUT_DIR, 'beatmaps.json')
            beatmaps = []
            
            if os.path.exists(metadata_path):
                with open(metadata_path, 'r') as f:
                    beatmaps = json.load(f)
            
            # Find and update the beatmap
            found = False
            for beatmap in beatmaps:
                if beatmap.get('id') == beatmap_id:
                    beatmap['title'] = title
                    beatmap['artist'] = artist
                    beatmap['album'] = album
                    beatmap['year'] = year
                    found = True
                    break
            
            if not found:
                app.logger.error(f"Beatmap {beatmap_id} not found")
                return jsonify({
                    "status": "error",
                    "message": f"Beatmap with ID {beatmap_id} not found"
                }), 404
            
            # Save updated metadata
            with open(metadata_path, 'w') as f:
                json.dump(beatmaps, f)
            
            app.logger.info(f"Metadata updated successfully for beatmap {beatmap_id}")
            
            # Update info.csv file in beatmap directory if it exists
            beatmap_dir = os.path.join(OUTPUT_DIR, beatmap_id)
            info_path = os.path.join(beatmap_dir, 'info.csv')
            
            if os.path.exists(beatmap_dir) and os.path.exists(info_path):
                app.logger.info(f"Updating info.csv for beatmap {beatmap_id}")
                # Update the info.csv file
                song_metadata = {
                    "title": title,
                    "artist": artist,
                    "album": album,
                    "year": year
                }
                generate_info_csv(song_metadata, info_path)
            
            return jsonify({
                "status": "success",
                "message": "Metadata updated successfully"
            })
            
        except Exception as file_error:
            app.logger.error(f"File error: {str(file_error)}", exc_info=True)
            return jsonify({
                "status": "error",
                "message": f"File error: {str(file_error)}"
            }), 500
            
    except Exception as e:
        app.logger.error(f"Error in update_metadata: {str(e)}", exc_info=True)
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500
    

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
                    try:
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
                    except Exception as e:
                        app.logger.error(f"Error creating notes.csv: {str(e)}")
                
                elif filename == "info.csv":
                    try:
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
                    except Exception as e:
                        app.logger.error(f"Error creating info.csv: {str(e)}")
                
                elif filename == "album.jpg":
                    try:
                        # Create a simple placeholder album art
                        from PIL import Image
                        img = Image.new('RGB', (500, 500), color=(73, 109, 137))
                        img.save(dest_path)
                        app.logger.info(f"Created placeholder album art at {dest_path}")
                    except Exception as e:
                        app.logger.error(f"Error creating album.jpg: {str(e)}")
                
                elif filename == "preview.ogg" and os.path.exists(os.path.join(beatmap_dir, "song.ogg")):
                    try:
                        # Try to create preview from song file
                        from processing.preview_generator import generate_preview
                        song_path = os.path.join(beatmap_dir, "song.ogg")
                        generate_preview(song_path, dest_path)
                        app.logger.info(f"Generated preview.ogg from song.ogg")
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
                    if os.path.exists(zip_path):
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

@app.route('/api/artwork/<beatmap_id>')
def get_artwork(beatmap_id):
    """Serve beatmap artwork"""
    try:
        # Try to find artwork file with common extensions
        extensions = ['.jpg', '.jpeg', '.png', '.gif']
        found = False
        
        # First, check for the standard name
        artwork_path = os.path.join(OUTPUT_DIR, f"{beatmap_id}_artwork.jpg")
        if os.path.exists(artwork_path):
            found = True
        else:
            # Try with different extensions
            for ext in extensions:
                potential_path = os.path.join(OUTPUT_DIR, f"{beatmap_id}_artwork{ext}")
                if os.path.exists(potential_path):
                    artwork_path = potential_path
                    found = True
                    break
        
        if found:
            return send_file(artwork_path, mimetype='image/jpeg')
        else:
            app.logger.warning(f"No artwork found for beatmap {beatmap_id}")
            return '', 404
            
    except Exception as e:
        app.logger.error(f"Error serving artwork: {str(e)}")
        return '', 500

# Call at startup
if __name__ == '__main__':
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    cleanup_output_dir(days=7)
    app.run(debug=False)
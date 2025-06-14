<p align="center">
  <img src="frontend/logo.png" alt="BeatMapper Logo" width="200"/>
</p>

# 🥁 BeatMapper

**BeatMapper** is a modern tool for converting MP3s into playable Drums Rock songs with a beautiful web interface.  
It uses audio processing and AI models to generate drum charts, audio previews, and all required files for Drums Rock custom songs.

---

## 🚀 Features

- 🎵 **MP3 to Drums Rock**: Upload your MP3 and get a ready-to-play Drums Rock song package.
- 🧠 **AI-Powered Chart Generation**: Uses machine learning models to analyze audio and create appropriate drum charts.
- 🎧 **Audio Preview**: Generate preview clips automatically.
- 🎚️ **Metadata Extraction**: Automatically extracts song title, artist, album, and album artwork from your MP3 files.
- 📦 **Modern UI**: Fast, responsive React-based interface.
- 🔄 **Edit Metadata**: Customize song information before finalizing your beatmaps.
- 💾 **Download Ready**: Get complete ZIP packages with all required files.

---

## 🖥️ Requirements

- **Python 3.10.0 (later versions of Python may be incompatible with dependencies)**
- **Node.js 18+ & npm**
- **FFmpeg** (required for audio processing)
- **Git** (recommended)
- **~500MB disk space** (for AI models)

---

## ⚡ Quickstart

### 1. **Clone the Repository**

```sh
git clone https://github.com/yourusername/BeatMapper.git
cd BeatMapper
```

### 2. **Install All Dependencies**

#### On Windows

```sh
installer.bat
```

#### On macOS/Linux/WSL

```sh
bash installer.sh
```

### 3. **Start the Application**

### On Windows
```sh
start.bat
```

### On macOS/Linux/WSL
``` sh
bash start.sh
```

### Or start processes individually

### Start the Backend

```sh
cd backend
python app.py
```

### Start the Frontend

```sh
cd frontend
npm run dev
```

- The frontend will be available at [http://localhost:5173](http://localhost:5173)
- The backend API runs at [http://localhost:5000](http://localhost:5000)

---

## 🛠️ Usage

1. **Upload your MP3** (artwork will be extracted if available).
2. **Review extracted metadata** (title, artist, album, year).
3. **Customize metadata** if needed using the Edit function.
4. **Download the beatmap package** containing:
   - notes.csv (drum chart)
   - song.ogg (audio file)
   - preview.ogg (short preview clip)
   - info.csv (song metadata)
   - album.jpg (artwork)
5. **Import into Drums Rock** and play!

---

## 🧩 Project Structure

```
BeatMapper/
│
├── backend/         # Python Flask API & processing
│   ├── processing/  # Audio, notes, info generators
│   ├── models/      # AI models for beat detection
│   └── app.py       # Main backend server
│
├── frontend/        # React + Vite
│   ├── src/         # React components
│   └── public/      # Static files
│
├── output/          # Generated files (auto-created)
├── installer.sh     # Linux/macOS/WSL installer
├── installer.bat    # Windows installer
└── README.md
```

---

## 🤖 AI Models

BeatMapper uses several AI models for audio processing:

- **Beat Detection Model**: Identifies downbeats and rhythm patterns
- **Drum Part Separation Model**: Isolates drum parts from mixed audio
- **Pattern Recognition Model**: Detects common drum patterns and fills
- **Difficulty Estimator**: Estimates appropriate difficulty levels

On first run, these models will be downloaded automatically (~300MB). They are cached for subsequent use.

---

## 📝 Notes

- **FFmpeg** must be installed and available in your system PATH for audio processing.
- All generated files are saved in the `output/` directory.
- For local use only; no authentication required.
- It's recommended to "Clear All" beatmaps after importing to Drums Rock to free up disk space.
- For best results, use high-quality MP3s with clear drum tracks.
- AI processing may take 1-3 minutes depending on song length and complexity.

---

## ⚠️ Error Handling

BeatMapper includes comprehensive logging and error reporting:

- Check the `beatmapper.log` file in the backend directory for detailed server logs.
- The UI displays user-friendly error messages when issues occur.
- If you encounter problems, check common issues:
  - FFmpeg not installed or not in PATH
  - Insufficient disk space
  - Invalid or corrupted MP3 files
  - Network issues between frontend and backend
  - AI model download failures

---

## 🤝 Contributing

Pull requests and issues are welcome!  
Please open an issue for bugs, feature requests, or questions.

---

## 📄 License

MIT License

---

## 🛠️ API Endpoints

- `GET /api/health` - Check if server is running
- `POST /api/upload` - Upload MP3 and generate beatmap
- `GET /api/download_beatmap/<beatmap_id>` - Download a beatmap ZIP
- `PUT /api/update_beatmap/<beatmap_id>` - Update beatmap metadata
- `DELETE /api/clear_all_beatmaps` - Delete all beatmaps and reset

---

**Enjoy mapping your favorite songs to Drums Rock!**
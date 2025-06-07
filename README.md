<p align="center">
  <img src="frontend/logo.png" alt="BeatMapper Logo" width="200"/>
</p>

# 🥁 BeatMapper

**BeatMapper** is a modern tool for converting MP3s into playable Drums Rock songs with a beautiful web interface.  
It uses advanced audio processing and machine learning to generate accurate drum charts, audio previews, and all required files for Drums Rock custom songs.

---

## 🚀 Features

- 🎵 **MP3 to Drums Rock**: Upload your MP3 and get a ready-to-play Drums Rock song package.
- 🥁 **AI Drum Detection**: Uses state-of-the-art models for drum note extraction.
- 🎚️ **Manual Correction**: Download, edit, and re-upload notes for perfect accuracy.
- 🎧 **Audio Preview**: Listen to the full song and preview clip in the browser.
- 📦 **Modern UI**: Fast, responsive, and easy to use.

---

## 🖥️ Requirements

- **Python 3.9+**
- **Node.js 18+ & npm**
- **FFmpeg** (required for audio processing)
- **Git** (recommended)

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

### 3. **Start the Backend**

```sh
cd backend
python app.py
```

### 4. **Start the Frontend**

```sh
cd frontend
npm run dev
```

- The frontend will be available at [http://localhost:5173](http://localhost:5173)
- The backend API runs at [http://localhost:5000](http://localhost:5000)

---

## 🛠️ Usage

1. **Upload your MP3** (and optional album art).
2. **Fill in song metadata** (title, artist, etc.).
3. **Set BPM/quantization** (or use auto-detect).
4. **Download generated files**: notes.csv, song.ogg, preview.ogg, info.csv, album.jpg.
5. **(Optional) Manual Correction**: Download and edit notes.csv, then re-upload for perfect accuracy.
6. **Import into Drums Rock** and play!

---

## 🧩 Project Structure

```
BeatMapper/
│
├── backend/         # Python Flask API & processing
│   ├── processing/  # Audio, notes, info generators
│   └── app.py       # Main backend server
│
├── frontend/        # React + Vite + Tailwind UI
│   ├── src/         # React components
│   └── public/      # Static files
│
├── output/          # Generated files (auto-created)
├── installer.sh     # Linux/macOS/WSL installer
├── installer.bat    # Windows installer
└── README.md
```

---

## 📝 Notes

- **FFmpeg** must be installed and available in your system PATH for audio processing.
- All generated files are saved in the `output/` directory.
- For local use only; no authentication required.
- For best results, use high-quality MP3s with clear drum tracks.

---

## 🤝 Contributing

Pull requests and issues are welcome!  
Please open an issue for bugs, feature requests, or questions.

---

## 📄 License

MIT License

---

**Enjoy mapping your favorite songs to Drums Rock!**
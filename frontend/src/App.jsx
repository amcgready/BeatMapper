import React, { useRef, useState } from "react";
import { BrowserRouter as Router, Routes, Route, useNavigate, useParams } from "react-router-dom";
import logo from "../logo.png";
import { FaUpload, FaDownload, FaTrash, FaEye, FaSave } from "react-icons/fa";
import JSZip from "jszip";
import { saveAs } from "file-saver";
import { parseBlob } from "music-metadata-browser";

// --- Beatmap Details Page with Edit ---
function BeatmapDetails({ beatmaps, setBeatmaps }) {
  const { id } = useParams();
  const beatmap = beatmaps.find((b) => String(b.id) === id);
  const navigate = useNavigate();

  const [artwork, setArtwork] = useState(beatmap?.artwork || null);
  const [artworkFile, setArtworkFile] = useState(null);
  const [editFields, setEditFields] = useState(
    beatmap
      ? {
          title: beatmap.title,
          artist: beatmap.artist,
          album: beatmap.album,
          year: beatmap.year,
        }
      : { title: "", artist: "", album: "", year: "" }
  );

  if (!beatmap) return <div className="bm-card" style={{ margin: "32px auto", maxWidth: 500 }}>Beatmap not found.</div>;

  const handleChange = (e) => {
    setEditFields((prev) => ({ ...prev, [e.target.name]: e.target.value }));
  };

  const handleArtworkChange = (e) => {
    const file = e.target.files[0];
    setArtworkFile(file);
    if (file) {
      const reader = new FileReader();
      reader.onload = (ev) => setArtwork(ev.target.result);
      reader.readAsDataURL(file);
    } else {
      setArtwork(null);
    }
  };

  const handleSave = (e) => {
    e.preventDefault();
    setBeatmaps((prev) =>
      prev.map((b) =>
        b.id === beatmap.id
          ? {
              ...b,
              ...editFields,
              artwork: artworkFile ? artwork : b.artwork,
              artworkFile: artworkFile || b.artworkFile,
            }
          : b
      )
    );
    navigate("/");
  };

  return (
    <div className="bm-background">
      <div className="bm-container" style={{ maxWidth: 600, margin: "0 auto", padding: 24 }}>
        <button
          className="btn btn-primary"
          style={{ marginBottom: 24, background: "#ffd600", color: "#23272b", border: "none", borderRadius: 6, padding: "10px 20px", fontWeight: "bold" }}
          onClick={() => navigate("/")}
        >
          Back to Beatmaps
        </button>
        <div className="bm-card" style={{ padding: 32 }}>
          <h2 style={{ color: "#ffd600", marginBottom: 24, textAlign: "center" }}>Edit Beatmap Metadata</h2>
          <form onSubmit={handleSave} style={{ display: "flex", flexDirection: "column", gap: 20 }}>
            <div style={{ display: "flex", gap: 24, alignItems: "flex-start" }}>
              <div style={{
                width: 160,
                height: 160,
                background: "#e9ecef",
                borderRadius: 8,
                overflow: "hidden",
                boxShadow: "0 3px 6px rgba(0,0,0,0.1)",
                border: "1px solid #ddd",
                display: "flex",
                alignItems: "center",
                justifyContent: "center"
              }}>
                {artwork ? (
                  <img src={artwork} alt="Album Art" style={{ width: "100%", height: "100%", objectFit: "cover" }} />
                ) : (
                  <span style={{ color: "#aaa" }}>No artwork</span>
                )}
              </div>
              <div style={{ flex: 1 }}>
                <div style={{ marginBottom: 12 }}>
                  <label style={{ color: "#eee", fontWeight: 500 }}>Title</label>
                  <input
                    type="text"
                    name="title"
                    value={editFields.title}
                    onChange={handleChange}
                    required
                    style={{
                      width: "100%",
                      marginTop: 4,
                      padding: 8,
                      borderRadius: 4,
                      border: "1px solid #444",
                      background: "#23272b",
                      color: "#ffd600",
                      fontSize: "1rem"
                    }}
                  />
                </div>
                <div style={{ marginBottom: 12 }}>
                  <label style={{ color: "#eee", fontWeight: 500 }}>Artist</label>
                  <input
                    type="text"
                    name="artist"
                    value={editFields.artist}
                    onChange={handleChange}
                    required
                    style={{
                      width: "100%",
                      marginTop: 4,
                      padding: 8,
                      borderRadius: 4,
                      border: "1px solid #444",
                      background: "#23272b",
                      color: "#ffd600",
                      fontSize: "1rem"
                    }}
                  />
                </div>
                <div style={{ marginBottom: 12 }}>
                  <label style={{ color: "#eee", fontWeight: 500 }}>Album</label>
                  <input
                    type="text"
                    name="album"
                    value={editFields.album}
                    onChange={handleChange}
                    style={{
                      width: "100%",
                      marginTop: 4,
                      padding: 8,
                      borderRadius: 4,
                      border: "1px solid #444",
                      background: "#23272b",
                      color: "#ffd600",
                      fontSize: "1rem"
                    }}
                  />
                </div>
                <div style={{ marginBottom: 12 }}>
                  <label style={{ color: "#eee", fontWeight: 500 }}>Year</label>
                  <input
                    type="number"
                    name="year"
                    value={editFields.year}
                    onChange={handleChange}
                    style={{
                      width: "100%",
                      marginTop: 4,
                      padding: 8,
                      borderRadius: 4,
                      border: "1px solid #444",
                      background: "#23272b",
                      color: "#ffd600",
                      fontSize: "1rem"
                    }}
                  />
                </div>
                <div style={{ marginBottom: 12 }}>
                  <label style={{ color: "#eee", fontWeight: 500 }}>Artwork Image (JPG or PNG)</label>
                  <input
                    type="file"
                    accept="image/jpeg,image/png"
                    onChange={handleArtworkChange}
                    style={{
                      width: "100%",
                      marginTop: 4,
                      padding: 8,
                      borderRadius: 4,
                      border: "1px solid #444",
                      background: "#23272b",
                      color: "#ffd600",
                      fontSize: "1rem"
                    }}
                  />
                </div>
              </div>
            </div>
            <button
              type="submit"
              className="btn btn-success"
              style={{
                background: "#ffd600",
                color: "#23272b",
                border: "none",
                borderRadius: 6,
                padding: "12px 24px",
                fontWeight: "bold",
                width: "100%",
                marginTop: 12,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontSize: "1.1rem"
              }}
            >
              <FaSave style={{ marginRight: 8 }} /> Save Changes
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}

// --- Home Page ---
function Home({ beatmaps, setBeatmaps, logs, setLogs }) {
  const fileInputRef = useRef();
  const [selectedFile, setSelectedFile] = useState(null);
  const navigate = useNavigate();

  const handleFileChange = (e) => {
    const file = e.target.files[0];
    setSelectedFile(file);
    setLogs((prev) => [...prev, `Selected file: ${file?.name || ""}`]);
  };

  const handleUpload = async (e) => {
    e.preventDefault();
    if (selectedFile) {
      setLogs((prev) => [...prev, `Uploading: ${selectedFile.name}`]);
      setTimeout(async () => {
        setLogs((prev) => [...prev, "Processing..."]);
        try {
          // Read file as Blob for music-metadata-browser
          const fileBlob = new Blob([selectedFile], { type: selectedFile.type });


          const metadata = await parseBlob(selectedFile);
          console.log(metadata); // See what is actually extracted
          const common = metadata.common || {};
          setBeatmaps((prev) => [
            ...prev,
            {
              id: Date.now(),
              title: common.title || selectedFile.name.replace(".mp3", ""),
              artist: common.artist || "Unknown",
              album: common.album || "",
              year: common.year || "",
              file: selectedFile,
            },
          ]);
          setLogs((prev) => [...prev, "Metadata extracted.", "Done!"]);
        } catch {
          setBeatmaps((prev) => [
            ...prev,
            {
              id: Date.now(),
              title: selectedFile.name.replace(".mp3", ""),
              artist: "Unknown",
              album: "",
              year: "",
              file: selectedFile,
            },
          ]);
          setLogs((prev) => [...prev, "Could not extract metadata.", "Done!"]);
        }
        setSelectedFile(null);
      }, 800);
    }
  };

  const handleDelete = (id) => {
    setBeatmaps((prev) => prev.filter((b) => b.id !== id));
  };

  const handleDownload = async (beatmap) => {
    const zip = new JSZip();
    zip.file(beatmap.title + ".mp3", beatmap.file);
    const blob = await zip.generateAsync({ type: "blob" });
    saveAs(blob, `${beatmap.title}.zip`);
  };

  return (
    <div className="bm-background">
      <div className="bm-container">
        <img src={logo} alt="BeatMapper Logo" className="bm-logo" />
        <div className="bm-card">
          <form onSubmit={handleUpload} style={{ width: "100%" }}>
            <input
              ref={fileInputRef}
              type="file"
              accept=".mp3"
              onChange={handleFileChange}
              className="bm-file-input"
            />
            <button
              type="button"
              className="bm-browse-btn"
              onClick={() => fileInputRef.current.click()}
            >
              {selectedFile ? selectedFile.name : "Browse for MP3"}
            </button>
            <button
              type="submit"
              className="bm-upload-btn"
              disabled={!selectedFile}
            >
              <FaUpload style={{ marginRight: 8, marginBottom: -2 }} />
              Upload
            </button>
          </form>
        </div>
        <div className="bm-card bm-logs">
          <div className="bm-logs-title">Logs</div>
          <pre className="bm-log-output">{logs.join("\n")}</pre>
        </div>
        <div className="bm-card">
          <div className="bm-logs-title" style={{ marginBottom: 16 }}>
            Your Beatmaps
          </div>
          {beatmaps.length === 0 ? (
            <div className="alert alert-info">
              No beatmaps found. Upload an MP3 file to create one!
            </div>
          ) : (
            <ul
              className="beatmap-list"
              style={{ width: "100%", padding: 0, margin: 0 }}
            >
              {beatmaps.map((b) => (
                <li
                  key={b.id}
                  className="beatmap-item"
                  style={{
                    border: "1px solid #e9ecef",
                    borderRadius: 4,
                    marginBottom: 16,
                    padding: 16,
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    background: "#23272b",
                  }}
                >
                  <div>
                    <span
                      className="beatmap-title"
                      style={{ fontWeight: 600 }}
                    >
                      {b.title}
                    </span>
                    <span
                      className="beatmap-artist"
                      style={{ marginLeft: 8, color: "#aaa" }}
                    >
                      by {b.artist}
                    </span>
                  </div>
                  <div
                    className="beatmap-actions"
                    style={{ display: "flex", gap: 8 }}
                  >
                    <button
                      className="btn btn-primary"
                      style={{ marginRight: 4 }}
                      onClick={() => navigate(`/beatmap/${b.id}`)}
                    >
                      <FaEye /> Details
                    </button>
                    <button
                      className="btn btn-success"
                      style={{ marginRight: 4 }}
                      onClick={() => handleDownload(b)}
                    >
                      <FaDownload /> Download
                    </button>
                    <button
                      className="btn btn-danger"
                      onClick={() => handleDelete(b.id)}
                    >
                      <FaTrash /> Delete
                    </button>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
}

// --- Main App with Routing ---
export default function App() {
  const [logs, setLogs] = useState(["Ready."]);
  const [beatmaps, setBeatmaps] = useState([]);
  return (
    <Router>
      <Routes>
        <Route
          path="/"
          element={
            <Home
              beatmaps={beatmaps}
              setBeatmaps={setBeatmaps}
              logs={logs}
              setLogs={setLogs}
            />
          }
        />
        <Route
          path="/beatmap/:id"
          element={
            <BeatmapDetails
              beatmaps={beatmaps}
              setBeatmaps={setBeatmaps}
            />
          }
        />
      </Routes>
    </Router>
  );
}
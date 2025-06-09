import React, { useState, useRef, useEffect } from "react";
import { BrowserRouter as Router, Routes, Route, Link, useParams, Navigate, useNavigate } from "react-router-dom";
import { FaUpload, FaMusic, FaTrash, FaPencilAlt, FaDownload, FaSave } from "react-icons/fa";
import logo from "../logo.png";
import { saveAs } from "file-saver";
import "./App.css";

// --- Beatmap Details Page with Edit ---
function BeatmapDetails({ beatmaps, setBeatmaps, onDelete }) {
  const { id } = useParams();
  const beatmap = beatmaps.find((b) => String(b.id) === id);
  const navigate = useNavigate();

  const [editMode, setEditMode] = useState(false);
  const [editFields, setEditFields] = useState({
    title: beatmap?.title || "",
    artist: beatmap?.artist || "",
    album: beatmap?.album || "",
    year: beatmap?.year || ""
  });

  const [uploadingMetadata, setUploadingMetadata] = useState(false);

  if (!beatmap) {
    return <Navigate to="/" replace />;
  }

  const handleChange = (e) => {
    const { name, value } = e.target;
    setEditFields((prev) => ({ ...prev, [name]: value }));
  };

  const handleSave = async () => {
    setUploadingMetadata(true);
    
    try {
      // Send updated metadata to backend
      const response = await fetch("/api/update_metadata", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          id: beatmap.id,
          ...editFields
        }),
      });

      if (!response.ok) {
        throw new Error("Failed to update metadata");
      }

      // Update local state
      setBeatmaps(prev => 
        prev.map(b => b.id === beatmap.id ? { ...b, ...editFields } : b)
      );
      
      setEditMode(false);
    } catch (error) {
      console.error("Error updating metadata:", error);
      alert("Failed to update metadata. Please try again.");
    } finally {
      setUploadingMetadata(false);
    }
  };

  const handleDownload = async () => {
    try {
      const response = await fetch(`/api/download_beatmap/${beatmap.id}`);
      if (!response.ok) {
        throw new Error("Failed to download beatmap");
      }

      const blob = await response.blob();
      saveAs(blob, `${beatmap.title}_beatmap.zip`);
    } catch (error) {
      console.error("Error downloading beatmap:", error);
      alert("Failed to download beatmap. Please try again.");
    }
  };

  return (
    <div className="bm-background min-h-screen pb-12">
      <div className="bm-container max-w-4xl mx-auto pt-16 px-4">
        <div className="flex justify-center mb-8">
          <img src={logo} alt="BeatMapper Logo" style={{ maxWidth: "200px" }} />
        </div>

        <div className="mb-4">
          <Link to="/" className="text-blue-400 hover:text-blue-300 inline-block">
            &larr; Back to Home
          </Link>
        </div>

        <div className="bm-card">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-2xl font-bold">{editMode ? "Edit Beatmap" : "Beatmap Details"}</h2>
            <div>
              {!editMode && (
                <>
                  <button
                    onClick={() => setEditMode(true)}
                    className="mr-2 bg-yellow-500 hover:bg-yellow-600 text-black py-1 px-3 rounded"
                  >
                    <FaPencilAlt className="inline mr-1" /> Edit
                  </button>
                  <button
                    onClick={handleDownload}
                    className="bg-green-600 hover:bg-green-700 text-white py-1 px-3 rounded"
                  >
                    <FaDownload className="inline mr-1" /> Download
                  </button>
                </>
              )}
            </div>
          </div>

          {editMode ? (
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-semibold mb-1">Song Title:</label>
                <input
                  type="text"
                  name="title"
                  value={editFields.title}
                  onChange={handleChange}
                  className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2"
                />
              </div>

              <div>
                <label className="block text-sm font-semibold mb-1">Artist:</label>
                <input
                  type="text"
                  name="artist"
                  value={editFields.artist}
                  onChange={handleChange}
                  className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2"
                />
              </div>

              <div>
                <label className="block text-sm font-semibold mb-1">Album:</label>
                <input
                  type="text"
                  name="album"
                  value={editFields.album}
                  onChange={handleChange}
                  className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2"
                />
              </div>

              <div>
                <label className="block text-sm font-semibold mb-1">Year:</label>
                <input
                  type="text"
                  name="year"
                  value={editFields.year}
                  onChange={handleChange}
                  className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2"
                />
              </div>

              <div className="flex justify-end space-x-2 mt-4">
                <button
                  onClick={() => setEditMode(false)}
                  className="bg-gray-600 hover:bg-gray-700 text-white py-2 px-4 rounded"
                >
                  Cancel
                </button>
                <button
                  onClick={handleSave}
                  disabled={uploadingMetadata}
                  className="bg-blue-600 hover:bg-blue-700 text-white py-2 px-4 rounded flex items-center"
                >
                  {uploadingMetadata ? (
                    <>
                      <span className="mr-2">Saving...</span>
                      <div className="animate-spin h-5 w-5 border-2 border-white border-t-transparent rounded-full"></div>
                    </>
                  ) : (
                    <>
                      <FaSave className="mr-2" /> Save Changes
                    </>
                  )}
                </button>
              </div>
            </div>
          ) : (
            <div className="space-y-2">
              <p><strong>Title:</strong> {beatmap.title}</p>
              <p><strong>Artist:</strong> {beatmap.artist}</p>
              <p><strong>Album:</strong> {beatmap.album}</p>
              <p><strong>Year:</strong> {beatmap.year}</p>
              <p><strong>Created:</strong> {new Date(beatmap.createdAt).toLocaleString()}</p>
            </div>
          )}

          <div className="mt-6 border-t border-gray-700 pt-4">
            <button
              onClick={() => {
                if (window.confirm("Are you sure you want to delete this beatmap?")) {
                  onDelete(beatmap.id);
                  navigate("/");
                }
              }}
              className="bg-red-600 hover:bg-red-700 text-white py-1 px-3 rounded"
            >
              <FaTrash className="inline mr-1" /> Delete Beatmap
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

// --- Home Page ---
function Home({ beatmaps, setBeatmaps, logs, setLogs, onDelete }) {
  const fileInputRef = useRef();
  const [selectedFile, setSelectedFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const navigate = useNavigate();

  const handleFileChange = (e) => {
    const file = e.target.files[0];
    setSelectedFile(file);
    setLogs((prev) => [...prev, `Selected file: ${file?.name || ""}`]);
  };

  const handleUpload = async (e) => {
    e.preventDefault();
    if (selectedFile) {
      setUploading(true);
      setLogs((prev) => [...prev, `Uploading: ${selectedFile.name}`]);
      const formData = new FormData();
      formData.append("file", selectedFile);
      
      setLogs((prev) => [...prev, "Preparing upload..."]);
      try {
        setLogs((prev) => [...prev, "Sending file to server..."]);
        const response = await fetch("/api/upload", {
          method: "POST",
          body: formData,
        });

        setLogs((prev) => [...prev, "Awaiting server response..."]);
        if (!response.ok) {
          setLogs((prev) => [...prev, `Server responded with status: ${response.status}`]);
          throw new Error(`Upload failed with status: ${response.status}`);
        }
        
        const contentType = response.headers.get("content-type");
        if (contentType && contentType.includes("application/json")) {
          const data = await response.json();
          setLogs((prev) => [...prev, "Server processed file successfully"]);
          
          if (data.status === "success") {
            // Add new beatmap to state
            const newBeatmap = {
              id: data.id,
              title: data.title || selectedFile.name.replace('.mp3', ''),
              artist: data.artist || "Unknown Artist",
              album: data.album || "Unknown Album",
              year: data.year || new Date().getFullYear().toString(),
              createdAt: new Date().toISOString()
            };
            
            setBeatmaps(prev => [...prev, newBeatmap]);
            setLogs((prev) => [...prev, `Beatmap created: ${newBeatmap.title}`, "Done!"]);
          } else {
            setLogs((prev) => [...prev, `Server responded with error: ${data.error || 'Unknown error'}`, "Done!"]);
          }
        } else {
          // Handle binary response (ZIP file download)
          const blob = await response.blob();
          const filename = `${selectedFile.name.replace(".mp3", "")}_beatmap.zip`;
          saveAs(blob, filename);
          
          setLogs((prev) => [...prev, `Downloaded beatmap package: ${filename}`, "Done!"]);
        }
      } catch (err) {
        setLogs((prev) => [...prev, `Upload failed: ${err.message}`, "Done!"]);
      } finally {
        setUploading(false);
        setSelectedFile(null);
        if (fileInputRef.current) {
          fileInputRef.current.value = "";
        }
      }
    }
  };

  const handleClearBeatmaps = async () => {
    if (!window.confirm("Are you sure you want to clear all beatmaps? This action cannot be undone.")) {
      return;
    }
    
    try {
      const response = await fetch("/api/clear_beatmaps", {
        method: "POST"
      });
      
      if (!response.ok) {
        throw new Error("Failed to clear beatmaps");
      }
      
      setBeatmaps([]);
      setLogs((prev) => [...prev, "All beatmaps cleared"]);
    } catch (error) {
      console.error("Error clearing beatmaps:", error);
      setLogs((prev) => [...prev, `Failed to clear beatmaps: ${error.message}`]);
    }
  };

  return (
    <div className="bm-background min-h-screen pb-12">
      <div className="bm-container pt-16" style={{ maxWidth: "100%", padding: "0 20px" }}>
        {/* Logo with more space */}
        <div className="flex justify-center mb-8">
          <img src={logo} alt="BeatMapper Logo" className="bm-logo" style={{ maxWidth: "200px" }} />
        </div>
        
        {/* Upload section */}
        <div className="bm-card w-full max-w-4xl mx-auto">
          <h2 className="text-xl font-bold mb-4">Upload New Song</h2>
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
              className="bm-browse-btn mb-4"
              onClick={() => fileInputRef.current.click()}
            >
              {selectedFile ? selectedFile.name : "Browse for MP3"}
            </button>
            <button
              type="submit"
              className="bm-upload-btn"
              disabled={!selectedFile || uploading}
            >
              {uploading ? (
                <div className="flex items-center justify-center">
                  <div className="animate-spin mr-2 h-5 w-5 border-2 border-white border-t-transparent rounded-full"></div>
                  <span>Uploading...</span>
                </div>
              ) : (
                <>
                  <FaUpload style={{ marginRight: 8 }} /> Upload
                </>
              )}
            </button>
          </form>
        </div>

        {/* Logs section - with proper layout overrides */}
        <div className="bm-card bm-card-full mt-6 mx-auto">
          <div className="bm-logs-title" style={{ textAlign: "left", width: "100%" }}>Logs</div>
          <pre className="bm-log-output" style={{ width: "100%", textAlign: "left" }}>
            {logs.join("\n")}
          </pre>
        </div>

        {/* Your Beatmaps Section - with proper layout overrides */}
        <div className="bm-card bm-card-full mt-6 mx-auto">
          <div style={{ 
            display: "flex", 
            justifyContent: "space-between", 
            alignItems: "center", 
            width: "100%",
            marginBottom: "1rem"
          }}>
            <h2 className="text-xl font-bold">Your Beatmaps</h2>
            {beatmaps.length > 0 && (
              <button
                onClick={handleClearBeatmaps}
                className="bg-red-600 hover:bg-red-700 text-white py-1 px-3 rounded text-sm flex items-center"
              >
                <FaTrash className="mr-1" /> Clear All
              </button>
            )}
          </div>

          {beatmaps.length === 0 ? (
            <p className="text-gray-400 text-center py-6">No beatmaps yet. Upload an MP3 to create one.</p>
          ) : (
            <div style={{ width: "100%" }}>
              {beatmaps.map((beatmap, index) => (
                <div key={beatmap.id} style={{ 
                  width: "100%",
                  borderBottom: index < beatmaps.length - 1 ? "1px solid #374151" : "none"
                }}>
                  <div style={{ 
                    display: "flex", 
                    alignItems: "center", 
                    padding: "1rem",
                    backgroundColor: "#1f2937",
                    width: "100%"
                  }}>
                    {/* Album Art */}
                    <div style={{ 
                      height: "48px", 
                      width: "48px", 
                      backgroundColor: "#374151",
                      borderRadius: "0.25rem",
                      marginRight: "1rem",
                      flexShrink: 0,
                      overflow: "hidden"
                    }}>
                      <img 
                        src={beatmap.artwork || "https://via.placeholder.com/48"} 
                        alt="Album art"
                        style={{ height: "100%", width: "100%", objectFit: "cover" }}
                        onError={(e) => { e.target.src = "https://via.placeholder.com/48"; }}
                      />
                    </div>
                    
                    {/* Song Info */}
                    <div style={{ flexGrow: 1, textAlign: "left" }}>
                      <div style={{ fontWeight: "500" }}>{beatmap.title}</div>
                      <div style={{ fontSize: "0.875rem", color: "#9ca3af" }}>{beatmap.artist}</div>
                    </div>
                    
                    {/* Buttons */}
                    <div style={{ display: "flex", gap: "0.75rem" }}>
                      <button
                        onClick={() => navigate(`/beatmap/${beatmap.id}`)}
                        className="bg-blue-600 hover:bg-blue-700 text-white py-1 px-3 rounded text-sm flex items-center"
                      >
                        <FaPencilAlt className="mr-1" /> Edit
                      </button>
                      <button
                        onClick={() => onDelete(beatmap.id)}
                        className="bg-red-600 hover:bg-red-700 text-white py-1 px-3 rounded text-sm flex items-center"
                      >
                        <FaTrash className="mr-1" /> Delete
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// --- Main App with Routing ---
export default function App() {
  const [beatmaps, setBeatmaps] = useState(() => {
    // Load beatmaps from localStorage on startup
    const savedBeatmaps = localStorage.getItem("beatmaps");
    return savedBeatmaps ? JSON.parse(savedBeatmaps) : [];
  });
  
  const [logs, setLogs] = useState(["Ready."]);

  // Save beatmaps to localStorage whenever they change
  useEffect(() => {
    localStorage.setItem("beatmaps", JSON.stringify(beatmaps));
  }, [beatmaps]);

  // Fetch existing beatmaps from server on load
  useEffect(() => {
    const fetchBeatmaps = async () => {
      try {
        const response = await fetch("/api/beatmaps");
        if (response.ok) {
          const data = await response.json();
          setBeatmaps(data.beatmaps);
        }
      } catch (error) {
        console.error("Failed to fetch beatmaps:", error);
        // If server fetch fails, we'll still have local storage as backup
      }
    };

    fetchBeatmaps();
  }, []);

  const handleDeleteBeatmap = async (id) => {
    try {
      // Send delete request to server
      await fetch(`/api/beatmap/${id}`, {
        method: "DELETE"
      });
      
      // Update local state
      setBeatmaps(prev => prev.filter(b => b.id !== id));
      setLogs(prev => [...prev, `Deleted beatmap ID: ${id}`]);
    } catch (error) {
      console.error("Failed to delete beatmap:", error);
      setLogs(prev => [...prev, `Failed to delete beatmap: ${error.message}`]);
    }
  };

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
              onDelete={handleDeleteBeatmap}
            />
          }
        />
        <Route
          path="/beatmap/:id"
          element={
            <BeatmapDetails
              beatmaps={beatmaps}
              setBeatmaps={setBeatmaps}
              onDelete={handleDeleteBeatmap}
            />
          }
        />
      </Routes>
    </Router>
  );
}
import React, { useState, useRef, useEffect } from "react";
import { BrowserRouter as Router, Routes, Route, Link, useParams, Navigate, useNavigate } from "react-router-dom";
import { FaUpload, FaMusic, FaTrash, FaPencilAlt, FaDownload, FaSave, FaTimes, FaFolder } from "react-icons/fa";
import logo from "../logo.png";
import { saveAs } from "file-saver";
import "./App.css";
import { extractAudioMetadata } from './utils/audioMetadata';

// --- Improved Metadata Edit Modal Component ---
function MetadataEditModal({ isOpen, onClose, beatmap, onSave }) {  const [metadata, setMetadata] = useState({
    title: beatmap?.title || "",
    artist: beatmap?.artist || "",
    song_map: beatmap?.song_map || "VULCAN",
    difficulty: beatmap?.difficulty ? (() => {
      // Convert numeric difficulty back to string for dropdown
      const difficultyMap = { "0": "EASY", "1": "MEDIUM", "2": "HARD", "3": "EXTREME" };
      return difficultyMap[beatmap.difficulty] || "AUTO";
    })() : "AUTO",
  });
    const [albumArt, setAlbumArt] = useState(null);
  const [albumArtPreview, setAlbumArtPreview] = useState(beatmap?.artwork || null);
  const [isSaving, setIsSaving] = useState(false);
  const [progress, setProgress] = useState({ percent: 0, message: "", isRegenerating: false });
    // Reset form when beatmap changes
  useEffect(() => {    if (beatmap) {      setMetadata({
        title: beatmap.title || "",
        artist: beatmap.artist || "",
        song_map: beatmap.song_map || "VULCAN",
        difficulty: beatmap.difficulty ? (() => {
          // Convert numeric difficulty back to string for dropdown
          const difficultyMap = { "0": "EASY", "1": "MEDIUM", "2": "HARD", "3": "EXTREME" };
          return difficultyMap[beatmap.difficulty] || "AUTO";
        })() : "AUTO",
      });
      setAlbumArtPreview(beatmap.artwork || null);
    }
  }, [beatmap]);
  
  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setMetadata({
      ...metadata,
      [name]: value,
    });
  };
  
  const handleAlbumArtChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      const reader = new FileReader();
      reader.onloadend = () => {
        setAlbumArtPreview(reader.result);
      };
      reader.readAsDataURL(file);
      setAlbumArt(file);
    }  };
  
  const pollProgress = async (taskId) => {
    let attempts = 0;
    const maxAttempts = 60; // 60 seconds max
      const poll = async () => {
      try {
        console.log(`Polling progress for task ${taskId}, attempt ${attempts + 1}`);
        const response = await fetch(`/api/progress/${taskId}`);
        const progressData = await response.json();
        
        console.log("Progress data received:", progressData);
        
        setProgress({
          percent: progressData.progress || 0,
          message: progressData.message || "Processing...",
          isRegenerating: progressData.status === 'in_progress'
        });
        
        console.log("Updated progress state:", {
          percent: progressData.progress || 0,
          message: progressData.message || "Processing...",
          isRegenerating: progressData.status === 'in_progress'
        });
        
        if (progressData.status === 'completed') {
          setProgress({ percent: 100, message: "Completed!", isRegenerating: false });
          return true; // Done
        } else if (progressData.status === 'error') {
          setProgress({ percent: 0, message: progressData.message || "Error occurred", isRegenerating: false });
          return true; // Stop polling
        } else if (attempts < maxAttempts) {
          attempts++;
          setTimeout(poll, 1000); // Poll every second
        } else {
          setProgress({ percent: 0, message: "Timeout", isRegenerating: false });
        }
      } catch (error) {
        console.error("Error polling progress:", error);
        setProgress({ percent: 0, message: "Error checking progress", isRegenerating: false });
      }
    };
    
    poll();
  };
  
  const handleSave = async () => {
    if (!beatmap) return;
    
    setIsSaving(true);
    setProgress({ percent: 0, message: "Saving changes...", isRegenerating: false });
    
    try {
      // Use the correct endpoint with beatmap ID in the URL
      const response = await fetch(`/api/update_beatmap/${beatmap.id}`, {
        method: "PUT",  // Match the backend's expected method
        headers: {
          "Content-Type": "application/json"
        },        body: JSON.stringify({
          title: metadata.title || "",
          artist: metadata.artist || "",
          // Only send difficulty if user explicitly selected one (not AUTO)
          ...(metadata.difficulty !== "AUTO" && { difficulty: metadata.difficulty }),
          song_map: metadata.song_map || "VULCAN"
        })
      });
      
      if (!response.ok) {
        const errorText = await response.text();
        console.error("Server error response:", errorText);
        throw new Error(`Server error: ${errorText}`);
      }      const result = await response.json();
      
      // Debug logging
      console.log("Update response:", result);
      console.log("Has regenerating flag:", result.regenerating);
      console.log("Has progress_task_id:", result.progress_task_id);
      
      if (result.status === "success") {
        // Check if note regeneration is happening
        if (result.regenerating && result.progress_task_id) {
          console.log("Starting progress tracking for task:", result.progress_task_id);
          setProgress({ percent: 5, message: "Starting note regeneration...", isRegenerating: true });
          // Start polling for progress
          pollProgress(result.progress_task_id);
          
          // Wait for regeneration to complete before updating UI
          const checkCompletion = setInterval(() => {
            if (!progress.isRegenerating) {
              clearInterval(checkCompletion);
              
              const updatedBeatmap = {
                ...beatmap,
                title: result.title,
                artist: result.artist,
                difficulty: result.difficulty,
                song_map: result.song_map,
                artwork: albumArtPreview || beatmap.artwork
              };
              
              onSave(updatedBeatmap);
              setIsSaving(false);
              onClose();
            }
          }, 500);        } else {
          // No regeneration needed, update immediately
          console.log("No regeneration needed, updating immediately");
          const updatedBeatmap = {
            ...beatmap,
            title: result.title,
            artist: result.artist,
            difficulty: result.difficulty, // Use numeric difficulty from backend response
            song_map: result.song_map,
            artwork: albumArtPreview || beatmap.artwork
          };
          
          onSave(updatedBeatmap);
          setIsSaving(false);
          onClose();
        }
      } else {
        throw new Error(result.message || "Unknown error updating metadata");
      }    } catch (error) {
      console.error("Error updating metadata:", error);
      alert(`Failed to update metadata: ${error.message}`);
      setProgress({ percent: 0, message: "", isRegenerating: false });
      setIsSaving(false);
    }
  };

  if (!isOpen) return null;
  
  return (
    // This is a fixed position overlay that covers the entire viewport
    <div style={{
      position: "fixed",
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      backgroundColor: "rgba(0, 0, 0, 0.7)",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      zIndex: 1000
    }}>
      {/* This is the modal container with fixed dimensions */}
      <div style={{
        backgroundColor: "#23272b",
        border: "1px solid #444",
        borderRadius: "12px",
        boxShadow: "0 2px 20px rgba(0, 0, 0, 0.6)",
        padding: "32px",
        width: "90%",
        maxWidth: "700px",
        maxHeight: "90vh",
        overflow: "auto",
        position: "relative"
      }}>        <h2 className="text-xl font-bold text-center mb-6">Edit Song Metadata</h2>
        
        <button 
          onClick={onClose} 
          style={{
            position: "absolute",
            top: "20px",
            right: "20px",
            background: "none",
            border: "none",
            fontSize: "24px",
            cursor: "pointer",
            color: "#999",
          }}
        >
          &#10005;
        </button>
        
        {/* Detected Difficulty Display */}
        <div style={{
          position: "absolute",
          top: "60px",
          right: "20px",
          padding: "8px 12px",
          borderRadius: "6px",
          fontSize: "12px",
          fontWeight: "bold",
          backgroundColor: (() => {
            const difficultyColors = {
              0: "#22c55e", // Green for EASY
              1: "#eab308", // Yellow for MEDIUM  
              2: "#f97316", // Orange for HARD
              3: "#ef4444"  // Red for EXTREME
            };
            return difficultyColors[beatmap?.difficulty] || "#6b7280";
          })(),
          color: "white",
          border: "1px solid rgba(255,255,255,0.2)",
          boxShadow: "0 2px 4px rgba(0,0,0,0.3)"        }}>
          Detected Difficulty: {(() => {
            const difficultyNames = ["EASY", "MEDIUM", "HARD", "EXTREME"];
            return difficultyNames[beatmap?.difficulty] || "UNKNOWN";
          })()}
        </div>
        
        <div style={{
          display: "flex",
          flexDirection: "row",
          marginBottom: "24px",
          alignItems: "center",
        }}>
          <div style={{
            width: "150px",
            height: "150px",
            backgroundColor: "#1a1d20",
            border: "1px solid #444",
            marginRight: "24px",
            flexShrink: 0,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}>
            {albumArtPreview ? (
              <img 
                src={albumArtPreview} 
                alt="Album artwork" 
                style={{ width: "100%", height: "100%", objectFit: "cover" }}
                onError={() => setAlbumArtPreview(null)}
              />
            ) : (
              <div style={{ color: "#777", textAlign: "center" }}>
                No Album Art
              </div>
            )}
          </div>
          
          <div>
            <div className="mb-3">Choose Album Art</div>
            <input
              type="file"
              accept="image/*"
              onChange={handleAlbumArtChange}
              style={{ display: "none" }}
              id="album-art-input"
            />
            <label 
              htmlFor="album-art-input" 
              style={{
                backgroundColor: "#444",
                border: "none",
                borderRadius: "4px",
                padding: "8px 16px",
                cursor: "pointer",
                display: "inline-block",
                marginRight: "10px",
              }}
            >
              Browse...
            </label>
            <span style={{ color: "#999" }}>
              {albumArt ? albumArt.name : "No file selected"}
            </span>
          </div>
        </div>
        
        <div style={{ marginBottom: "16px", textAlign: "left" }}>
          <div style={{ marginBottom: "8px" }}>Song Title</div>
          <input
            type="text"
            name="title"
            value={metadata.title}
            onChange={handleInputChange}
            style={{
              width: "100%",
              backgroundColor: "#1a1d20",
              border: "1px solid #444",
              borderRadius: "4px",
              padding: "8px 12px",
              color: "white",
            }}
          />
        </div>
          <div style={{ marginBottom: "16px", textAlign: "left" }}>
          <div style={{ marginBottom: "8px" }}>Artist</div>
          <input
            type="text"
            name="artist"
            value={metadata.artist}
            onChange={handleInputChange}
            style={{
              width: "100%",
              backgroundColor: "#1a1d20",
              border: "1px solid #444",
              borderRadius: "4px",
              padding: "8px 12px",
              color: "white",
            }}
          />        </div>
          <div style={{ marginBottom: "16px", textAlign: "left" }}>
          <div style={{ marginBottom: "12px" }}>
            Difficulty Override 
            <span style={{ color: "#999", fontSize: "12px", marginLeft: "8px" }}>
              (Optional - click "Auto-Detect" to use detected value)
            </span>
          </div>
          <div style={{ display: "flex", flexWrap: "wrap", gap: "8px", alignItems: "center" }}>
            <button
              type="button"
              onClick={() => handleInputChange({ target: { name: "difficulty", value: "AUTO" } })}
              style={{
                padding: "8px 16px",
                borderRadius: "6px",
                border: "2px solid",
                cursor: "pointer",
                fontWeight: "bold",
                fontSize: "14px",
                backgroundColor: (metadata.difficulty || "AUTO") === "AUTO" ? "#6b7280" : "transparent",
                borderColor: (metadata.difficulty || "AUTO") === "AUTO" ? "#6b7280" : "#4b5563",
                color: (metadata.difficulty || "AUTO") === "AUTO" ? "white" : "#9ca3af",
                transition: "all 0.2s ease",
              }}
            >
              Auto-Detect
            </button>
            <button
              type="button"
              onClick={() => handleInputChange({ target: { name: "difficulty", value: "EASY" } })}
              style={{
                padding: "8px 16px",
                borderRadius: "6px",
                border: "2px solid",
                cursor: "pointer",
                fontWeight: "bold",
                fontSize: "14px",
                backgroundColor: metadata.difficulty === "EASY" ? "#22c55e" : "transparent",
                borderColor: metadata.difficulty === "EASY" ? "#22c55e" : "#16a34a",
                color: metadata.difficulty === "EASY" ? "white" : "#22c55e",
                transition: "all 0.2s ease",
              }}
            >
              EASY
            </button>
            <button
              type="button"
              onClick={() => handleInputChange({ target: { name: "difficulty", value: "MEDIUM" } })}
              style={{
                padding: "8px 16px",
                borderRadius: "6px",
                border: "2px solid",
                cursor: "pointer",
                fontWeight: "bold",
                fontSize: "14px",
                backgroundColor: metadata.difficulty === "MEDIUM" ? "#eab308" : "transparent",
                borderColor: metadata.difficulty === "MEDIUM" ? "#eab308" : "#ca8a04",
                color: metadata.difficulty === "MEDIUM" ? "white" : "#eab308",
                transition: "all 0.2s ease",
              }}
            >
              MEDIUM
            </button>
            <button
              type="button"
              onClick={() => handleInputChange({ target: { name: "difficulty", value: "HARD" } })}
              style={{
                padding: "8px 16px",
                borderRadius: "6px",
                border: "2px solid",
                cursor: "pointer",
                fontWeight: "bold",
                fontSize: "14px",
                backgroundColor: metadata.difficulty === "HARD" ? "#f97316" : "transparent",
                borderColor: metadata.difficulty === "HARD" ? "#f97316" : "#ea580c",
                color: metadata.difficulty === "HARD" ? "white" : "#f97316",
                transition: "all 0.2s ease",
              }}
            >
              HARD
            </button>
            <button
              type="button"
              onClick={() => handleInputChange({ target: { name: "difficulty", value: "EXTREME" } })}
              style={{
                padding: "8px 16px",
                borderRadius: "6px",
                border: "2px solid",
                cursor: "pointer",
                fontWeight: "bold",
                fontSize: "14px",
                backgroundColor: metadata.difficulty === "EXTREME" ? "#ef4444" : "transparent",
                borderColor: metadata.difficulty === "EXTREME" ? "#ef4444" : "#dc2626",
                color: metadata.difficulty === "EXTREME" ? "white" : "#ef4444",
                transition: "all 0.2s ease",
              }}
            >
              EXTREME
            </button>
          </div>
        </div>
        
        <div style={{ marginBottom: "24px", textAlign: "left" }}>
          <div style={{ marginBottom: "8px" }}>Stage Select</div>
          <select
            name="song_map"
            value={metadata.song_map}
            onChange={handleInputChange}
            style={{
              width: "100%",
              backgroundColor: "#1a1d20",
              border: "1px solid #444",
              borderRadius: "4px",
              padding: "8px 12px",              color: "white",
            }}
          >
            <option value="VULCAN">Vulcan</option>
            <option value="DESERT">Desert</option>
            <option value="STORM">Storm</option>
          </select>
        </div>        {/* Debug Info */}
        {(isSaving || progress.isRegenerating) && (
          <div style={{ 
            marginTop: "16px", 
            padding: "8px", 
            backgroundColor: "#333", 
            borderRadius: "4px",
            fontSize: "12px",
            color: "#ccc"
          }}>
            Debug: isSaving={isSaving.toString()}, isRegenerating={progress.isRegenerating.toString()}, percent={progress.percent}, message="{progress.message}"
          </div>
        )}
          {/* Progress Bar */}
        {(progress.isRegenerating || (isSaving && progress.percent > 0)) && (
          <div style={{ marginTop: "20px" }}>
            <div style={{ 
              color: "#ccc", 
              fontSize: "14px", 
              marginBottom: "8px",
              textAlign: "center"
            }}>
              {progress.message}
            </div>
            <div style={{
              width: "100%",
              height: "8px",
              backgroundColor: "#333",
              borderRadius: "4px",
              overflow: "hidden"
            }}>
              <div style={{
                width: `${progress.percent}%`,
                height: "100%",
                backgroundColor: "#2563eb",
                borderRadius: "4px",
                transition: "width 0.3s ease"
              }} />
            </div>
            <div style={{ 
              color: "#999", 
              fontSize: "12px", 
              marginTop: "4px",
              textAlign: "center"
            }}>
              {progress.percent}% complete
            </div>
          </div>
        )}
        
        <div style={{ 
          display: "flex", 
          justifyContent: "center", 
          gap: "16px",
          marginTop: "24px",
        }}>
          <button
            onClick={onClose}
            style={{
              backgroundColor: "#444",
              border: "none",
              borderRadius: "4px",
              padding: "10px 24px",
              cursor: "pointer",
            }}
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            disabled={isSaving}
            style={{
              backgroundColor: "#2563eb",
              border: "none",
              borderRadius: "4px",
              padding: "10px 24px",
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              gap: "8px",
              opacity: isSaving ? 0.7 : 1,
            }}
          >
            {isSaving ? (
              <>
                <div 
                  style={{
                    width: "16px",
                    height: "16px",
                    border: "2px solid rgba(255,255,255,0.3)",
                    borderTop: "2px solid white",
                    borderRadius: "50%",
                  }}                  className="spin-animation"
                ></div>
                {progress.isRegenerating ? "Regenerating Notes..." : "Saving..."}
              </>
            ) : (
              <>
                <FaSave />
                Save Changes
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}

// --- Beatmap Details Page with Edit ---
function BeatmapDetails({ beatmaps, setBeatmaps, onDelete }) {
  const { id } = useParams();
  const beatmap = beatmaps.find((b) => String(b.id) === id);
  const navigate = useNavigate();

  const [editMode, setEditMode] = useState(false);  const [editFields, setEditFields] = useState({
    title: beatmap?.title || "",
    artist: beatmap?.artist || "",
    song_map: beatmap?.song_map || "VULCAN",
    difficulty: beatmap?.difficulty ? (() => {
      // Convert numeric difficulty back to string for dropdown
      const difficultyMap = { "0": "EASY", "1": "MEDIUM", "2": "HARD", "3": "EXTREME" };
      return difficultyMap[beatmap.difficulty] || "AUTO";
    })() : "AUTO",
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
      // Use the correct endpoint with beatmap ID in the URL
      const response = await fetch(`/api/update_beatmap/${beatmap.id}`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json"
        },        body: JSON.stringify({
          id: beatmap.id,
          title: editFields.title,
          artist: editFields.artist,
          // Only send difficulty if user explicitly selected one (not AUTO)
          ...(editFields.difficulty !== "AUTO" && { difficulty: editFields.difficulty }),
          song_map: editFields.song_map
        })
      });

      if (!response.ok) {
        const errorData = await response.text();
        console.error("Server error on update_metadata:", errorData);
        throw new Error(`Failed to update metadata: ${response.status}`);
      }

      const result = await response.json();
        if (result.status === "success") {
        // Update local state with the response data from backend (which has correct numeric difficulty)
        setBeatmaps(prev => 
          prev.map(b => b.id === beatmap.id ? { 
            ...b, 
            title: result.title,
            artist: result.artist,
            difficulty: result.difficulty, // Use numeric difficulty from backend response
            song_map: result.song_map
          } : b)
        );
        
        setEditMode(false);
      } else {
        throw new Error(result.message || "Unknown error updating metadata");
      }
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
              </div>              <div>
                <label className="block text-sm font-semibold mb-1">Artist:</label>
                <input
                  type="text"
                  name="artist"
                  value={editFields.artist}
                  onChange={handleChange}
                  className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2"
                />              </div>              <div>
                <label className="block text-sm font-semibold mb-1">Song Map:</label>
                <select
                  name="song_map"
                  value={editFields.song_map}
                  onChange={handleChange}                  className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2"
                >
                  <option value="VULCAN">Vulcan</option>
                  <option value="DESERT">Desert</option>
                  <option value="STORM">Storm</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-semibold mb-2">
                  Difficulty Override
                  <span className="text-gray-400 text-xs ml-2">
                    (Optional - click "Auto-Detect" to use detected value)
                  </span>
                </label>
                <div className="flex flex-wrap gap-2 items-center">
                  <button
                    type="button"
                    onClick={() => setEditFields(prev => ({ ...prev, difficulty: "AUTO" }))}
                    className={`px-4 py-2 rounded-md border-2 font-bold text-sm transition-all duration-200 ${
                      editFields.difficulty === "AUTO" 
                        ? "bg-gray-500 border-gray-500 text-white" 
                        : "bg-transparent border-gray-600 text-gray-400 hover:border-gray-500"
                    }`}
                  >
                    Auto-Detect
                  </button>
                  <button
                    type="button"
                    onClick={() => setEditFields(prev => ({ ...prev, difficulty: "EASY" }))}
                    className={`px-4 py-2 rounded-md border-2 font-bold text-sm transition-all duration-200 ${
                      editFields.difficulty === "EASY" 
                        ? "bg-green-500 border-green-500 text-white" 
                        : "bg-transparent border-green-600 text-green-500 hover:border-green-500"
                    }`}
                  >
                    EASY
                  </button>
                  <button
                    type="button"
                    onClick={() => setEditFields(prev => ({ ...prev, difficulty: "MEDIUM" }))}
                    className={`px-4 py-2 rounded-md border-2 font-bold text-sm transition-all duration-200 ${
                      editFields.difficulty === "MEDIUM" 
                        ? "bg-yellow-500 border-yellow-500 text-white" 
                        : "bg-transparent border-yellow-600 text-yellow-500 hover:border-yellow-500"
                    }`}
                  >
                    MEDIUM
                  </button>
                  <button
                    type="button"
                    onClick={() => setEditFields(prev => ({ ...prev, difficulty: "HARD" }))}
                    className={`px-4 py-2 rounded-md border-2 font-bold text-sm transition-all duration-200 ${
                      editFields.difficulty === "HARD" 
                        ? "bg-orange-500 border-orange-500 text-white" 
                        : "bg-transparent border-orange-600 text-orange-500 hover:border-orange-500"
                    }`}
                  >
                    HARD
                  </button>
                  <button
                    type="button"
                    onClick={() => setEditFields(prev => ({ ...prev, difficulty: "EXTREME" }))}
                    className={`px-4 py-2 rounded-md border-2 font-bold text-sm transition-all duration-200 ${
                      editFields.difficulty === "EXTREME" 
                        ? "bg-red-500 border-red-500 text-white" 
                        : "bg-transparent border-red-600 text-red-500 hover:border-red-500"
                    }`}
                  >
                    EXTREME
                  </button>
                </div>
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
          ) : (            <div className="space-y-2">
              <p><strong>Title:</strong> {beatmap.title}</p>
              <p><strong>Artist:</strong> {beatmap.artist}</p>              <p><strong>Difficulty:</strong> {['EASY', 'MEDIUM', 'HARD', 'EXTREME'][beatmap.difficulty] || 'EASY'}</p>
              <p><strong>Song Map:</strong> {beatmap.song_map}</p>
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
function Home({ beatmaps, setBeatmaps, logs, setLogs, onDelete }) {  const fileInputRef = useRef();
  const midiInputRef = useRef();
  const logsRef = useRef(); // Add ref for logs container
  const [selectedFile, setSelectedFile] = useState(null);
  const [selectedMidiFile, setSelectedMidiFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const navigate = useNavigate();
  
  // Add new state for the metadata modal
  const [isMetadataModalOpen, setIsMetadataModalOpen] = useState(false);  const [currentBeatmap, setCurrentBeatmap] = useState(null);  // Add state to store extracted metadata
  const [extractedMetadata, setExtractedMetadata] = useState(null);
  const [downloadingMap, setDownloadingMap] = useState({});
  const [showScrollToBottom, setShowScrollToBottom] = useState(false);  // Auto-scroll logs to bottom whenever logs change
  useEffect(() => {
    if (logsRef.current && logs.length > 0) {
      const logsContainer = logsRef.current;
      
      // Use requestAnimationFrame to ensure DOM has updated
      requestAnimationFrame(() => {
        // Always scroll to bottom on the first few logs or if content is small
        if (logs.length <= 3 || logsContainer.scrollHeight <= logsContainer.clientHeight) {
          logsContainer.scrollTop = logsContainer.scrollHeight;
          setShowScrollToBottom(false);
          return;
        }
        
        // Check if user is near the bottom (within 30px) before auto-scrolling
        const distanceFromBottom = logsContainer.scrollHeight - logsContainer.scrollTop - logsContainer.clientHeight;
        const isNearBottom = distanceFromBottom < 30;
        
        if (isNearBottom) {
          // Force scroll to bottom
          logsContainer.scrollTop = logsContainer.scrollHeight;
          setShowScrollToBottom(false);
        } else {
          setShowScrollToBottom(true);
        }
      });
    }
  }, [logs]);  // Handle scroll events to show/hide scroll to bottom button
  const handleLogsScroll = () => {
    if (logsRef.current) {
      const logsContainer = logsRef.current;
      const distanceFromBottom = logsContainer.scrollHeight - logsContainer.scrollTop - logsContainer.clientHeight;
      const isNearBottom = distanceFromBottom < 30;
      setShowScrollToBottom(!isNearBottom);
    }
  };

  // Scroll to bottom manually
  const scrollToBottom = () => {
    if (logsRef.current) {
      logsRef.current.scrollTo({
        top: logsRef.current.scrollHeight,
        behavior: 'smooth'
      });
      setShowScrollToBottom(false);
    }
  };

  const handleFileChange = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    
    setSelectedFile(file);
    setLogs((prev) => [...prev, `Selected file: ${file.name}`]);
    
    // Extract metadata from the file when selected
    setLogs((prev) => [...prev, "Extracting metadata from file..."]);
    try {
      const metadata = await extractAudioMetadata(file);
      
      // Log the extraction results
      const foundItems = [];      if (metadata.title) foundItems.push("Title");
      if (metadata.artist) foundItems.push("Artist");
      if (metadata.artwork) foundItems.push("Artwork");
      
      setLogs((prev) => [
        ...prev, 
        `Metadata extraction ${foundItems.length > 0 ? "successful" : "found nothing"}!`,
        foundItems.length > 0 ? `Found: ${foundItems.join(", ")}` : "",        `Title: ${metadata.title || "(not found)"}`,
        `Artist: ${metadata.artist || "(not found)"}`,
        `Artwork: ${metadata.artwork ? "Found" : "Not found"}`
      ]);
      
      setExtractedMetadata(metadata);
    } catch (error) {
      console.error("Error extracting metadata:", error);
      setLogs((prev) => [...prev, `Error extracting metadata: ${error.message}`]);
        // Still create a basic metadata object with filename as title
      const fallbackMetadata = {
        title: file.name.replace(/\.[^/.]+$/, ""), // Remove extension
        artist: "",
        artwork: null
      };
      
      setExtractedMetadata(fallbackMetadata);
      setLogs((prev) => [...prev, "Using filename as fallback title"]);
    }
  };

  // --- Update the handleUpload function to use extracted metadata ---
  const handleUpload = async (e) => {
    e.preventDefault();
    if (selectedFile) {
      setUploading(true);
      setLogs((prev) => [...prev, `Uploading: ${selectedFile.name}`]);      const formData = new FormData();
      formData.append("file", selectedFile);
      
      // Add MIDI file if selected
      if (selectedMidiFile) {
        formData.append("midi_file", selectedMidiFile);
        setLogs((prev) => [...prev, `Including MIDI file: ${selectedMidiFile.name}`]);
      }
      
      // Add metadata to form if available
      if (extractedMetadata) {
        if (extractedMetadata.artwork) {
          // Convert data URL to Blob for uploading
          try {
            const response = await fetch(extractedMetadata.artwork);
            const blob = await response.blob();
            formData.append("artwork", blob, "artwork.jpg");
          } catch (error) {
            console.error("Error processing artwork:", error);
          }
        }
          // Add text metadata
        formData.append("title", extractedMetadata.title || "");
        formData.append("artist", extractedMetadata.artist || "");
      }
      
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
          
          if (data.status === "success") {            // Use extracted metadata if available, otherwise use server response or fallbacks
            const newBeatmap = {
              id: data.id,
              title: extractedMetadata?.title || data.title || selectedFile.name.replace(/\.(mp3|flac|wav|ogg)$/i, ''),
              artist: extractedMetadata?.artist || data.artist || "Unknown Artist",
              difficulty: data.difficulty || "EASY",
              song_map: data.song_map || "VULCAN",
              artwork: extractedMetadata?.artwork || data.artwork || null,
              createdAt: new Date().toISOString()
            };
            
            // Add to beatmaps state
            setBeatmaps(prev => [...prev, newBeatmap]);
            setLogs((prev) => [...prev, `Beatmap created: ${newBeatmap.title}`, "Done!"]);
            
            // Open metadata modal with the new beatmap
            setCurrentBeatmap(newBeatmap);
            setIsMetadataModalOpen(true);
          } else {
            setLogs((prev) => [...prev, `Server responded with error: ${data.error || 'Unknown error'}`, "Done!"]);
          }
        } else {
          // Handle binary response (ZIP file download)
          const blob = await response.blob();
          const filename = `${selectedFile.name.replace(/\.(mp3|flac|wav|ogg)$/i, '')}_beatmap.zip`;
          saveAs(blob, filename);
          
          setLogs((prev) => [...prev, `Downloaded beatmap package: ${filename}`, "Done!"]);
        }
      } catch (err) {
        setLogs((prev) => [...prev, `Upload failed: ${err.message}`, "Done!"]);      } finally {
        setUploading(false);
        setSelectedFile(null);
        setSelectedMidiFile(null);
        setExtractedMetadata(null);
        if (fileInputRef.current) {
          fileInputRef.current.value = "";
        }
        if (midiInputRef.current) {
          midiInputRef.current.value = "";
        }
      }
    }
  };

  const handleMidiFileChange = (e) => {
    const file = e.target.files[0];
    if (!file) return;
    
    setSelectedMidiFile(file);
    setLogs((prev) => [...prev, `Selected MIDI file: ${file.name}`]);
  };

  // Add handler for metadata updates
  const handleMetadataUpdate = (updatedBeatmap) => {
    setBeatmaps(prevBeatmaps => 
      prevBeatmaps.map(beatmap => 
        beatmap.id === updatedBeatmap.id ? updatedBeatmap : beatmap
      )
    );
    setLogs(prev => [...prev, `Metadata updated for: ${updatedBeatmap.title}`]);
  };

  const handleClearBeatmaps = async () => {
    if (!window.confirm("Are you sure you want to delete ALL beatmaps? This will remove all files from the output folder.")) {
      return;
    }
    
    setLogs(prev => [...prev, "Clearing all beatmaps..."]);
    
    try {
      // Call the backend endpoint to delete all beatmaps and files
      const response = await fetch("/api/clear_all_beatmaps", {
        method: "DELETE",
      });
      
      if (!response.ok) {
        const errorText = await response.text();
        console.error("Clear all beatmaps error:", errorText);
        throw new Error(`Failed to clear beatmaps: ${response.status}`);
      }
      
      const result = await response.json();
      
      // Update UI state
      setBeatmaps([]);
      setLogs(prev => [...prev, 
        `All beatmaps cleared successfully. ${result.itemsDeleted || 'All'} items deleted.`,
        "Output folder has been cleaned."
      ]);
      
    } catch (error) {
      console.error("Error clearing beatmaps:", error);
      setLogs(prev => [...prev, `Error clearing beatmaps: ${error.message}`]);
    }
  };

  return (    <div className="bm-background min-h-screen pb-12">
      <div className="bm-container pt-32" style={{ maxWidth: "100%", padding: "0 20px", paddingTop: "8rem" }}>
        {/* Logo with more space */}
        <div className="flex justify-center mb-8">
          <img src={logo} alt="BeatMapper Logo" className="bm-logo" style={{ maxWidth: "200px" }} />
        </div>
        
        {/* Upload section */}        <div className="bm-card w-full max-w-4xl mx-auto">
          <h2 className="text-xl font-bold mb-6">Upload New Song</h2>
          
          <form onSubmit={handleUpload} style={{ width: "100%" }}>
            {/* Audio File Section */}
            <div className="mb-6">
              <label className="block text-sm font-medium text-white mb-3">
                Audio File (MP3, OGG, FLAC, WAV)
              </label>              <input
                ref={fileInputRef}
                type="file"
                accept=".mp3,.flac,.wav,.ogg"
                onChange={handleFileChange}
                className="bm-file-input"
              />              <button
                type="button"
                onClick={() => fileInputRef.current.click()}
                className="bm-browse-btn"
              >
                <FaFolder style={{ marginRight: 8 }} /> 
                <span style={{ fontWeight: selectedFile ? 'normal' : 'bold' }}>
                  {selectedFile ? selectedFile.name : "Browse"}
                </span>
              </button>
            </div>
            
            {/* MIDI File Section - Optional */}
            <div className="mb-6">
              <label className="block text-sm font-medium text-white mb-2">
                MIDI File (Optional)
              </label>
              <p className="text-xs text-gray-400 mb-3">
                Upload a MIDI file to improve beat detection accuracy
              </p>
              
              <input
                ref={midiInputRef}
                type="file"
                accept=".mid,.midi"
                onChange={handleMidiFileChange}
                className="bm-file-input"
              />
              
              <button
                type="button"
                onClick={() => midiInputRef.current.click()}
                className="bm-browse-btn"
                style={{ 
                  background: selectedMidiFile ? "#4A5568" : "#B8860B",
                  opacity: selectedMidiFile ? 0.9 : 1
                }}
              >
                <FaMusic style={{ marginRight: 8 }} /> 
                <span style={{ fontWeight: selectedMidiFile ? 'normal' : 'bold' }}>
                  {selectedMidiFile ? selectedMidiFile.name : "Browse MIDI (Optional)"}
                </span>
              </button>
              
              {selectedMidiFile && (
                <button
                  type="button"
                  onClick={() => {
                    setSelectedMidiFile(null);
                    if (midiInputRef.current) {
                      midiInputRef.current.value = "";
                    }
                    setLogs((prev) => [...prev, "MIDI file removed"]);
                  }}
                  className="text-red-400 hover:text-red-300 text-sm mt-2 block"
                >
                  Remove MIDI file
                </button>
              )}
            </div>

            {/* Upload Button */}
            <button
              type="submit"
              className="bm-upload-btn"
              disabled={!selectedFile || uploading}
            >
              {uploading ? (
                <div className="flex items-center justify-center">
                  <div className="animate-spin mr-2 h-5 w-5 border-2 border-gray-800 border-t-transparent rounded-full"></div>
                  <span>Uploading...</span>
                </div>
              ) : (
                <>
                  <FaUpload style={{ marginRight: 8 }} /> Upload
                </>
              )}
            </button>
          </form>
        </div>        {/* Logs section - doubled width */}
        <div className="bm-card logs-card mt-6 mx-auto" style={{ position: 'relative' }}>
          <div className="bm-logs-title">Logs</div>
          <pre 
            className="bm-log-output w-full" 
            ref={logsRef}
            onScroll={handleLogsScroll}
          >
            {logs.join("\n")}
          </pre>          {showScrollToBottom && (
            <button
              onClick={scrollToBottom}
              className="logs-scroll-to-bottom"
              title="Scroll to bottom"
            >
              ↓
            </button>
          )}
        </div>

        {/* Your Beatmaps Section - doubled width */}
        <div className="bm-card beatmaps-card mt-6 mx-auto">
          <div style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            width: "100%",
            textAlign: "left"
          }}>
            <h2 className="text-xl font-bold" style={{ textAlign: "left" }}>Your Beatmaps</h2>
            
            <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
              {beatmaps.length > 0 && (
                <>
                  <div style={{ 
                    backgroundColor: "#374151", 
                    padding: "8px 12px", 
                    borderRadius: "4px",
                    fontSize: "0.875rem", 
                    color: "#fbbf24", 
                    maxWidth: "300px" 
                  }}>
                    <strong>NOTE:</strong> It is recommended to 'Clear All' after importing to Drums Rock
                  </div>
                  <button
                    onClick={handleClearBeatmaps}
                    className="bg-red-600 hover:bg-red-700 text-white py-1 px-3 rounded whitespace-nowrap"
                  >
                    <FaTrash className="inline mr-1" /> Clear All
                  </button>
                </>
              )}
            </div>
          </div>

          {beatmaps.length === 0 ? (
            <p style={{ textAlign: "center", padding: "1.5rem 0", color: "#9ca3af" }}>
              No beatmaps yet. Upload an audio file to create one.
            </p>
          ) : (
            <div style={{ width: "100%" }}>
              {beatmaps.map((beatmap, index) => (
                <div key={beatmap.id}>
                  {index > 0 && <hr style={{ borderColor: "#374151", margin: "0" }} />}                  <div style={{
                    display: "flex",
                    alignItems: "center",
                    padding: "1rem",
                    backgroundColor: "#1f2937",
                    borderLeft: `4px solid ${(() => {
                      const difficultyColors = {
                        0: "#22c55e", // Green for EASY
                        1: "#eab308", // Yellow for MEDIUM  
                        2: "#f97316", // Orange for HARD
                        3: "#ef4444"  // Red for EXTREME
                      };
                      return difficultyColors[beatmap.difficulty] || "#6b7280";
                    })()}`,
                  }}>
                    {/* Album Art */}
                    <div style={{
                      height: "60px",
                      width: "60px",
                      backgroundColor: "#374151",
                      marginRight: "1rem",
                      flexShrink: 0,
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                    }}>
                      {beatmap.artwork ? (
                        <img
                          src={beatmap.artwork}
                          alt="Album art"
                          style={{ height: "100%", width: "100%", objectFit: "cover" }}
                          onError={(e) => { e.target.src = "https://via.placeholder.com/60"; }}
                        />
                      ) : (
                        "Album art"
                      )}
                    </div>
                      {/* Song Info */}
                    <div style={{ flexGrow: 1, textAlign: "left" }}>
                      <div style={{ 
                        display: "flex", 
                        alignItems: "center", 
                        gap: "0.75rem",
                        marginBottom: "0.25rem"
                      }}>
                        <div style={{ fontWeight: "500" }}>{beatmap.title}</div>
                        <div style={{
                          padding: "4px 8px",
                          borderRadius: "4px",
                          fontSize: "0.75rem",
                          fontWeight: "bold",
                          backgroundColor: (() => {
                            const difficultyColors = {
                              0: "#22c55e", // Green for EASY
                              1: "#eab308", // Yellow for MEDIUM  
                              2: "#f97316", // Orange for HARD
                              3: "#ef4444"  // Red for EXTREME
                            };
                            return difficultyColors[beatmap.difficulty] || "#6b7280";
                          })(),
                          color: "white",                        }}>
                          {(() => {
                            const difficultyNames = ["EASY", "MEDIUM", "HARD", "EXTREME"];
                            return difficultyNames[beatmap.difficulty] || "UNKNOWN";
                          })()}
                        </div>
                        <div style={{
                          padding: "4px 8px",
                          borderRadius: "4px",
                          fontSize: "0.75rem",
                          fontWeight: "bold",
                          backgroundColor: "#4f46e5", // Purple for stage
                          color: "white",
                        }}>
                          {(() => {
                            const stageNames = ["VULCAN", "DESERT", "STORM"];
                            const songMapIndex = parseInt(beatmap.song_map) || 0;
                            return stageNames[songMapIndex] || "UNKNOWN";
                          })()}
                        </div>
                      </div>
                      <div style={{ color: "#9ca3af" }}>{beatmap.artist}</div>
                    </div>
                    
                    {/* Buttons - REMOVE THE DELETE BUTTON */}
                    <div style={{ display: "flex", gap: "0.75rem" }}>
                      <button
                        onClick={() => {
                          setCurrentBeatmap(beatmap);
                          setIsMetadataModalOpen(true);
                        }}
                        className="bg-blue-600 hover:bg-blue-700 text-white py-1 px-3 rounded text-sm flex items-center"
                      >
                        <FaPencilAlt className="mr-1" /> Edit
                      </button>
                      <button 
                        onClick={async () => {
                          try {
                            setDownloadingMap(prev => ({ ...prev, [beatmap.id]: true }));
                            setLogs(prev => [...prev, `Downloading beatmap: ${beatmap.title}...`]);
                            
                            const response = await fetch(`/api/download_beatmap/${beatmap.id}`);
                            
                            if (!response.ok) {
                              // Try to get error details from response
                              let errorMessage = `Download failed with status: ${response.status}`;
                              try {
                                const contentType = response.headers.get('content-type');
                                if (contentType && contentType.includes('application/json')) {
                                  const errorData = await response.json();
                                  errorMessage = errorData.error || errorMessage;
                                }
                              } catch {}
                              
                              throw new Error(errorMessage);
                            }
                            
                            // Handle successful ZIP download
                            const blob = await response.blob();
                            saveAs(blob, `${beatmap.title || 'beatmap'}.zip`);
                            
                            setLogs(prev => [...prev, `Beatmap downloaded successfully: ${beatmap.title}`]);
                          } catch (error) {
                            console.error("Error downloading beatmap:", error);
                            setLogs(prev => [...prev, `Failed to download beatmap: ${error.message}`]);
                          } finally {
                            setDownloadingMap(prev => ({ ...prev, [beatmap.id]: false }));
                          }
                        }}
                        className="bg-green-600 hover:bg-green-700 text-white py-1 px-3 rounded text-sm flex items-center"
                        disabled={downloadingMap[beatmap.id]}
                      >
                        {downloadingMap[beatmap.id] ? (
                          <>
                            <div className="animate-spin mr-1 h-4 w-4 border-2 border-white border-t-transparent rounded-full"></div>
                            <span>Downloading...</span>
                          </>
                        ) : (
                          <>
                            <FaDownload className="mr-1" /> Download
                          </>
                        )}
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Metadata Edit Modal */}
        <MetadataEditModal
          isOpen={isMetadataModalOpen}
          onClose={() => setIsMetadataModalOpen(false)}
          beatmap={currentBeatmap}
          onSave={handleMetadataUpdate}
        />
      </div>
    </div>
  );
}

// --- Main App with Routing ---
export default function App() {
  const [beatmaps, setBeatmaps] = useState(() => {
    // Load beatmaps from localStorage on app start
    const savedBeatmaps = localStorage.getItem("beatmaps");
    return savedBeatmaps ? JSON.parse(savedBeatmaps) : [];
  });
  
  const [logs, setLogs] = useState(() => {
    // We'll initialize with just one welcome message instead of loading from localStorage
    return ["BeatMapper initialized. Ready to process audio files."];
  });

  // Run once when the app first loads
  useEffect(() => {
    // Clear any old logs in localStorage
    localStorage.removeItem("logs");
    
    // Log the initialization message
    const timestamp = new Date().toLocaleTimeString();
    setLogs([`[${timestamp}] BeatMapper started. Session logs will be cleared on restart.`]);
    
    // Optional: Log app version or other initialization info
    console.log("BeatMapper initialized - logs cleared");
  }, []); // Empty dependency array means this runs once on mount

  // Sync beatmaps with localStorage
  useEffect(() => {
    localStorage.setItem("beatmaps", JSON.stringify(beatmaps));
  }, [beatmaps]);

  // Sync logs with localStorage - but only during the session
  useEffect(() => {
    localStorage.setItem("logs", JSON.stringify(logs));
  }, [logs]);

  const handleDelete = (id) => {
    setBeatmaps((prev) => prev.filter((b) => b.id !== id));
    setLogs((prev) => [...prev, `Deleted beatmap with id: ${id}`]);
  };

  return (
    <Router>
      <Routes>
        <Route path="/" element={
          <Home 
            beatmaps={beatmaps} 
            setBeatmaps={setBeatmaps} 
            logs={logs} 
            setLogs={setLogs} 
            onDelete={handleDelete} 
          />
        } />
        <Route path="/beatmap/:id" element={
          <BeatmapDetails 
            beatmaps={beatmaps} 
            setBeatmaps={setBeatmaps} 
            onDelete={handleDelete} 
          />
        } />
      </Routes>
    </Router>
  );
}
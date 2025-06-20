import React from "react";

export default function BeatmapDetails({ beatmap }) {
  // beatmap: { title, artist, bpm, mapper, has_artwork, name }
  return (
    <div className="bm-background">
      <div className="bm-container">
        <div className="bm-card">
          <div className="card-header">
            <h2>Beatmap Details</h2>
          </div>
          <div className="card-body">
            <div style={{ display: "flex", alignItems: "flex-start", marginBottom: 32 }}>
              <div
                style={{
                  width: 200,
                  height: 200,
                  background: "#e9ecef",
                  borderRadius: 5,
                  marginRight: 32,
                  overflow: "hidden",
                  boxShadow: "0 3px 6px rgba(0,0,0,0.1)",
                  border: "1px solid #ddd",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                }}
              >
                {beatmap.has_artwork ? (
                  <img
                    src={`/artwork/${beatmap.name}`}
                    alt="Album Art"
                    style={{ width: "100%", height: "100%", objectFit: "cover" }}
                  />
                ) : (
                  <span>No artwork</span>
                )}
              </div>
              <div style={{ flex: 1 }}>
                <h2>{beatmap.title || "Unknown Title"}</h2>
                <div style={{ color: "#6c757d", fontSize: "1.25rem", marginBottom: 16 }}>
                  {beatmap.artist || "Unknown Artist"}
                </div>                <ul style={{ listStyle: "none", padding: 0 }}>
                  {beatmap.bpm && (
                    <li>
                      <span style={{ fontWeight: "bold", display: "inline-block", width: 80 }}>BPM:</span>
                      {beatmap.bpm}
                    </li>
                  )}
                  <li>
                    <span style={{ fontWeight: "bold", display: "inline-block", width: 80 }}>Mapper:</span>
                    {beatmap.mapper || "Unknown"}
                  </li>
                </ul>
              </div>
            </div>
            {/* Tabs and edit/analyze sections can be added here */}
          </div>
        </div>
      </div>
    </div>
  );
}
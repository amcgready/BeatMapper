import React, { useState } from "react";
import axios from "axios";
import { FaFileCsv, FaUpload, FaSpinner } from "react-icons/fa";

function ManualCorrection({ onSuccess }) {
  const [file, setFile] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!file) {
      setError("Please select a CSV file.");
      return;
    }
    setLoading(true);
    setError("");
    const formData = new FormData();
    formData.append("file", file);
    try {
      await axios.post("/api/upload_notes", formData, {
        headers: { "Content-Type": "multipart/form-data" }
      });
      setLoading(false);
      onSuccess && onSuccess();
    } catch (err) {
      setError("Upload failed.");
      setLoading(false);
    }
  };

  return (
    <form
      onSubmit={handleSubmit}
      className="bg-gray-800 rounded-xl p-8 shadow-lg max-w-xl mx-auto mt-8"
    >
      <h2 className="text-2xl font-bold mb-6 flex items-center">
        <FaFileCsv className="mr-2 text-green-400" /> Manual Correction
      </h2>
      <div className="mb-4">
        <label className="block font-medium mb-2">
          Upload corrected <span className="font-mono">notes.csv</span>:
          <input
            type="file"
            accept=".csv"
            onChange={e => setFile(e.target.files[0])}
            required
            className="block mt-2 w-full text-white bg-gray-700 rounded p-2"
          />
        </label>
      </div>
      <button
        type="submit"
        disabled={loading}
        className="w-full py-3 mt-2 bg-blue-500 hover:bg-blue-700 text-white font-semibold rounded transition flex items-center justify-center"
      >
        {loading ? (
          <>
            <FaSpinner className="animate-spin mr-2" /> Uploading...
          </>
        ) : (
          <>
            <FaUpload className="mr-2" /> Upload
          </>
        )}
      </button>
      {error && <div className="text-red-400 mt-4">{error}</div>}
    </form>
  );
}

export default ManualCorrection;
import React from "react";
import { FaMusic, FaRegFileAudio } from "react-icons/fa";

function SongPreview() {
  return (
    <div className="mt-8 bg-gray-800 rounded-xl p-8 shadow-lg max-w-xl mx-auto">
      <h2 className="text-2xl font-bold mb-6 flex items-center">
        <FaMusic className="mr-2 text-blue-400" /> Song Preview
      </h2>
      <div className="mb-6">
        <p className="font-semibold flex items-center mb-2">
          <FaMusic className="mr-2 text-green-400" /> Full Song:
        </p>
        <audio
          controls
          src="/api/download/song.ogg"
          className="w-full rounded"
        />
      </div>
      <div>
        <p className="font-semibold flex items-center mb-2">
          <FaRegFileAudio className="mr-2 text-yellow-400" /> Preview Clip:
        </p>
        <audio
          controls
          src="/api/download/preview.ogg"
          className="w-full rounded"
        />
      </div>
    </div>
  );
}

export default SongPreview;
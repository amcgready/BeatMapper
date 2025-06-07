import React from "react";
import { FaFileCsv, FaMusic, FaRegFileAudio, FaInfoCircle, FaImage, FaDownload } from "react-icons/fa";
import { Tooltip } from "react-tooltip";

const files = [
  {
    name: "notes.csv",
    icon: <FaFileCsv className="inline mr-2" />,
    tooltip: "Drum notes for Drums Rock"
  },
  {
    name: "song.ogg",
    icon: <FaMusic className="inline mr-2" />,
    tooltip: "Full song audio (OGG)"
  },
  {
    name: "preview.ogg",
    icon: <FaRegFileAudio className="inline mr-2" />,
    tooltip: "Preview audio clip (OGG)"
  },
  {
    name: "info.csv",
    icon: <FaInfoCircle className="inline mr-2" />,
    tooltip: "Song metadata"
  },
  {
    name: "album.jpg",
    icon: <FaImage className="inline mr-2" />,
    tooltip: "Album artwork"
  }
];

function DownloadLinks() {
  return (
    <div className="mt-8 bg-gray-800 rounded-xl p-8 shadow-lg">
      <h2 className="text-2xl font-bold mb-4">Download Files</h2>
      <ul className="list-none p-0 m-0">
        {files.map(f => (
          <li key={f.name} className="mb-4">
            <a
              href={`/api/download/${f.name}`}
              download
              data-tip={f.tooltip}
              className="inline-flex items-center px-5 py-2 bg-blue-500 hover:bg-blue-700 text-white rounded-md font-medium shadow transition"
            >
              {f.icon}
              {f.name}
              <FaDownload className="ml-2" />
            </a>
            <Tooltip effect="solid" />
          </li>
        ))}
      </ul>
    </div>
  );
}

export default DownloadLinks;
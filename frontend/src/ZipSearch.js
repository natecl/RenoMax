import React, { useState } from "react";

function ZipSearch({ onResults }) {
  const [zip, setZip] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const quickZips = ["94107", "10001", "30309", "78704"];

  const handleSearch = async () => {
    if (!zip || zip.length !== 5) {
      setError("Please enter a valid 5-digit ZIP code.");
      return;
    }

    setError("");
    setLoading(true);

    try {
      const API_URL = "https://YOUR-BACKEND-NAME.onrender.com";

      const res = await fetch(`${API_URL}/housing/${zip}`);

      if (!res.ok) throw new Error("API error");

      const data = await res.json();
      onResults(data); // send data to App.js
    } catch (err) {
      setError("No results found or API error.");
    }

    setLoading(false);
  };

  return (
    <div className="bg-white/80 border border-slate-100 p-6 rounded-2xl shadow-sm backdrop-blur">
      <div className="flex items-start justify-between gap-3 mb-4">
        <div>
          <h1 className="text-xl font-semibold text-slate-900">Search by ZIP</h1>
          <p className="text-sm text-slate-600">
            Pull listings in seconds, then refine with filters.
          </p>
        </div>
        <span className="text-xs font-semibold px-3 py-1 rounded-full bg-green-50 text-green-700">
          Live
        </span>
      </div>

      <div className="flex gap-2 mb-3">
        <input
          type="text"
          maxLength="5"
          value={zip}
          onChange={(e) => setZip(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleSearch()}
          placeholder="Enter ZIP Code"
          className="flex-1 border border-slate-200 px-3 py-2 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
        <button
          onClick={handleSearch}
          disabled={loading}
          className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 disabled:opacity-60 disabled:cursor-not-allowed transition"
        >
          {loading ? "Searching..." : "Search homes"}
        </button>
      </div>

      <div className="flex flex-wrap gap-2 mb-3">
        {quickZips.map((z) => (
          <button
            key={z}
            onClick={() => {
              setZip(z);
              handleSearch();
            }}
            className="px-3 py-1 rounded-full border border-slate-200 text-slate-700 text-sm hover:border-blue-400 hover:text-blue-700 transition"
          >
            {z}
          </button>
        ))}
      </div>

      <p className="text-xs text-slate-500 mb-2">
        Tip: we also pull nearby ZIPs if results are thin.
      </p>

      {loading && <p className="text-center text-slate-600">Loading...</p>}
      {error && <p className="text-red-600 text-center">{error}</p>}
    </div>
  );
}

export default ZipSearch;

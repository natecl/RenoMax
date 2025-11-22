import { useState } from "react";
import ZipSearch from "./ZipSearch";

function App() {
  const [homes, setHomes] = useState([]);

  return (
    <div className="min-h-screen bg-gray-100 p-6">
      <ZipSearch onResults={setHomes} />

      {/* RESULTS */}
      <div className="mt-10 max-w-5xl mx-auto grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
        {homes.map((home) => (
          <div
            key={home.externalId}
            className="bg-white p-4 rounded-xl shadow hover:shadow-lg transition"
          >
            <h2 className="text-xl font-semibold text-gray-800">
              {home.address}
            </h2>

            <p className="text-gray-600">{home.city}, {home.state}</p>

            <p className="mt-2 text-blue-600 font-bold text-lg">
              ${home.price.toLocaleString()}
            </p>

            <p className="text-gray-700 mt-1">
              {home.bedrooms} Beds · {home.bathrooms} Baths · {home.sqft} Sqft
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}

export default App;

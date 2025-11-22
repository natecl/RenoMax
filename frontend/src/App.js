import { useState } from "react";
import ZipSearch from "./ZipSearch";

function App() {
  // IMPORTANT: initialize as empty array, not undefined
  const [homes, setHomes] = useState([]);

  return (
    <div className="min-h-screen bg-gray-100 p-6">
      {/* ZIP Search Component */}
      <ZipSearch onResults={setHomes} />

      {/* Housing Results */}
      {Array.isArray(homes) && homes.length > 0 && (
        <div className="mt-10 max-w-5xl mx-auto grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
          {homes.map((home) => (
            <div
              key={home.externalId || home.address}
              className="bg-white p-4 rounded-xl shadow hover:shadow-lg transition"
            >
              <h2 className="text-xl font-semibold text-gray-800">
                {home.address}
              </h2>

              <p className="text-gray-600">
                {home.city}, {home.state}
              </p>

              <p className="mt-2 text-blue-600 font-bold text-lg">
                ${home.price?.toLocaleString()}
              </p>

              <p className="text-gray-700 mt-1">
                {home.bedrooms} Beds · {home.bathrooms} Baths · {home.sqft} Sqft
              </p>
            </div>
          ))}
        </div>
      )}

      {/* No results message */}
      {Array.isArray(homes) && homes.length === 0 && (
        <p className="text-center text-gray-500 mt-10">
          Enter a ZIP code to begin searching.
        </p>
      )}
    </div>
  );
}

export default App;

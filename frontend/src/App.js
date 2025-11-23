import { useState } from "react";
import ZipSearch from "./ZipSearch";
import FilterBar from "./FilterBar";

function App() {
  const [homes, setHomes] = useState([]);
  const [filteredHomes, setFilteredHomes] = useState([]);
  const [filters, setFilters] = useState({
    beds: "",
    baths: "",
    minPrice: "",
    maxPrice: "",
  });

  const applyFilters = () => {
    let list = [...homes];

    if (filters.beds)
      list = list.filter((h) => h.bedrooms >= Number(filters.beds));

    if (filters.baths)
      list = list.filter((h) => h.bathrooms >= Number(filters.baths));

    if (filters.minPrice)
      list = list.filter((h) => h.price >= Number(filters.minPrice));

    if (filters.maxPrice)
      list = list.filter((h) => h.price <= Number(filters.maxPrice));

    setFilteredHomes(list);
  };

  const priceValues = filteredHomes
    .map((h) => h.price)
    .filter((p) => typeof p === "number");
  const minPrice = priceValues.length ? Math.min(...priceValues) : null;
  const maxPrice = priceValues.length ? Math.max(...priceValues) : null;
  const formatCurrency = (value) =>
    typeof value === "number" ? `$${value.toLocaleString()}` : "—";
  const hasResults = filteredHomes.length > 0;

  return (
    <div className="min-h-screen bg-slate-50">
      <div className="max-w-6xl mx-auto px-6 py-12 space-y-10">
        <header className="space-y-3">
          <span className="inline-flex items-center gap-2 rounded-full bg-blue-50 text-blue-700 px-3 py-1 text-xs font-semibold uppercase tracking-wide">
            RenovMax
          </span>
          <div className="space-y-2">
            <h1 className="text-3xl md:text-4xl font-bold text-slate-900">
              Find the right home and plan your renovation
            </h1>
            <p className="text-slate-600 max-w-3xl">
              Search by ZIP, then refine by beds, baths, and budget. We surface nearby listings so you can spot opportunities quickly.
            </p>
          </div>
        </header>

        <div className="grid lg:grid-cols-3 gap-6 items-start">
          <div className="space-y-6 lg:col-span-1">
            <ZipSearch
              onResults={(data) => {
                setFilters({
                  beds: "",
                  baths: "",
                  minPrice: "",
                  maxPrice: "",
                });
                setHomes(data);
                setFilteredHomes(data);
              }}
            />

            {homes.length > 0 && (
              <FilterBar
                filters={filters}
                setFilters={setFilters}
                applyFilters={applyFilters}
                onClear={() => setFilteredHomes(homes)}
              />
            )}
          </div>

          <div className="space-y-4 lg:col-span-2">
            {homes.length === 0 && (
              <div className="bg-white/70 border border-slate-100 rounded-2xl p-8 shadow-sm">
                <h3 className="text-xl font-semibold text-slate-900">
                  Start with a ZIP search
                </h3>
                <p className="text-slate-600 mt-2">
                  We’ll pull listings nearby and show quick stats. Then, dial it in with filters to find your best options.
                </p>
              </div>
            )}

            {homes.length > 0 && (
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div className="space-y-1">
                  <p className="text-sm uppercase tracking-wide text-slate-500 font-semibold">
                    Current Results
                  </p>
                  <h2 className="text-2xl font-bold text-slate-900">
                    {filteredHomes.length} home{filteredHomes.length === 1 ? "" : "s"} in view
                  </h2>
                </div>
                {hasResults && (
                  <div className="flex items-center gap-4 text-sm text-slate-600">
                    <div>
                      <p className="text-xs uppercase tracking-wide text-slate-500 font-semibold">Price range</p>
                      <p className="font-semibold text-slate-900">
                        {formatCurrency(minPrice)} – {formatCurrency(maxPrice)}
                      </p>
                    </div>
                    <div className="h-10 w-px bg-slate-200" />
                    <div>
                      <p className="text-xs uppercase tracking-wide text-slate-500 font-semibold">Total fetched</p>
                      <p className="font-semibold text-slate-900">{homes.length}</p>
                    </div>
                  </div>
                )}
              </div>
            )}

            {hasResults && (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
                {filteredHomes.map((home) => (
                  <div
                    key={home.externalId}
                    className="group bg-white/90 border border-slate-100 rounded-2xl shadow-sm hover:shadow-xl transition hover:-translate-y-1"
                  >
                    <div className="h-1 rounded-t-2xl bg-gradient-to-r from-blue-600 via-indigo-500 to-purple-500" />
                    <div className="p-5 space-y-3">
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <p className="text-sm text-slate-500 uppercase tracking-wide font-semibold">
                            {home.city}, {home.state}
                          </p>
                          <h2 className="text-xl font-semibold text-slate-900">
                            {home.address}
                          </h2>
                        </div>
                        <span className="text-xs font-semibold px-3 py-1 rounded-full bg-blue-50 text-blue-700">
                          For Sale
                        </span>
                      </div>
                      <p className="text-2xl font-bold text-slate-900">
                        ${home.price.toLocaleString()}
                      </p>
                      <div className="flex items-center gap-4 text-slate-600 text-sm">
                        <span className="inline-flex items-center gap-1">
                          🛏️ {home.bedrooms} Beds
                        </span>
                        <span className="inline-flex items-center gap-1">
                          🛁 {home.bathrooms} Baths
                        </span>
                        <span className="inline-flex items-center gap-1">
                          📐 {home.sqft} Sqft
                        </span>
                      </div>
                      <div className="flex items-center justify-between text-sm text-slate-500 pt-2">
                        <span>ZIP {home.zipcode || "—"}</span>
                        <span className="font-medium text-blue-700 group-hover:text-blue-800">
                          View details
                        </span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}

            {homes.length > 0 && filteredHomes.length === 0 && (
              <div className="text-center text-slate-600 bg-white/80 border border-slate-100 rounded-2xl py-10 shadow-sm">
                <p className="text-lg font-semibold text-slate-900">
                  No homes match these filters.
                </p>
                <p className="mt-2">
                  Try widening the price range or lowering the bed/bath minimums.
                </p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;

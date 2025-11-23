import { useState } from "react";
import ZipSearch from "./ZipSearch";
import FilterBar from "./FilterBar";

function App() {
  const [homes, setHomes] = useState([]);
  const [filteredHomes, setFilteredHomes] = useState([]);
  const [anomaliesOnly, setAnomaliesOnly] = useState(false);
  const [filters, setFilters] = useState({
    beds: "",
    baths: "",
    minPrice: "",
    maxPrice: "",
  });

  const sortHomes = (list) =>
    [...list].sort((a, b) => {
      if (a.anomaly === b.anomaly) return (b.price || 0) - (a.price || 0);
      return b.anomaly ? 1 : -1;
    });

  const computeFiltered = (base, currentFilters, anomalyOnlyFlag) => {
    let list = [...base];

    if (currentFilters.beds)
      list = list.filter((h) => h.bedrooms >= Number(currentFilters.beds));

    if (currentFilters.baths)
      list = list.filter((h) => h.bathrooms >= Number(currentFilters.baths));

    if (currentFilters.minPrice)
      list = list.filter((h) => h.price >= Number(currentFilters.minPrice));

    if (currentFilters.maxPrice)
      list = list.filter((h) => h.price <= Number(currentFilters.maxPrice));

    if (anomalyOnlyFlag) list = list.filter((h) => h.anomaly);

    return sortHomes(list);
  };

  const applyFilters = () => {
    setFilteredHomes(computeFiltered(homes, filters, anomaliesOnly));
  };

  const priceValues = filteredHomes
    .map((h) => h.price)
    .filter((p) => typeof p === "number");
  const minPrice = priceValues.length ? Math.min(...priceValues) : null;
  const maxPrice = priceValues.length ? Math.max(...priceValues) : null;
  const avgPrice = priceValues.length
    ? Math.round(priceValues.reduce((a, b) => a + b, 0) / priceValues.length)
    : null;
  const sqftValues = filteredHomes
    .map((h) => h.sqft)
    .filter((s) => typeof s === "number");
  const avgSqft = sqftValues.length
    ? Math.round(sqftValues.reduce((a, b) => a + b, 0) / sqftValues.length)
    : null;
  const formatCurrency = (value) =>
    typeof value === "number" ? `$${value.toLocaleString()}` : "—";
  const hasResults = filteredHomes.length > 0;

  return (
    <div className="min-h-screen bg-slate-50 relative overflow-hidden">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_20%_20%,rgba(79,70,229,0.10),transparent_25%),radial-gradient(circle_at_80%_0%,rgba(59,130,246,0.12),transparent_22%)]" />
      <div className="pointer-events-none absolute bottom-6 right-6 w-64 h-48 md:w-80 md:h-60 opacity-70">
        <svg viewBox="0 0 320 240" fill="none" xmlns="http://www.w3.org/2000/svg">
          <defs>
            <pattern id="grid" x="0" y="0" width="20" height="20" patternUnits="userSpaceOnUse">
              <path d="M20 0H0V20" stroke="#5CA4FF" strokeWidth="0.5" />
            </pattern>
          </defs>
          <rect width="320" height="240" fill="url(#grid)" />
          <rect x="0.5" y="0.5" width="319" height="239" stroke="#4F90F8" strokeWidth="1" />
          <path
            d="M80 180V120L160 70L240 120V180H80Z"
            stroke="#8BC8FF"
            strokeWidth="4"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
          <path d="M115 180V140H145V180" stroke="#8BC8FF" strokeWidth="3" />
          <path d="M175 180V150H210V180" stroke="#8BC8FF" strokeWidth="3" />
          <path d="M160 70V110" stroke="#8BC8FF" strokeWidth="3" />
          <path d="M80 147H240" stroke="#4F90F8" strokeWidth="2" strokeDasharray="8 6" />
          <circle cx="100" cy="200" r="6" fill="#2563EB" opacity="0.7" />
          <circle cx="220" cy="200" r="6" fill="#2563EB" opacity="0.7" />
          <path d="M100 200H220" stroke="#2563EB" strokeWidth="2" strokeDasharray="4 5" />
        </svg>
      </div>
      <div className="relative z-10 max-w-6xl mx-auto px-6 py-10 space-y-10">
        <header className="flex items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="h-11 w-11 rounded-2xl bg-gradient-to-br from-blue-500 via-indigo-500 to-purple-500 flex items-center justify-center text-white font-bold shadow-lg">
              R
            </div>
            <div>
              <p className="text-sm uppercase tracking-wide text-slate-500 font-semibold">
                Renomax
              </p>
              <h1 className="text-2xl md:text-3xl font-bold text-slate-900">
                Find the right home. Plan the smart renovation.
              </h1>
            </div>
          </div>
          <button
            onClick={() => {
              const next = !anomaliesOnly;
              setAnomaliesOnly(next);
              setFilteredHomes(computeFiltered(homes, filters, next));
            }}
            className={`hidden sm:inline-flex items-center gap-2 px-4 py-2 rounded-full text-sm font-semibold shadow-lg shadow-slate-900/10 hover:-translate-y-0.5 transition ${
              anomaliesOnly
                ? "bg-gradient-to-r from-blue-500 via-indigo-500 to-purple-500 text-white"
                : "bg-slate-900 text-white"
            }`}
          >
            {anomaliesOnly ? "Show all homes" : "Show anomalies only"}
          </button>
        </header>

        <div className="grid lg:grid-cols-3 gap-6 items-start">
          <div className="space-y-4 lg:col-span-1">
            <ZipSearch
              onResults={(data) => {
                const ordered = sortHomes(data);
                setFilters({
                  beds: "",
                  baths: "",
                  minPrice: "",
                  maxPrice: "",
                });
                setAnomaliesOnly(false);
                setHomes(ordered);
                setFilteredHomes(computeFiltered(ordered, {
                  beds: "",
                  baths: "",
                  minPrice: "",
                  maxPrice: "",
                }, false));
              }}
            />

            {homes.length > 0 && (
              <FilterBar
                filters={filters}
                setFilters={setFilters}
                applyFilters={applyFilters}
                onClear={() =>
                  setFilteredHomes(
                    computeFiltered(
                      homes,
                      { beds: "", baths: "", minPrice: "", maxPrice: "" },
                      anomaliesOnly
                    )
                  )
                }
              />
            )}

            <div className="bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 text-white rounded-2xl p-5 shadow-lg">
              <p className="text-sm text-slate-200">Renovation potential</p>
              <h3 className="text-lg font-semibold mt-1">Spot undervalued homes</h3>
              <p className="text-slate-300 text-sm mt-2">
                Compare price per square foot and bedroom counts to find the best candidates for upgrades.
              </p>
            </div>
          </div>

          <div className="space-y-6 lg:col-span-2">
            {homes.length === 0 && (
              <div className="bg-white/70 border border-slate-100 rounded-2xl p-8 shadow-lg backdrop-blur">
                <h3 className="text-xl font-semibold text-slate-900">
                  Start with a ZIP search
                </h3>
                <p className="text-slate-600 mt-2">
                  We’ll pull listings nearby and show quick stats. Then, dial it in with filters to find your best options.
                </p>
              </div>
            )}

            {hasResults && (
              <>
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div className="space-y-1">
                    <p className="text-sm uppercase tracking-wide text-slate-500 font-semibold">
                      Current Results
                    </p>
                    <h2 className="text-2xl font-bold text-slate-900">
                      {filteredHomes.length} home{filteredHomes.length === 1 ? "" : "s"} in view
                    </h2>
                  </div>
                  <div className="flex items-center gap-3 text-sm text-slate-600">
                    <div className="bg-white/80 border border-slate-100 px-4 py-3 rounded-2xl shadow-sm">
                      <p className="text-xs uppercase tracking-wide text-slate-500 font-semibold">Price range</p>
                      <p className="font-semibold text-slate-900">
                        {formatCurrency(minPrice)} – {formatCurrency(maxPrice)}
                      </p>
                    </div>
                    <div className="bg-white/80 border border-slate-100 px-4 py-3 rounded-2xl shadow-sm">
                      <p className="text-xs uppercase tracking-wide text-slate-500 font-semibold">Avg price</p>
                      <p className="font-semibold text-slate-900">
                        {formatCurrency(avgPrice)}
                      </p>
                    </div>
                    <div className="bg-white/80 border border-slate-100 px-4 py-3 rounded-2xl shadow-sm">
                      <p className="text-xs uppercase tracking-wide text-slate-500 font-semibold">Avg size</p>
                      <p className="font-semibold text-slate-900">
                        {avgSqft ? `${avgSqft.toLocaleString()} sqft` : "—"}
                      </p>
                    </div>
                    <div className="bg-indigo-50 border border-indigo-100 px-4 py-3 rounded-2xl shadow-sm text-indigo-800">
                      <p className="text-xs uppercase tracking-wide font-semibold">Anomalies</p>
                      <p className="font-semibold">
                        {filteredHomes.filter((h) => h.anomaly).length} flagged
                      </p>
                    </div>
                  </div>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
                  {filteredHomes.map((home) => {
                    const pricePerSqft =
                      home.price && home.sqft ? Math.round(home.price / home.sqft) : null;
                    return (
                      <div
                        key={home.externalId}
                        className="group bg-white/90 border border-slate-100 rounded-2xl shadow-lg hover:shadow-2xl transition hover:-translate-y-1 backdrop-blur"
                      >
                        <div className="h-1 rounded-t-2xl bg-gradient-to-r from-blue-600 via-indigo-500 to-purple-500" />
                        <div className="p-5 space-y-3">
                          <div className="flex items-start justify-between gap-3">
                            <div>
                              <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                                {home.city}, {home.state}
                              </p>
                              <h2 className="text-lg font-semibold text-slate-900">
                                {home.address}
                              </h2>
                            </div>
                            <div className="flex flex-col gap-1 items-end">
                              <span className="text-xs font-semibold px-3 py-1 rounded-full bg-blue-50 text-blue-700">
                                For Sale
                              </span>
                              {home.anomaly && (
                                <span className="text-[11px] font-semibold px-2 py-1 rounded-full bg-amber-100 text-amber-800">
                                  Anomaly
                                </span>
                              )}
                            </div>
                          </div>
                          <p className="text-2xl font-bold text-slate-900">
                            ${home.price.toLocaleString()}
                          </p>
                          <div className="flex items-center gap-4 text-slate-700 text-sm">
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
                              {pricePerSqft ? `$${pricePerSqft}/sqft` : "Details"}
                            </span>
                          </div>
                          {home.renovation && (
                            <div className="mt-3 rounded-xl bg-slate-50 border border-slate-100 p-3">
                              <p className="text-xs uppercase tracking-wide text-slate-500 font-semibold mb-1">
                                Renovation uplift
                              </p>
                              <div className="flex items-center justify-between">
                                <div className="text-sm text-slate-700">
                                  +{home.renovation.addBedrooms} bed / +{home.renovation.addBathrooms} bath · +{home.renovation.addedSqft} sqft
                                </div>
                                <div className="text-right">
                                  <p className="text-sm text-slate-500">Projected</p>
                                  <p className="text-lg font-semibold text-green-700">
                                    ${home.renovation.predictedNewPrice.toLocaleString()}
                                  </p>
                                </div>
                              </div>
                              <p className="text-xs text-green-700 font-semibold mt-1">
                                +${home.renovation.estimatedUplift.toLocaleString()} uplift
                              </p>
                            </div>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </>
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

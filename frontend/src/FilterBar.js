
import React from "react";

function FilterBar({ filters, setFilters, applyFilters, onClear }) {
  const handleChange = (key) => (e) => {
    const value = e.target.value;
    setFilters((prev) => ({ ...prev, [key]: value }));
  };

  const handleClear = () => {
    setFilters({
      beds: "",
      baths: "",
      minPrice: "",
      maxPrice: "",
    });
    if (onClear) onClear();
  };

  return (
    <div className="bg-white/80 mt-2 p-6 rounded-2xl shadow-sm border border-slate-100 backdrop-blur">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h2 className="text-lg font-semibold text-gray-800">
            Filter Results
          </h2>
          <p className="text-sm text-slate-600">Narrow down by minimums and budget.</p>
        </div>
      </div>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <label className="flex flex-col text-sm text-gray-700">
          <span className="mb-1 font-medium">Min Beds</span>
          <input
            type="number"
            min="0"
            value={filters.beds}
            onChange={handleChange("beds")}
            placeholder="e.g. 3"
            className="border rounded-lg px-3 py-2"
            aria-label="Minimum beds"
          />
        </label>
        <label className="flex flex-col text-sm text-gray-700">
          <span className="mb-1 font-medium">Min Baths</span>
          <input
            type="number"
            min="0"
            value={filters.baths}
            onChange={handleChange("baths")}
            placeholder="e.g. 2"
            className="border rounded-lg px-3 py-2"
            aria-label="Minimum baths"
          />
        </label>
        <label className="flex flex-col text-sm text-gray-700">
          <span className="mb-1 font-medium">Min Price</span>
          <input
            type="number"
            min="0"
            value={filters.minPrice}
            onChange={handleChange("minPrice")}
            placeholder="e.g. 300000"
            className="border rounded-lg px-3 py-2"
            aria-label="Minimum price"
          />
        </label>
        <label className="flex flex-col text-sm text-gray-700">
          <span className="mb-1 font-medium">Max Price</span>
          <input
            type="number"
            min="0"
            value={filters.maxPrice}
            onChange={handleChange("maxPrice")}
            placeholder="e.g. 750000"
            className="border rounded-lg px-3 py-2"
            aria-label="Maximum price"
          />
        </label>
      </div>

      <div className="flex flex-wrap gap-3 mt-5">
        <button
          onClick={applyFilters}
          className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700"
        >
          Apply Filters
        </button>
        <button
          onClick={handleClear}
          className="bg-gray-100 text-gray-700 px-4 py-2 rounded-lg hover:bg-gray-200"
        >
          Clear
        </button>
      </div>
    </div>
  );
}

export default FilterBar;

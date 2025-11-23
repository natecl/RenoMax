import React from "react";

function FilterBar({ filters, setFilters, applyFilters }) {
  return (
    <div className="bg-white p-4 rounded-xl shadow flex flex-wrap gap-4 items-end mt-6">
      
      {/* Beds */}
      <div>
        <label className="block text-sm font-medium text-gray-700">Beds</label>
        <select
          className="border p-2 rounded w-32"
          value={filters.beds}
          onChange={(e) => setFilters({ ...filters, beds: e.target.value })}
        >
          <option value="">Any</option>
          <option value="1">1+</option>
          <option value="2">2+</option>
          <option value="3">3+</option>
          <option value="4">4+</option>
        </select>
      </div>

      {/* Baths */}
      <div>
        <label className="block text-sm font-medium text-gray-700">Baths</label>
        <select
          className="border p-2 rounded w-32"
          value={filters.baths}
          onChange={(e) => setFilters({ ...filters, baths: e.target.value })}
        >
          <option value="">Any</option>
          <option value="1">1+</option>
          <option value="2">2+</option>
          <option value="3">3+</option>
        </select>
      </div>

      {/* Min Price */}
      <div>
        <label className="block text-sm font-medium text-gray-700">Min Price</label>
        <input
          type="number"
          className="border p-2 rounded w-32"
          placeholder="0"
          value={filters.minPrice}
          onChange={(e) => setFilters({ ...filters, minPrice: e.target.value })}
        />
      </div>

      {/* Max Price */}
      <div>
        <label className="block text-sm font-medium text-gray-700">Max Price</label>
        <input
          type="number"
          className="border p-2 rounded w-32"
          placeholder="Any"
          value={filters.maxPrice}
          onChange={(e) => setFilters({ ...filters, maxPrice: e.target.value })}
        />
      </div>

      {/* Apply Button */}
      <button
        onClick={applyFilters}
        className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700"
      >
        Apply Filters
      </button>
    </div>
  );
}

export default FilterBar;

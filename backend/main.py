from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import requests
import os
from dotenv import load_dotenv
import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest, RandomForestRegressor
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os





# Load environment variables
load_dotenv()

app = FastAPI()

app.mount("/static", StaticFiles(directory="frontend/build/static"), name="static")
# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# SERVE REACT FRONTEND
@app.get("/{full_path:path}")
def serve_react_app(full_path: str):
    index_path = os.path.join("frontend", "build", "index.html")
    return FileResponse(index_path)

# ✅ Zillow.com (apimaker) RapidAPI key
API_KEY = os.getenv("RAPIDAPI_KEY", "YOUR_API_KEY_HERE")


def build_zillow_url(zipcode: str, limit: int) -> tuple[str, dict]:
    """
    Build Zillow.com (apimaker) API URL and headers.
    Use /propertyExtendedSearch since it supports ZIPs.
    """
    base = "https://zillow-com1.p.rapidapi.com/propertyExtendedSearch"
    url = f"{base}?location={zipcode}&status_type=ForSale&home_type=Houses&limit={limit}"
    headers = {
        "X-RapidAPI-Key": API_KEY,
        "X-RapidAPI-Host": "zillow-com1.p.rapidapi.com",
    }
    return url, headers


def simplify_properties(raw: list[dict]) -> list[dict]:
    """
    Convert Zillow raw data into a clean and consistent shape for ML analysis.
    Filters out incomplete or unrealistic records.
    """
    simplified = []
    for item in raw:
        simplified.append({
            "address": item.get("address"),
            "city": item.get("city") or "Unknown",
            "state": item.get("state") or "CA",
            "zipcode": item.get("zipcode") or None,
            "bedrooms": item.get("bedrooms"),
            "bathrooms": item.get("bathrooms"),
            "sqft": item.get("livingArea") or item.get("area"),
            "price": item.get("price") or item.get("unformattedPrice") or item.get("zestimate"),
            "lat": item.get("latitude"),
            "lng": item.get("longitude"),
            "externalId": item.get("zpid") or item.get("id"),
        })
    
    # Filter out missing or unrealistic values
    clean = [
        p for p in simplified
        if p["price"] and p["price"] > 50000
        and p["bedrooms"] and p["bathrooms"]
        and p["sqft"] and p["sqft"] > 300
        and p["lat"] and p["lng"]
    ]
    return clean


@app.get("/housing/{zipcode}")
def get_housing_by_zip(
    zipcode: str,
    limit: int = Query(20, ge=1, le=100),
    raw: bool = Query(False)
):
    """
    Fetch Zillow data for a ZIP code using apimaker's Zillow.com API.
    If too few homes are returned, automatically try nearby ZIPs.
    """
    if not API_KEY or API_KEY == "YOUR_API_KEY_HERE":
        raise HTTPException(status_code=500, detail="RAPIDAPI_KEY not configured in .env")

    # Helper function to fetch a single ZIP
    def fetch_zip(zipcode: str):
        url, headers = build_zillow_url(zipcode, limit)
        try:
            response = requests.get(url, headers=headers, timeout=20)
            if response.status_code != 200:
                return []
            data = response.json()
            if isinstance(data, dict):
                data = data.get("props", data.get("properties", []))
            return simplify_properties(data)
        except Exception:
            return []

    # Start with the main ZIP
    all_props = fetch_zip(zipcode)

    # If not enough, expand to neighboring ZIPs (±1 and ±2)
    if len(all_props) < 10:
        try:
            zip_int = int(zipcode)
            neighbors = [str(zip_int - 2), str(zip_int - 1), str(zip_int + 1), str(zip_int + 2)]
            for z in neighbors:
                all_props.extend(fetch_zip(z))
        except ValueError:
            pass  # ignore if ZIP isn't numeric

    # Deduplicate by address
    seen = set()
    unique_props = []
    for p in all_props:
        if p["address"] not in seen:
            seen.add(p["address"])
            unique_props.append(p)

    if not unique_props:
        raise HTTPException(status_code=404, detail=f"No valid housing data found near ZIP {zipcode}.")

    return unique_props if raw else unique_props


@app.get("/anomalies/{zipcode}")
def detect_anomalies_and_simulate_fix(
    zipcode: str,
    limit: int = Query(50, ge=5, le=200)
):
    """
    Detect undervalued homes, calculate ROI, and categorize them
    as 'good investment' or 'good renovation' opportunities.
    """
    data = get_housing_by_zip(zipcode, limit=limit, raw=False)

    if not data:
        raise HTTPException(status_code=404, detail="No valid housing data found for this ZIP code.")

    df = pd.DataFrame(data)
    numeric_cols = ["bedrooms", "bathrooms", "sqft", "price"]
    df = df[numeric_cols].dropna()

    if df.empty or len(df) < 10:
        raise HTTPException(status_code=400, detail="Not enough clean data to analyze anomalies.")

    # Train Random Forest model
    X = df[["bedrooms", "bathrooms", "sqft"]]
    y = df["price"]
    rf = RandomForestRegressor(n_estimators=100, random_state=42, n_jobs=-1)
    rf.fit(X, y)

    df["predicted_price"] = rf.predict(X)
    df["price_diff"] = df["price"] - df["predicted_price"]

    # Detect anomalies
    iso = IsolationForest(contamination=0.1, random_state=42)
    df["is_anomaly"] = iso.fit_predict(df[["bedrooms", "bathrooms", "sqft", "price_diff"]]) == -1

    avg_features = df[["bedrooms", "bathrooms", "sqft"]].mean().to_dict()
    upgraded_records = []

    for _, row in df[df["is_anomaly"]].iterrows():
        added_features = {}
        adjusted = row.copy()

        # Simulate feature improvements
        for f in ["bedrooms", "bathrooms"]:
            if row[f] < avg_features[f]:
                diff = max(0, round(avg_features[f] - row[f]))
                adjusted[f] += diff
                added_features[f] = diff

        if not added_features:
            continue

        # Predict new price after upgrades
        new_price = rf.predict([[adjusted["bedrooms"], adjusted["bathrooms"], adjusted["sqft"]]])[0]
        price_gain = new_price - row["price"]

        if price_gain > 0:
            potential_investment_score = round((price_gain / row["price"]) * 100, 2)

            # Categorize home
            if potential_investment_score >= 15:
                category = "good_investment"
            elif potential_investment_score >= 5:
                category = "good_renovation"
            else:
                continue  # skip low ROI homes

            upgraded_records.append({
                "original": {
                    "bedrooms": row["bedrooms"],
                    "bathrooms": row["bathrooms"],
                    "sqft": row["sqft"],
                    "price": round(row["price"], 2),
                    "predicted_price": round(row["predicted_price"], 2),
                    "price_diff": round(row["price_diff"], 2),
                },
                "adjusted": {
                    "bedrooms": adjusted["bedrooms"],
                    "bathrooms": adjusted["bathrooms"],
                    "sqft": adjusted["sqft"],
                    "new_price": round(new_price, 2),
                    "price_gain": round(price_gain, 2),
                    "potential_investment_score": potential_investment_score,
                    "category": category,
                },
                "added_features": added_features,
            })

    # Separate homes by category
    good_investments = [h for h in upgraded_records if h["adjusted"]["category"] == "good_investment"]
    good_renovations = [h for h in upgraded_records if h["adjusted"]["category"] == "good_renovation"]

    return {
        "zipcode": zipcode,
        "total_homes_analyzed": len(df),
        "undervalued_homes_found": len(upgraded_records),
        "feature_importance": dict(zip(["bedrooms", "bathrooms", "sqft"], rf.feature_importances_.round(3).tolist())),
        "good_investments": good_investments,
        "good_renovations": good_renovations,
    }



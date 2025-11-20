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

# Load environment variables
load_dotenv()

app = FastAPI()

# Serve React static files
app.mount(
    "/static",
    StaticFiles(directory="../frontend/build/static"),
    name="static"
)

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Zillow API key
API_KEY = os.getenv("RAPIDAPI_KEY", "YOUR_API_KEY_HERE")


def build_zillow_url(zipcode: str, limit: int):
    base = "https://zillow-com1.p.rapidapi.com/propertyExtendedSearch"
    url = f"{base}?location={zipcode}&status_type=ForSale&home_type=Houses&limit={limit}"
    headers = {
        "X-RapidAPI-Key": API_KEY,
        "X-RapidAPI-Host": "zillow-com1.p.rapidapi.com",
    }
    return url, headers


def simplify_properties(raw):
    simplified = []
    for item in raw:
        simplified.append({
            "address": item.get("address"),
            "city": item.get("city") or "Unknown",
            "state": item.get("state") or "CA",
            "zipcode": item.get("zipcode"),
            "bedrooms": item.get("bedrooms"),
            "bathrooms": item.get("bathrooms"),
            "sqft": item.get("livingArea") or item.get("area"),
            "price": item.get("price") or item.get("unformattedPrice") or item.get("zestimate"),
            "lat": item.get("latitude"),
            "lng": item.get("longitude"),
            "externalId": item.get("zpid") or item.get("id"),
        })

    clean = [
        p for p in simplified
        if p["price"] and p["price"] > 50000
        and p["bedrooms"] and p["bathrooms"]
        and p["sqft"] and p["sqft"] > 300
        and p["lat"] and p["lng"]
    ]
    return clean


@app.get("/housing/{zipcode}")
def get_housing_by_zip(zipcode: str, limit: int = Query(20, ge=1, le=100), raw: bool = Query(False)):
    if not API_KEY or API_KEY == "YOUR_API_KEY_HERE":
        raise HTTPException(status_code=500, detail="RAPIDAPI_KEY not configured.")

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
        except:
            return []

    all_props = fetch_zip(zipcode)

    if len(all_props) < 10:
        try:
            zip_int = int(zipcode)
            neighbors = [str(zip_int - 2), str(zip_int - 1), str(zip_int + 1), str(zip_int + 2)]
            for z in neighbors:
                all_props.extend(fetch_zip(z))
        except:
            pass

    seen = set()
    unique_props = []
    for p in all_props:
        if p["address"] not in seen:
            seen.add(p["address"])
            unique_props.append(p)

    if not unique_props:
        raise HTTPException(status_code=404, detail=f"No valid housing data found near ZIP {zipcode}.")

    return unique_props


@app.get("/anomalies/{zipcode}")
def detect_anomalies_and_simulate_fix(zipcode: str, limit: int = Query(50, ge=5, le=200)):
    data = get_housing_by_zip(zipcode, limit=limit, raw=False)
    if not data:
        raise HTTPException(status_code=404, detail="No valid housing data found.")

    df = pd.DataFrame(data)
    df = df[["bedrooms", "bathrooms", "sqft", "price"]].dropna()

    if df.empty or len(df) < 10:
        raise HTTPException(status_code=400, detail="Not enough clean data.")

    X = df[["bedrooms", "bathrooms", "sqft"]]
    y = df["price"]

    rf = RandomForestRegressor(n_estimators=100, random_state=42, n_jobs=-1)
    rf.fit(X, y)

    df["predicted_price"] = rf.predict(X)
    df["price_diff"] = df["price"] - df["predicted_price"]

    iso = IsolationForest(contamination=0.1, random_state=42)
    df["is_anomaly"] = iso.fit_predict(df[["bedrooms", "bathrooms", "sqft", "price_diff"]]) == -1

    avg_features = df[["bedrooms", "bathrooms", "sqft"]].mean().to_dict()
    upgraded_records = []

    for _, row in df[df["is_anomaly"]].iterrows():
        added = {}
        adjusted = row.copy()

        for f in ["bedrooms", "bathrooms"]:
            if row[f] < avg_features[f]:
                diff = max(0, round(avg_features[f] - row[f]))
                adjusted[f] += diff
                added[f] = diff

        if not added:
            continue

        new_price = rf.predict([[adjusted["bedrooms"], adjusted["bathrooms"], adjusted["sqft"]]])[0]
        gain = new_price - row["price"]

        if gain > 0:
            score = round((gain / row["price"]) * 100, 2)

            if score >= 15:
                category = "good_investment"
            elif score >= 5:
                category = "good_renovation"
            else:
                continue

            upgraded_records.append({
                "original": {
                    "bedrooms": row["bedrooms"],
                    "bathrooms": row["bathrooms"],
                    "sqft": row["sqft"],
                    "price": round(row["price"]),
                    "predicted_price": round(row["predicted_price"]),
                    "price_diff": round(row["price_diff"]),
                },
                "adjusted": {
                    "bedrooms": adjusted["bedrooms"],
                    "bathrooms": adjusted["bathrooms"],
                    "sqft": adjusted["sqft"],
                    "new_price": round(new_price),
                    "price_gain": round(gain),
                    "potential_investment_score": score,
                    "category": category,
                },
                "added_features": added,
            })

    return {
        "zipcode": zipcode,
        "total_homes_analyzed": len(df),
        "undervalued_homes_found": len(upgraded_records),
        "good_investments": [h for h in upgraded_records if h["adjusted"]["category"] == "good_investment"],
        "good_renovations": [h for h in upgraded_records if h["adjusted"]["category"] == "good_renovation"],
    }


# 🎉 Serve React Frontend
@app.get("/")
def serve_react_root():
    return FileResponse("../frontend/build/index.html")

@app.get("/{full_path:path}")
def react_fallback(full_path: str):
    return FileResponse("../frontend/build/index.html")

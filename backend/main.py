from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import requests
import os
from dotenv import load_dotenv
import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest, RandomForestRegressor

# Load environment variables (for your RAPIDAPI_KEY)
load_dotenv()

app = FastAPI()

# Allow CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"message": "Backend is running!"}


# ✅ Use RAPIDAPI key for Zillow
API_KEY = os.getenv("RAPIDAPI_KEY", "YOUR_API_KEY_HERE")

# ✅ Build Zillow API URL
def build_zillow_url(zipcode: str, limit: int) -> tuple[str, dict]:
    base = "https://zillow56.p.rapidapi.com/search"
    url = f"{base}?location={zipcode}&limit={limit}"
    headers = {
        "X-RapidAPI-Key": API_KEY,
        "X-RapidAPI-Host": "zillow56.p.rapidapi.com",
    }
    return url, headers


# ✅ Simplify Zillow property response into your clean schema
def simplify_properties(raw: list[dict]) -> list[dict]:
    simplified = []
    for item in raw:
        simplified.append({
            "address": item.get("address"),
            "city": item.get("city"),
            "state": item.get("state"),
            "zipcode": item.get("zipcode"),
            "bedrooms": item.get("bedrooms"),
            "bathrooms": item.get("bathrooms"),
            "sqft": item.get("livingArea") or item.get("sqft"),
            "price": item.get("price") or item.get("unformattedPrice") or item.get("zestimate"),
            "listedDate": item.get("datePosted") or item.get("listedDate"),
            "lat": item.get("latitude"),
            "lng": item.get("longitude"),
            "externalId": item.get("zpid") or item.get("id"),
        })
    return simplified


# ✅ Fetch Zillow housing data
@app.get("/housing/{zipcode}")
def get_housing_by_zip(
    zipcode: str,
    limit: int = Query(10, ge=1, le=100, description="Max number of properties to return (1–100)"),
    raw: bool = Query(False, description="Return raw provider JSON if true, else simplified list"),
):
    if not API_KEY or API_KEY == "YOUR_API_KEY_HERE":
        raise HTTPException(status_code=500, detail="API key is not configured. Set RAPIDAPI_KEY in .env")

    # ✅ Call Zillow (not RentCast)
    url, headers = build_zillow_url(zipcode, limit)

    try:
        response = requests.get(url, headers=headers, timeout=15)
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Upstream request failed: {e!s}")

    if response.status_code == 401:
        raise HTTPException(status_code=502, detail="Provider rejected API key (401 Unauthorized).")
    if response.status_code == 429:
        raise HTTPException(status_code=502, detail="Rate limit exceeded by provider (429 Too Many Requests).")
    if response.status_code >= 400:
        raise HTTPException(status_code=502, detail=f"Provider error: HTTP {response.status_code}")

    try:
        data = response.json()
    except ValueError:
        raise HTTPException(status_code=502, detail="Provider returned invalid JSON.")

    # ✅ Zillow’s API returns "results" instead of "properties"
    if isinstance(data, dict) and "results" in data:
        data = data["results"]

    if not isinstance(data, list):
        data = [data]

    return data if raw else simplify_properties(data)


# ✅ Anomaly detection endpoint
@app.get("/anomalies/{zipcode}")
def detect_anomalies_and_simulate_fix(
    zipcode: str,
    limit: int = Query(50, ge=5, le=200, description="Number of properties to analyze")
):
    data = get_housing_by_zip(zipcode, limit=limit, raw=False)

    if not data:
        raise HTTPException(status_code=404, detail="No housing data found for this ZIP code.")
    
    df = pd.DataFrame(data)
    numeric_cols = ["bedrooms", "bathrooms", "sqft", "price"]
    df = df[[col for col in numeric_cols if col in df.columns]].dropna()

    if df.empty or len(df) < 10:
        raise HTTPException(status_code=400, detail="Not enough clean data to analyze anomalies.")

    X = df[["bedrooms", "bathrooms", "sqft"]]
    y = df["price"]

    rf = RandomForestRegressor(n_estimators=100, random_state=42, n_jobs=-1)
    rf.fit(X, y)

    df["predicted_price"] = rf.predict(X)
    df["price_diff"] = df["price"] - df["predicted_price"]

    features_for_anomaly = ["bedrooms", "bathrooms", "sqft", "price_diff"]
    iso = IsolationForest(contamination=0.1, random_state=42)
    df["anomaly_score"] = iso.fit_predict(df[features_for_anomaly])
    df["is_anomaly"] = df["anomaly_score"] == -1

    avg_features = df[["bedrooms", "bathrooms", "sqft"]].mean().to_dict()

    upgraded_records = []
    for _, row in df[df["is_anomaly"]].iterrows():
        added_features = {}
        adjusted_features = {
            "bedrooms": row["bedrooms"],
            "bathrooms": row["bathrooms"],
            "sqft": row["sqft"]
        }

        for feature in ["bedrooms", "bathrooms"]:
            if row[feature] < avg_features[feature]:
                diff = max(0, round(avg_features[feature] - row[feature]))
                adjusted_features[feature] += diff
                added_features[feature] = diff

        if not added_features:
            continue

        new_price = rf.predict([[adjusted_features["bedrooms"], adjusted_features["bathrooms"], adjusted_features["sqft"]]])[0]
        price_gain = new_price - row["price"]

        upgraded_records.append({
            "original_features": {
                "bedrooms": row["bedrooms"],
                "bathrooms": row["bathrooms"],
                "sqft": row["sqft"],
                "price": round(row["price"], 2),
                "predicted_price": round(row["predicted_price"], 2),
                "price_diff": round(row["price_diff"], 2)
            },
            "adjusted_features": {
                "bedrooms": adjusted_features["bedrooms"],
                "bathrooms": adjusted_features["bathrooms"],
                "sqft": adjusted_features["sqft"],
                "new_predicted_price": round(new_price, 2),
                "estimated_value_increase": round(price_gain, 2)
            },
            "added_features": added_features
        })

    return {
        "zipcode": zipcode,
        "total_homes_analyzed": len(df),
        "anomalies_found": len(upgraded_records),
        "feature_importance": dict(zip(["bedrooms", "bathrooms", "sqft"], rf.feature_importances_.round(3).tolist())),
        "upgraded_anomalous_homes": upgraded_records
    }

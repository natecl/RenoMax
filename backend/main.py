from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import requests
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

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

API_KEY= os.getenv("RENTCAST_API_KEY", "YOUR_API_KEY_HERE")

def build_rentcast_url(zipcode: str, Limit: int) -> tuple[str, dict]:
    base="https://api.rentcast.io/v1/properties"
    url= f"{base}?postalCode={zipcode}&limit={Limit}"

    headers = {
        "accept": "application/json",
        "X-API-Key": API_KEY,
    }
    return url, headers

def simplify_properties(raw: list[dict]) -> list[dict]:
    """
    Optional post-processing: return a clean, consistent shape for the frontend.
    We map external API fields into our own stable schema.
    """
    simplified = []
    for item in raw:
        simplified.append({
            "address": item.get("formattedAddress") or item.get("address"),
            "city": item.get("city"),
            "state": item.get("state"),
            "zipcode": item.get("postalCode") or item.get("zipCode"),
            "bedrooms": item.get("bedrooms"),
            "bathrooms": item.get("bathrooms"),
            "sqft": item.get("squareFootage") or item.get("sqft"),
            "price": item.get("price") or item.get("lastSalePrice") or item.get("listedPrice"),
            "listedDate": item.get("listedDate") or item.get("lastSaleDate"),
            # Include IDs/coords if present; useful later for maps and de-duplication
            "lat": item.get("latitude"),
            "lng": item.get("longitude"),
            "externalId": item.get("id") or item.get("propertyId"),
        })
    return simplified

@app.get("/housing/{zipcode}")

def get_housing_by_zip(
    zipcode: str,
    limit: int= Query(10, ge=1, le=100, description= "Max number of properties to return (1-100)"),
    raw: bool= Query( False, description="Return raw provider JSON if true, else simplified list"),
):
    if not API_KEY or API_KEY == "YOUR_API_KEY_HERE":
        raise HTTPException(status_code=500, detail="API key is not configured. Set RENTCAST_API_KEY in .env")
    
    url, headers= build_rentcast_url(zipcode, limit)

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
    
    if not isinstance(data, list):
        data= data.get("properties") if isinstance(data, dict) else []

    return data if raw else simplify_properties(data)
    
from sklearn.ensemble import IsolationForest, RandomForestRegressor
import pandas as pd
import numpy as np

from sklearn.ensemble import IsolationForest, RandomForestRegressor
import pandas as pd
import numpy as np

@app.get("/anomalies/{zipcode}")
def detect_anomalies_and_simulate_fix(
    zipcode: str,
    limit: int = Query(50, ge=5, le=200, description="Number of properties to analyze per ZIP")
):
    """
    Detect homes that are missing features (e.g., fewer bathrooms than peers)
    and estimate what their price would be if upgraded to match area averages.
    Combines data from the target ZIP and nearby ZIP codes for better model accuracy.
    """

    
    try:
        zip_int = int(zipcode)
        nearby_zips = [str(zip_int + offset).zfill(5) for offset in range(-2, 3)]
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid ZIP code format. Use numbers only.")

    
    combined_data = []
    for z in nearby_zips:
        try:
            data = get_housing_by_zip(z, limit=limit, raw=False)
            if data:
                for item in data:
                    item["source_zip"] = z  
                combined_data.extend(data)
        except Exception as e:
            print(f"Warning: failed to fetch data for ZIP {z}: {e}")

    if not combined_data:
        raise HTTPException(status_code=404, detail="No housing data found for these ZIP codes.")

    df = pd.DataFrame(combined_data)
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
        original = row.to_dict()

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
            "source_zip": row.get("source_zip"),
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
        "included_zips": nearby_zips,
        "total_homes_analyzed": len(df),
        "anomalies_found": len(upgraded_records),
        "feature_importance": dict(zip(["bedrooms", "bathrooms", "sqft"], rf.feature_importances_.round(3).tolist())),
        "upgraded_anomalous_homes": upgraded_records
    }

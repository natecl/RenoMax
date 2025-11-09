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
    
from sklearn.ensemble import IsolationForest
import pandas as pd
import numpy as np

@app.get("/anomalies/{zipcode}")
def detect_anomalies(
    zipcode: str,
    limit: int= Query(50, ge=5, le=200, description="Number of properties to analyze")
):
    data= get_housing_by_zip(zipcode, limit=limit, raw=False)

    if not data:
        raise HTTPException(status_code=404, detail="No housing data found for this ZIP code.")
    
    df=pd.DataFrame(data)

    numeric_cols= ["bedrooms", "bathrooms", "sqft", "price"]
    df=df[[col for col in numeric_cols if col in df.columns]].copy()

    df = df.dropna()
    if df.empty:
        raise HTTPException(status_code=400, detail="Not enough data to analyze anomalies.")
    
    model = IsolationForest(contamination=0.1, random_state=42)
    df["anomaly_score"]= model.fit_predict(df)

    '''
    Isolation forest model is a unsupervised anomaly detection model that randomly partitions data and isolates points that are easier to separate.
    '''
    df["is_anomaly"]=df["anomaly_score"]==-1

    anomalies = df[df["is_anomaly"]].to_dict(orient="records")
    normal = df[~df["is_anomaly"]].to_dict(orient="records")

    return {
        "zipcode": zipcode,
        "total_homes_analyzed": len(df),
        "anomalies_found": len(anomalies),
        "anomalous_homes": anomalies,
        "normal_homes": normal[:5],
    }

#Regression model for adjusted feature prediction

from sklearn.ensemble import RandomForestRegressor

@app.get("/predict_price/{zipcode}")
def predict_price_adjustment(
    zipcode: str,
    limit: int= Query(50, ge=5, le=200),
    add_bedrooms: int= Query(0),
    add_bathrooms: int= Query(0)
):

    data= get_housing_by_zip(zipcode, limit=limit, raw=False)

    if not data:
        raise HTTPException(status_code=404, detail="No housing data found for this ZIP code.")

    df = pd.DataFrame(data)

    features= ["bedrooms", "bathrooms", "sqft"]
    target= "price"

    df= df[[*features, target]].dropna()

    if df.empty:
        raise HTTPException(statys_code=400, detail="Insufficient clean data to train model.")
    
    X = df[features]
    y = df[target]

    model= RandomForestRegressor(
        n_estimators=100,
        random_state=42,
        max_depth=None,
        n_jobs=-1
    )

    model.fit(X,y)

    avg_house= df[features].mean().to_dict()
    base_price= model.predict([list(avg_house.values())])[0]

    adjusted_house= avg_house.copy()
    adjusted_house["bedrooms"] += add_bedrooms
    adjusted_house["bathrooms"] += add_bathrooms

    adjusted_price=model.predict([list(adjusted_house.values())])[0]

    return {
        "zipcode": zipcode,
        "base_price": round(base_price, 2),
        "adjusted_price": round(adjusted_price, 2),
        "feature_change": {
            "added_bedrooms": add_bedrooms,
            "added_bathrooms": add_bathrooms
        },
        "estimated_increase": round(adjusted_price - base_price, 2),
        "feature_importance": dict(zip(features, model.feature_importances_.round(3).tolist()))
    }

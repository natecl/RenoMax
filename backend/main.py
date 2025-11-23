from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import os
import requests
import pandas as pd
from sklearn.ensemble import IsolationForest, RandomForestRegressor
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

# CORS so frontend can call backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # You can paste your frontend Render URL here later
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

API_KEY = os.getenv("RAPIDAPI_KEY", "")

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
def get_housing_by_zip(zipcode: str, limit: int = Query(20, ge=1, le=100)):
    if not API_KEY:
        raise HTTPException(status_code=500, detail="RAPIDAPI_KEY is not configured on Render.")

    def fetch_zip(z):
        url, headers = build_zillow_url(z, limit)
        try:
            r = requests.get(url, headers=headers, timeout=15)
            if r.status_code != 200:
                return []
            data = r.json()
            if isinstance(data, dict):
                data = data.get("props", data.get("properties", []))
            return simplify_properties(data)
        except:
            return []

    props = fetch_zip(zipcode)

    # Extend to neighbor ZIPs if needed
    if len(props) < 10:
        try:
            z = int(zipcode)
            for n in [z-1, z+1]:
                props.extend(fetch_zip(str(n)))
        except:
            pass

    seen = set()
    unique = []
    for p in props:
        if p["address"] not in seen:
            seen.add(p["address"])
            unique.append(p)

    if not unique:
        raise HTTPException(status_code=404, detail="No valid housing data found.")

    return unique

from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import os
import requests
import pandas as pd
from sklearn.ensemble import IsolationForest, RandomForestRegressor
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

# Allow frontend to call backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # or put your Render frontend URL here
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
def get_housing_by_zip(zipcode: str, limit: int = Query(20, ge=1, le=100)):
    if not API_KEY or API_KEY == "YOUR_API_KEY_HERE":
        raise HTTPException(status_code=500, detail="RAPIDAPI_KEY not set.")

    def fetch_zip(z):
        url, headers = build_zillow_url(z, limit)
        try:
            r = requests.get(url, headers=headers, timeout=20)
            if r.status_code != 200:
                return []
            data = r.json()
            if isinstance(data, dict):
                data = data.get("props", data.get("properties", []))
            return simplify_properties(data)
        except:
            return []

    props = fetch_zip(zipcode)

    if len(props) < 10:
        try:
            z = int(zipcode)
            neighbors = [str(z - 1), str(z + 1)]
            for n in neighbors:
                props.extend(fetch_zip(n))
        except:
            pass

    seen = set()
    unique = []
    for p in props:
        if p["address"] not in seen:
            seen.add(p["address"])
            unique.append(p)

    if not unique:
        raise HTTPException(status_code=404, detail="No data found.")

    return unique

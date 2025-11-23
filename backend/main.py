from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os
import requests
import pandas as pd
from sklearn.ensemble import IsolationForest, RandomForestRegressor
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

# ---------------------------------------------------------
# FIX: ABSOLUTE, SAFE PATHS TO FRONTEND BUILD
# ---------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.join(BASE_DIR, "..", "frontend", "build")
FRONTEND_DIR = os.path.abspath(FRONTEND_DIR)
STATIC_DIR = os.path.join(FRONTEND_DIR, "static")

print("Frontend:", FRONTEND_DIR)
print("Static:", STATIC_DIR)

# Serve React static folder
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Allow frontend → backend requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

API_KEY = os.getenv("RAPIDAPI_KEY")


# ---------------------------------------------------------
# Zillow API helpers
# ---------------------------------------------------------
def build_zillow_url(zipcode: str, limit: int):
    base = "https://zillow-com1.p.rapidapi.com/propertyExtendedSearch"
    url = f"{base}?location={zipcode}&status_type=ForSale&home_type=Houses&limit={limit}"

    headers = {
        "X-RapidAPI-Key": API_KEY,
        "X-RapidAPI-Host": "zillow-com1.p.rapidapi.com",
    }
    return url, headers


def simplify_properties(raw):
    simple = []
    for item in raw:
        simple.append({
            "address": item.get("address"),
            "city": item.get("city") or "Unknown",
            "state": item.get("state") or "CA",
            "zipcode": item.get("zipcode"),
            "bedrooms": item.get("bedrooms"),
            "bathrooms": item.get("bathrooms"),
            "sqft": item.get("livingArea") or item.get("area"),
            "price": item.get("price")
                     or item.get("unformattedPrice")
                     or item.get("zestimate"),
            "lat": item.get("latitude"),
            "lng": item.get("longitude"),
            "externalId": item.get("zpid") or item.get("id")
        })
    return [
        p for p in simple
        if p["price"] and p["sqft"] and p["sqft"] > 300
    ]


# ---------------------------------------------------------
# Housing search endpoint
# ---------------------------------------------------------
@app.get("/housing/{zipcode}")
def get_housing(zipcode: str, limit: int = Query(20)):
    if not API_KEY:
        raise HTTPException(500, "Missing RAPIDAPI_KEY")

    def fetch(z):
        url, headers = build_zillow_url(z, limit)
        try:
            r = requests.get(url, headers=headers, timeout=15)
            if r.status_code != 200:
                return []
            data = r.json()
            props = data.get("props") or data.get("properties") or []
            return simplify_properties(props)
        except:
            return []

    homes = fetch(zipcode)

    # Expand search if too few results
    if len(homes) < 10:
        try:
            z = int(zipcode)
            for neighbor in [z - 1, z + 1, z - 2, z + 2]:
                homes.extend(fetch(str(neighbor)))
        except:
            pass

    # Remove duplicate addresses
    seen = set()
    unique = []
    for h in homes:
        if h["address"] not in seen:
            seen.add(h["address"])
            unique.append(h)

    if not unique:
        raise HTTPException(404, f"No homes found near {zipcode}")

    return unique


# ---------------------------------------------------------
# React frontend routes
# ---------------------------------------------------------
@app.get("/")
def serve_index():
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))


@app.get("/{path:path}")
def serve_react_app(path: str):
    """
    Catch-all: always return index.html
    (Allows React Router to work)
    """
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))

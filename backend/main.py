from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

import os
import requests
import pandas as pd
from sklearn.ensemble import IsolationForest, RandomForestRegressor
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = FastAPI()

# ---------------------------------------------------------
#  FRONTEND STATIC PATH FIX (THIS PREVENTS BROWSER CRASH)
# ---------------------------------------------------------
BASE_DIR = os.path.dirname(__file__)
FRONTEND_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", "frontend", "build"))
STATIC_DIR = os.path.join(FRONTEND_DIR, "static")

# Serve React static files
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Allow CORS for local frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Zillow API Key
API_KEY = os.getenv("RAPIDAPI_KEY", "YOUR_API_KEY_HERE")


# ---------------------------------------------------------
#  HELPER FUNCTIONS
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


# ---------------------------------------------------------
#  HOUSING ENDPOINT
# ---------------------------------------------------------
@app.get("/housing/{zipcode}")
def get_housing_by_zip(zipcode: str, limit: int = Query(20, ge=1, le=100)):
    if not API_KEY or API_KEY == "YOUR_API_KEY_HERE":
        raise HTTPException(status_code=500, detail="RAPIDAPI_KEY not configured.")

    def fetch_zip(zipcode_local: str):
        url, headers = build_zillow_url(zipcode_local, limit)

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

    # Expand search if needed
    if len(all_props) < 10:
        try:
            z = int(zipcode)
            neighbors = [str(z - 2), str(z - 1), str(z + 1), str(z + 2)]
            for n in neighbors:
                all_props.extend(fetch_zip(n))
        except:
            pass

    # Remove duplicates
    seen = set()
    unique = []
    for p in all_props:
        if p["address"] not in seen:
            seen.add(p["address"])
            unique.append(p)

    if not unique:
        raise HTTPException(status_code=404, detail=f"No valid housing data near ZIP {zipcode}.")

    return unique


# ---------------------------------------------------------
#  ANOMALY DETECTION
# ---------------------------------------------------------
@app.get("/anomalies/{zipcode}")
def detect_anomalies_and_simulate_fix(zipcode: str, limit: int = Query(50, ge=5, le=200)):
    data = get_housing_by_zip(zipcode, limit)

    df = pd.DataFrame(data)
    df = df[["bedrooms", "bathrooms", "sqft", "price"]].dropna()

    if df.empty or len(df) < 10:
        raise HTTPException(status_code=400, detail="Not enough clean data to analyze.")

    X = df[["bedrooms", "bathrooms", "sqft"]]
    y = df["price"]

    rf = RandomForestRegressor(n_estimators=100, random_state=42, n_jobs=-1)
    rf.fit(X, y)

    df["predicted_price"] = rf.predict(X)
    df["price_diff"] = df["price"] - df["predicted_price"]

    iso = IsolationForest(contamination=0.1, random_state=42)
    df["is_anomaly"] = iso.fit_predict(df[["bedrooms", "bathrooms", "sqft", "price_diff"]]) == -1

    avg_features = df[["bedrooms", "bathrooms", "sqft"]].mean()

    upgraded = []

    for _, row in df[df["is_anomaly"]].iterrows():
        adjusted = row.copy()
        added = {}

        for f in ["bedrooms", "bathrooms"]:
            if row[f] < avg_features[f]:
                diff = round(avg_features[f] - row[f])
                if diff > 0:
                    added[f] = diff
                    adjusted[f] += diff

        if not added:
            continue

        new_price = rf.predict([[adjusted["bedrooms"], adjusted["bathrooms"], adjusted["sqft"]]])[0]
        gain = new_price - row["price"]

        if gain > 0:
            score = (gain / row["price"]) * 100

            if score >= 15:
                category = "good_investment"
            elif score >= 5:
                category = "good_renovation"
            else:
                continue

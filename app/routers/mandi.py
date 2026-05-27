import os
import logging
import httpx
from fastapi import APIRouter, Query
from typing import Optional

router = APIRouter(
    prefix="/api/mandi",
    tags=["Mandi Prices"],
)

logger = logging.getLogger(__name__)

# Constants for Government API
DATA_GOV_API_URL = "https://api.data.gov.in/resource/9ef84268-d588-465a-a308-a864a43d0070"

# High-quality realistic mock data generator for fallback
MOCK_COMMODITIES = [
    {"commodity": "Rice", "variety": "Common", "min_price": 2100, "max_price": 2700, "modal_price": 2400},
    {"commodity": "Wheat", "variety": "Lokwan", "min_price": 2300, "max_price": 2900, "modal_price": 2600},
    {"commodity": "Tomato", "variety": "Local", "min_price": 1200, "max_price": 2500, "modal_price": 1800},
    {"commodity": "Onion", "variety": "Red", "min_price": 1500, "max_price": 2800, "modal_price": 2200},
    {"commodity": "Potato", "variety": "Jyoti", "min_price": 1000, "max_price": 1800, "modal_price": 1400},
    {"commodity": "Cotton", "variety": "Medium Staple", "min_price": 6200, "max_price": 7500, "modal_price": 6800},
    {"commodity": "Maize", "variety": "Yellow", "min_price": 1850, "max_price": 2200, "modal_price": 2000},
    {"commodity": "Sugarcane", "variety": "Co 86032", "min_price": 290, "max_price": 350, "modal_price": 315},
]

@router.get("/prices")
async def get_mandi_prices(
    state: Optional[str] = Query(None, description="Filter by State (e.g. Tamil Nadu)"),
    district: Optional[str] = Query(None, description="Filter by District (e.g. Madurai)"),
    commodity: Optional[str] = Query(None, description="Filter by Commodity (e.g. Rice)"),
    limit: int = Query(50, ge=1, le=100)
):
    api_key = os.getenv("DATA_GOV_API_KEY", "")
    
    # If no API key is set, use realistic mock data
    if not api_key:
        logger.warning("DATA_GOV_API_KEY environment variable is not set. Serving demo/mock data.")
        return generate_mock_prices(state, district, commodity, limit)

    # Prepare query params for data.gov.in API
    params = {
        "api-key": api_key,
        "format": "json",
        "limit": limit
    }
    
    # Add filters if provided
    # Government API uses case-sensitive matching sometimes
    filter_count = 0
    if state:
        params[f"filters[state]"] = state
        filter_count += 1
    if district:
        params[f"filters[district]"] = district
        filter_count += 1
    if commodity:
        params[f"filters[commodity]"] = commodity
        filter_count += 1

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(DATA_GOV_API_URL, params=params)
            
            if response.status_code == 200:
                data = response.json()
                records = data.get("records", [])
                
                # Format response nicely
                formatted_records = []
                for rec in records:
                    formatted_records.append({
                        "state": rec.get("state"),
                        "district": rec.get("district"),
                        "market": rec.get("market"),
                        "commodity": rec.get("commodity"),
                        "variety": rec.get("variety"),
                        "min_price": float(rec.get("min_price", 0)),
                        "max_price": float(rec.get("max_price", 0)),
                        "modal_price": float(rec.get("modal_price", 0)),
                        "arrival_date": rec.get("arrival_date")
                    })
                
                # If filter returned empty result, fallback to mock data so UI still shows items
                if not formatted_records and filter_count > 0:
                    return generate_mock_prices(state, district, commodity, limit, note="Live empty, showing mock")

                return {
                    "status": "success",
                    "is_live": True,
                    "records": formatted_records
                }
            else:
                logger.error(f"Government API returned status {response.status_code}: {response.text}")
                return generate_mock_prices(state, district, commodity, limit, error=f"API status {response.status_code}")
                
    except Exception as e:
        logger.error(f"Error connecting to Government Mandi API: {e}")
        return generate_mock_prices(state, district, commodity, limit, error=str(e))

def generate_mock_prices(state: str, district: str, commodity: str, limit: int, error: str = None, note: str = None):
    # Set default values if not selected
    selected_state = state or "Maharashtra"
    selected_district = district or "Pune"
    
    import random
    from datetime import datetime
    
    # Use deterministic seeding based on day/district to keep prices stable for the day
    today_str = datetime.today().strftime("%Y-%m-%d")
    seed_str = f"{selected_state}-{selected_district}-{today_str}"
    random.seed(hash(seed_str))
    
    mandis = [f"{selected_district} Market", f"{selected_district} APMC", "Rural Mandi Sub-Center"]
    
    records = []
    for c in MOCK_COMMODITIES:
        # Filter by commodity if requested
        if commodity and commodity.lower() not in c["commodity"].lower():
            continue
            
        # Add random variation to prices based on seed
        var_factor = random.uniform(0.9, 1.1)
        min_p = int(c["min_price"] * var_factor)
        max_p = int(c["max_price"] * var_factor)
        mod_p = int((min_p + max_p) / 2)
        
        # Add to records for random markets
        for mandi in mandis[:random.randint(1, 3)]:
            records.append({
                "state": selected_state,
                "district": selected_district,
                "market": mandi,
                "commodity": c["commodity"],
                "variety": c["variety"],
                "min_price": min_p,
                "max_price": max_p,
                "modal_price": mod_p,
                "arrival_date": datetime.today().strftime("%d/%m/%Y")
            })
            
    # Reset seed
    random.seed()
    
    return {
        "status": "success",
        "is_live": False,
        "records": records[:limit],
        "debug_info": {"error": error, "note": note} if (error or note) else None
    }

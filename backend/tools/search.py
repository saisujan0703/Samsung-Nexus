"""
NEXUS Search Tools — Destination, Hotel, and Activity search with realistic mock data.

These tools use deterministic mock data for hackathon reliability.
The architecture allows real API backends to be swapped in later.
"""

from __future__ import annotations

import asyncio
import random
from typing import Any

from backend.tools.base import BaseTool, ToolResult, ToolResultStatus


# ---------------------------------------------------------------------------
# Mock Data
# ---------------------------------------------------------------------------

DESTINATIONS_DB = {
    "chennai": [
        {"name": "Marina Beach", "type": "beach", "rating": 4.3, "walking": "moderate", "cost_per_person": 0, "description": "India's longest urban beach, 13 km stretch along the Bay of Bengal"},
        {"name": "Kapaleeshwarar Temple", "type": "temple", "rating": 4.6, "walking": "low", "cost_per_person": 0, "description": "Ancient Dravidian-style Shiva temple in Mylapore"},
        {"name": "Fort St. George", "type": "historical", "rating": 4.2, "walking": "moderate", "cost_per_person": 25, "description": "First English fortress in India, now houses a museum"},
        {"name": "Government Museum", "type": "museum", "rating": 4.1, "walking": "moderate", "cost_per_person": 50, "description": "Second oldest museum in India with rich collections"},
        {"name": "Mahabalipuram", "type": "heritage", "rating": 4.7, "walking": "high", "cost_per_person": 100, "description": "UNESCO World Heritage Site with ancient rock-cut temples"},
        {"name": "San Thome Cathedral", "type": "church", "rating": 4.4, "walking": "low", "cost_per_person": 0, "description": "Basilica built over the tomb of St. Thomas the Apostle"},
        {"name": "Guindy National Park", "type": "park", "rating": 4.0, "walking": "high", "cost_per_person": 30, "description": "One of the smallest national parks in India"},
        {"name": "DakshinaChitra", "type": "cultural", "rating": 4.5, "walking": "moderate", "cost_per_person": 150, "description": "Living museum showcasing South Indian heritage and architecture"},
        {"name": "Express Avenue Mall", "type": "shopping", "rating": 4.2, "walking": "low", "cost_per_person": 0, "description": "Premium shopping and entertainment destination"},
        {"name": "Elliot's Beach", "type": "beach", "rating": 4.1, "walking": "low", "cost_per_person": 0, "description": "Quieter alternative to Marina Beach, great for evening walks"},
    ],
    "bangalore": [
        {"name": "Lalbagh Botanical Garden", "type": "park", "rating": 4.5, "walking": "high", "cost_per_person": 20, "description": "Historic botanical garden with glass house"},
        {"name": "Bangalore Palace", "type": "palace", "rating": 4.2, "walking": "moderate", "cost_per_person": 230, "description": "Tudor-style palace inspired by Windsor Castle"},
        {"name": "Cubbon Park", "type": "park", "rating": 4.4, "walking": "moderate", "cost_per_person": 0, "description": "Sprawling green space in the heart of the city"},
    ],
    "default": [
        {"name": "City Center", "type": "landmark", "rating": 4.0, "walking": "moderate", "cost_per_person": 0, "description": "Main city center area with attractions"},
        {"name": "Local Market", "type": "shopping", "rating": 3.8, "walking": "moderate", "cost_per_person": 0, "description": "Traditional local market experience"},
    ],
}

HOTELS_DB = {
    "chennai": [
        {"name": "Taj Coromandel", "stars": 5, "price_per_night": 8500, "rating": 4.7, "area": "Nungambakkam", "accessibility": "excellent", "amenities": ["pool", "spa", "restaurant", "gym", "wheelchair_access"]},
        {"name": "ITC Grand Chola", "stars": 5, "price_per_night": 9200, "rating": 4.8, "area": "Guindy", "accessibility": "excellent", "amenities": ["pool", "spa", "restaurant", "gym", "wheelchair_access"]},
        {"name": "Hyatt Regency", "stars": 5, "price_per_night": 7000, "rating": 4.5, "area": "Teynampet", "accessibility": "good", "amenities": ["pool", "restaurant", "gym"]},
        {"name": "Trident Chennai", "stars": 4, "price_per_night": 5500, "rating": 4.3, "area": "Mount Road", "accessibility": "good", "amenities": ["pool", "restaurant"]},
        {"name": "FabHotel Prime", "stars": 3, "price_per_night": 2200, "rating": 3.9, "area": "T. Nagar", "accessibility": "moderate", "amenities": ["restaurant", "wifi"]},
        {"name": "OYO Townhouse", "stars": 3, "price_per_night": 1800, "rating": 3.7, "area": "Anna Nagar", "accessibility": "moderate", "amenities": ["wifi", "parking"]},
        {"name": "Zostel Chennai", "stars": 2, "price_per_night": 800, "rating": 4.0, "area": "Mylapore", "accessibility": "basic", "amenities": ["wifi", "common_area"]},
        {"name": "Backpacker Panda", "stars": 2, "price_per_night": 600, "rating": 3.8, "area": "Egmore", "accessibility": "basic", "amenities": ["wifi"]},
        {"name": "Hotel Kanchi", "stars": 3, "price_per_night": 2500, "rating": 4.0, "area": "Egmore", "accessibility": "good", "amenities": ["restaurant", "wifi", "parking"]},
        {"name": "GreenPark Chennai", "stars": 4, "price_per_night": 4200, "rating": 4.2, "area": "Vadapalani", "accessibility": "good", "amenities": ["pool", "restaurant", "gym"]},
    ],
    "default": [
        {"name": "City Hotel", "stars": 3, "price_per_night": 2000, "rating": 3.8, "area": "City Center", "accessibility": "moderate", "amenities": ["wifi", "restaurant"]},
        {"name": "Budget Inn", "stars": 2, "price_per_night": 1000, "rating": 3.5, "area": "Station Area", "accessibility": "basic", "amenities": ["wifi"]},
    ],
}

ACTIVITIES_DB = {
    "chennai": [
        {"name": "South Indian Cooking Class", "duration_hours": 3, "cost_per_person": 1500, "walking": "low", "type": "experience", "description": "Learn to cook authentic Tamil cuisine"},
        {"name": "Heritage Walk - Mylapore", "duration_hours": 2, "cost_per_person": 500, "walking": "high", "type": "tour", "description": "Guided walk through historic Mylapore"},
        {"name": "Boat Ride - Muttukadu", "duration_hours": 2, "cost_per_person": 300, "walking": "low", "type": "adventure", "description": "Boating at Muttukadu boathouse"},
        {"name": "Kathakali Performance", "duration_hours": 2, "cost_per_person": 800, "walking": "low", "type": "cultural", "description": "Traditional dance performance"},
        {"name": "Street Food Tour", "duration_hours": 3, "cost_per_person": 600, "walking": "moderate", "type": "food", "description": "Explore Chennai's vibrant street food scene"},
        {"name": "Crocodile Farm Visit", "duration_hours": 2, "cost_per_person": 200, "walking": "moderate", "type": "nature", "description": "Visit one of the largest crocodile farms in the world"},
        {"name": "Auto Rickshaw City Tour", "duration_hours": 4, "cost_per_person": 400, "walking": "low", "type": "tour", "description": "See the city from a classic auto rickshaw"},
        {"name": "Silk Saree Shopping", "duration_hours": 2, "cost_per_person": 0, "walking": "low", "type": "shopping", "description": "Browse Kanchipuram silk sarees at T. Nagar"},
    ],
}


# ---------------------------------------------------------------------------
# Search Tools
# ---------------------------------------------------------------------------

class DestinationSearchTool(BaseTool):
    name = "destination_search"
    description = "Search for tourist destinations and attractions in a city"
    category = "SEARCH"

    async def execute(self, params: dict[str, Any], cancel_event: asyncio.Event) -> ToolResult:
        city = params.get("city", "").lower()
        max_walking = params.get("max_walking", None)  # low, moderate, high
        budget_per_person = params.get("budget_per_person", None)

        await self._simulate_latency(1.5, cancel_event)

        destinations = DESTINATIONS_DB.get(city, DESTINATIONS_DB["default"])

        # Apply filters
        if max_walking:
            walking_order = {"low": 0, "moderate": 1, "high": 2}
            max_level = walking_order.get(max_walking, 2)
            destinations = [d for d in destinations if walking_order.get(d["walking"], 2) <= max_level]

        if budget_per_person is not None:
            destinations = [d for d in destinations if d["cost_per_person"] <= budget_per_person]

        count = len(destinations)
        status = ToolResultStatus.SUCCESS_WITH_RESULTS if count > 0 else ToolResultStatus.SUCCESS_WITH_NO_RESULTS
        summary = (
            f"Found {count} destinations in {city.title()}"
            if count > 0
            else f"No destinations found in {city.title()}"
        )
        return ToolResult(
            success=True,
            status=status.value,
            data={"destinations": destinations, "city": city, "count": count, "status": status.value},
            summary=summary,
        )


class HotelSearchTool(BaseTool):
    name = "hotel_search"
    description = "Search for hotels with price, rating, and accessibility filters"
    category = "SEARCH"

    async def execute(self, params: dict[str, Any], cancel_event: asyncio.Event) -> ToolResult:
        city = params.get("city", "").lower()
        max_price = params.get("max_price_per_night", None)
        min_rating = params.get("min_rating", None)
        min_accessibility = params.get("min_accessibility", None)
        num_nights = params.get("num_nights", 1)
        num_rooms = params.get("num_rooms", 1)

        await self._simulate_latency(2.0, cancel_event)

        hotels = list(HOTELS_DB.get(city, HOTELS_DB["default"]))

        if max_price is not None:
            hotels = [h for h in hotels if h["price_per_night"] <= max_price]

        if min_rating is not None:
            hotels = [h for h in hotels if h["rating"] >= min_rating]

        if min_accessibility:
            acc_order = {"basic": 0, "moderate": 1, "good": 2, "excellent": 3}
            min_level = acc_order.get(min_accessibility, 0)
            hotels = [h for h in hotels if acc_order.get(h["accessibility"], 0) >= min_level]

        # Add total cost calculation
        for h in hotels:
            h["total_cost"] = h["price_per_night"] * num_nights * num_rooms

        hotels.sort(key=lambda h: h["rating"], reverse=True)
        count = len(hotels)

        if count > 0:
            status = ToolResultStatus.SUCCESS_WITH_RESULTS
            summary = f"Found {count} hotels in {city.title()} within budget"
        else:
            status = ToolResultStatus.SUCCESS_WITH_NO_RESULTS
            summary = (
                f"No hotels found in {city.title()} within budget of ₹{max_price:,}/night"
                if max_price
                else f"No hotels found in {city.title()} within budget"
            )

        return ToolResult(
            success=True,
            status=status.value,
            data={
                "hotels": hotels,
                "city": city,
                "count": count,
                "num_nights": num_nights,
                "status": status.value,
            },
            summary=summary,
        )


class ActivitySearchTool(BaseTool):
    name = "activity_search"
    description = "Search for activities and experiences in a city"
    category = "SEARCH"

    async def execute(self, params: dict[str, Any], cancel_event: asyncio.Event) -> ToolResult:
        city = params.get("city", "").lower()
        max_walking = params.get("max_walking", None)
        max_cost_per_person = params.get("max_cost_per_person", None)
        activity_type = params.get("type", None)

        await self._simulate_latency(1.8, cancel_event)

        activities = ACTIVITIES_DB.get(city, [])

        if max_walking:
            walking_order = {"low": 0, "moderate": 1, "high": 2}
            max_level = walking_order.get(max_walking, 2)
            activities = [a for a in activities if walking_order.get(a["walking"], 2) <= max_level]

        if max_cost_per_person is not None:
            activities = [a for a in activities if a["cost_per_person"] <= max_cost_per_person]

        if activity_type:
            activities = [a for a in activities if a["type"] == activity_type]

        count = len(activities)
        status = ToolResultStatus.SUCCESS_WITH_RESULTS if count > 0 else ToolResultStatus.SUCCESS_WITH_NO_RESULTS
        summary = (
            f"Found {count} activities in {city.title()}"
            if count > 0
            else f"No activities found in {city.title()}"
        )

        return ToolResult(
            success=True,
            status=status.value,
            data={"activities": activities, "city": city, "count": count, "status": status.value},
            summary=summary,
        )

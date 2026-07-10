import os
import requests
from dotenv import load_dotenv

load_dotenv()


def _fallback_doctors(specialist, city):
    return [
        {
            "name": f"{specialist} near {city}",
            "address": "Google Places API key is missing or doctor search failed.",
            "rating": "Not available",
            "reviews": 0,
            "phone": "Not available",
            "website": "Not available",
            "maps_link": f"https://www.google.com/maps/search/{specialist}+doctor+in+{city}".replace(" ", "+"),
            "source": "fallback"
        }
    ]


def search_nearby_doctors(specialist, city="Delhi", max_results=5):
    specialist = specialist or "General Physician"
    city = city or "Delhi"

    api_key = os.getenv("GOOGLE_PLACES_API_KEY")

    if not api_key:
        print("GOOGLE_PLACES_API_KEY missing in .env")
        return _fallback_doctors(specialist, city)

    url = "https://places.googleapis.com/v1/places:searchText"

    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": (
            "places.displayName,"
            "places.formattedAddress,"
            "places.rating,"
            "places.userRatingCount,"
            "places.nationalPhoneNumber,"
            "places.websiteUri,"
            "places.googleMapsUri"
        )
    }

    payload = {
        "textQuery": f"{specialist} doctor in {city}",
        "maxResultCount": max_results
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=20)

        if response.status_code != 200:
            print("Google Places API error:")
            print(response.text)
            return _fallback_doctors(specialist, city)

        data = response.json()
        doctors = []

        for place in data.get("places", []):
            doctors.append({
                "name": place.get("displayName", {}).get("text", "Unknown"),
                "address": place.get("formattedAddress", "Not available"),
                "rating": place.get("rating", "No rating"),
                "reviews": place.get("userRatingCount", 0),
                "phone": place.get("nationalPhoneNumber", "Not available"),
                "website": place.get("websiteUri", "Not available"),
                "maps_link": place.get("googleMapsUri", "Not available"),
                "source": "google_places"
            })

        if not doctors:
            return _fallback_doctors(specialist, city)

        return doctors

    except Exception as e:
        print(f"Doctor search failed: {e}")
        return _fallback_doctors(specialist, city)


if __name__ == "__main__":
    doctors = search_nearby_doctors("Cardiologist", "Delhi")
    for doctor in doctors:
        print(doctor)
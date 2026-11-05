import os
import re
from typing import Optional

import requests
from dotenv import load_dotenv

load_dotenv()

GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")
PLACES_BASE_URL = "https://places.googleapis.com/v1"

SEARCH_FIELDS = [
    "places.id",
    "places.displayName",
    "places.formattedAddress",
    "places.shortFormattedAddress",
    "places.location",
    "places.primaryTypeDisplayName",
    "places.businessStatus",
]

DETAIL_FIELDS = [
    "id",
    "displayName",
    "formattedAddress",
    "shortFormattedAddress",
    "addressComponents",
    "internationalPhoneNumber",
    "nationalPhoneNumber",
    "websiteUri",
    "googleMapsUri",
    "businessStatus",
    "primaryType",
    "primaryTypeDisplayName",
    "rating",
    "userRatingCount",
    "regularOpeningHours",
    "currentOpeningHours",
    "location",
    "timeZone",
]


class BusinessLookupError(Exception):
    pass


def _headers(field_mask: str) -> dict:
    if not GOOGLE_MAPS_API_KEY:
        raise BusinessLookupError("GOOGLE_MAPS_API_KEY manquante dans .env")

    return {
        "X-Goog-Api-Key": GOOGLE_MAPS_API_KEY,
        "X-Goog-FieldMask": field_mask,
        "Content-Type": "application/json",
    }


def search_businesses(
    query: str,
    language: str = "fr",
    region: str = "FR",
    max_results: int = 5,
) -> list[dict]:
    """
    Recherche des commerces à partir d'un texte libre.
    Exemples :
      - "Boulangerie 12 rue de la Paix Paris"
      - "Le Petit Café, Nanterre"
      - "Coiffeur Bella, 92000 Nanterre"
    """
    if not query or len(query.strip()) < 3:
        raise BusinessLookupError("La recherche doit contenir au moins 3 caractères.")

    response = requests.post(
        f"{PLACES_BASE_URL}/places:searchText",
        headers=_headers(",".join(SEARCH_FIELDS)),
        json={
            "textQuery": query.strip(),
            "languageCode": language,
            "regionCode": region,
            "maxResultCount": max_results,
        },
        timeout=15,
    )

    if response.status_code != 200:
        raise BusinessLookupError(
            f"Erreur Google Places Search [{response.status_code}] : {response.text}"
        )

    places = response.json().get("places", [])

    return [
        {
            "place_id": place.get("id"),
            "name": place.get("displayName", {}).get("text"),
            "address": place.get("formattedAddress"),
            "short_address": place.get("shortFormattedAddress"),
            "category": place.get("primaryTypeDisplayName", {}).get("text"),
            "business_status": place.get("businessStatus"),
            "latitude": place.get("location", {}).get("latitude"),
            "longitude": place.get("location", {}).get("longitude"),
        }
        for place in places
    ]


def get_business_details(place_id: str, language: str = "fr") -> dict:
    """
    Récupère les informations détaillées d'un commerce à partir de son place_id.
    """
    if not place_id:
        raise BusinessLookupError("place_id est obligatoire.")

    response = requests.get(
        f"{PLACES_BASE_URL}/places/{place_id}",
        headers=_headers(",".join(DETAIL_FIELDS)),
        params={"languageCode": language},
        timeout=15,
    )

    if response.status_code != 200:
        raise BusinessLookupError(
            f"Erreur Google Places Details [{response.status_code}] : {response.text}"
        )

    place = response.json()

    address_components = place.get("addressComponents", [])
    components = {}

    for component in address_components:
        for component_type in component.get("types", []):
            components[component_type] = component.get("longText")

    google_hours = google_hours_to_weekly(place.get("regularOpeningHours"))

    return {
        "place_id": place.get("id"),
        "name": place.get("displayName", {}).get("text"),
        "address": place.get("formattedAddress"),
        "street": components.get("route"),
        "street_number": components.get("street_number"),
        "postal_code": components.get("postal_code"),
        "city": components.get("locality") or components.get("postal_town"),
        "country": components.get("country"),
        "phone": place.get("nationalPhoneNumber"),
        "international_phone": place.get("internationalPhoneNumber"),
        "website": place.get("websiteUri"),
        "google_maps_url": place.get("googleMapsUri"),
        "category": place.get("primaryTypeDisplayName", {}).get("text"),
        "business_status": place.get("businessStatus"),
        "rating": place.get("rating"),
        "review_count": place.get("userRatingCount"),
        "google_hours": google_hours,
        "is_open_now": _get_open_now(place.get("currentOpeningHours")),
        "latitude": place.get("location", {}).get("latitude"),
        "longitude": place.get("location", {}).get("longitude"),
        "timezone": place.get("timeZone", {}).get("id"),
    }


def _get_open_now(current_opening_hours: Optional[dict]) -> Optional[bool]:
    if not current_opening_hours:
        return None

    return current_opening_hours.get("openNow")


def clean_phone(phone: Optional[str]) -> Optional[str]:
    """Normalise un numéro pour un agent téléphonique : chiffres et + uniquement."""
    if not phone:
        return None

    return re.sub(r"[^\d+]", "", phone)


def google_hours_to_weekly(opening_hours: Optional[dict]) -> Optional[dict]:
    """Convertit regularOpeningHours Google (0 = dimanche) en semaine 0 = lundi."""
    periods = (opening_hours or {}).get("periods")
    if not periods:
        return None

    days: dict[int, list] = {d: [] for d in range(7)}
    for period in periods:
        start, end = period.get("open") or {}, period.get("close")
        if not end:  # ouvert 24h/24, 7j/7
            return {
                "source": "google",
                "days": [{"day": d, "slots": [{"open": "00:00", "close": "24:00"}]} for d in range(7)],
            }
        day = (start.get("day", 0) - 1) % 7
        close = f"{end.get('hour', 0):02d}:{end.get('minute', 0):02d}"
        days[day].append({
            "open": f"{start.get('hour', 0):02d}:{start.get('minute', 0):02d}",
            "close": "24:00" if close == "00:00" else close,
        })

    return {
        "source": "google",
        "days": [{"day": d, "slots": sorted(days[d], key=lambda s: s["open"])} for d in range(7)],
    }
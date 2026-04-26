from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter

_geolocator = Nominatim(user_agent="aegis-route-hackathon")
_geocode = RateLimiter(_geolocator.geocode, min_delay_seconds=1)

# Bounding box: covers Altadena, Pasadena, and surrounding LA area
# (west, north), (east, south)
_LA_VIEWBOX = [(-118.65, 34.10), (-118.30, 33.95)]


def geocode_location(description: str) -> tuple[float, float] | None:
    try:
        result = _geocode(description, viewbox=_LA_VIEWBOX, bounded=True, timeout=10)
        if result is None:
            result = _geocode(description + ", Los Angeles, California", timeout=10)
        if result is None:
            return None
        return (result.latitude, result.longitude)
    except Exception:
        return None

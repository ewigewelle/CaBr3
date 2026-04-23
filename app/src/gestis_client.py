import logging
import requests

class GestisClient:
    BASE_URL = "https://gestis-api.dguv.de/api"
    
    def __init__(self, token=None):
        # Using the token from the original code
        self.token = token or "dddiiasjhduuvnnasdkkwUUSHhjaPPKMasd"
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/json"
        }

    def search(self, query, exact=False):
        """Search for a substance by name or CAS."""
        try:
            # Original code uses GET with query parameters
            # and search types like 'stoffname' or 'nummern' (for CAS)
            search_type = "nummern" if any(c.isdigit() for c in query) and "-" in query else "stoffname"
            exact_str = "true" if exact else "false"
            url = f"{self.BASE_URL}/search/de?{search_type}={query}&exact={exact_str}"
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            
            # The API returns a list of results directly
            results = response.json()
            # Map to expected format
            formatted = []
            for item in results:
                # The API often uses 'zvg_nr' instead of just 'zvg'
                zvg_id = item.get("zvg_nr") or item.get("zvgNr") or item.get("zvg") or ""
                formatted.append({
                    "id": zvg_id,
                    "name": item.get("name", ""),
                    "cas": item.get("cas", "N/A")
                })
            return formatted
        except Exception as e:
            logging.error(f"GESTIS search failed: {e}")
            return []

    def get_article(self, zvg_number):
        """Fetch full article data by ZVG number."""
        try:
            zvg_formatted = str(zvg_number).zfill(6)
            url = f"{self.BASE_URL}/article/de/{zvg_formatted}"
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logging.error(f"GESTIS get_article failed: {e}")
            return None

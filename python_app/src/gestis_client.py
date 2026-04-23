import requests
import logging

class GestisClient:
    BASE_URL = "https://gestis-api.dguv.de/api"
    
    def __init__(self, token=None):
        self.token = token or "7b47b47b-47b4-47b4-47b4-47b47b47b47b" # Placeholder token if none provided
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/json"
        }

    def search(self, query):
        """Search for a substance by name or CAS."""
        try:
            url = f"{self.BASE_URL}/search/de"
            payload = {"term": query, "limit": 20}
            response = requests.post(url, json=payload, headers=self.headers)
            response.raise_for_status()
            return response.json().get("beispiele", [])
        except Exception as e:
            logging.error(f"GESTIS search failed: {e}")
            return []

    def get_article(self, zvg_number):
        """Fetch full article data by ZVG number."""
        try:
            # ZVG numbers should be 6 digits, left-padded with zeros
            zvg_formatted = str(zvg_number).zfill(6)
            url = f"{self.BASE_URL}/article/de/{zvg_formatted}"
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logging.error(f"GESTIS get_article failed: {e}")
            return None

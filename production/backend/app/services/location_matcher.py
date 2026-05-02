import pickle
from pathlib import Path
from typing import Tuple, Optional
import Levenshtein

class LocationMatcher:
    def __init__(self):
        models_path = Path(__file__).resolve().parent.parent.parent / "models"
        self.pickup_map = pickle.load(open(models_path / "pickup_location_map.pkl", "rb"))
        self.drop_map = pickle.load(open(models_path / "drop_location_map.pkl", "rb"))
        self.le_pickup = pickle.load(open(models_path / "le_pickup.pkl", "rb"))
        self.le_drop = pickle.load(open(models_path / "le_drop.pkl", "rb"))

    def encode_location(self, location: str, location_type: str = "pickup") -> Optional[int]:
        """Encode location string to integer, with fallback"""
        le = self.le_pickup if location_type == "pickup" else self.le_drop
        # Try exact match
        try:
            return le.transform([location])[0]
        except:
            # Try fuzzy match with known locations
            known = list(le.classes_)
            best_match = None
            best_score = 0
            for k in known:
                score = Levenshtein.ratio(location.lower(), k.lower())
                if score > best_score:
                    best_score = score
                    best_match = k
            if best_match:
                return le.transform([best_match])[0]
            return 0 # default for fallback
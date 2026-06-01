"""
Sidebar Favorites Manager - Persistent storage
Saves favorites to JSON file so they persist across sessions
"""

import json
import os
from pathlib import Path
from typing import List
from sidebar_assets import AssetItem


FAVORITES_FILE = Path(__file__).parent / "data" / "sidebar_favorites.json"


def ensure_favorites_file():
    """Create favorites directory if it doesn't exist"""
    FAVORITES_FILE.parent.mkdir(parents=True, exist_ok=True)


def save_favorites(favorites: List[AssetItem]) -> bool:
    """Save favorites to JSON file"""
    try:
        ensure_favorites_file()
        data = [
            {
                "id": fav.id,
                "symbol": fav.symbol,
                "name": fav.name,
                "price": fav.price,
                "change_percent": fav.change_percent,
            }
            for fav in favorites
        ]
        with open(FAVORITES_FILE, 'w') as f:
            json.dump(data, f, indent=2)
        return True
    except Exception as e:
        print(f"Error saving favorites: {e}")
        return False


def load_favorites() -> List[AssetItem]:
    """Load favorites from JSON file"""
    try:
        ensure_favorites_file()
        if FAVORITES_FILE.exists():
            with open(FAVORITES_FILE, 'r') as f:
                data = json.load(f)
                return [
                    AssetItem(
                        id=item['id'],
                        symbol=item['symbol'],
                        name=item['name'],
                        price=item.get('price'),
                        change_percent=item.get('change_percent'),
                        is_favorite=True
                    )
                    for item in data
                ]
    except Exception as e:
        print(f"Error loading favorites: {e}")
    
    return []


def get_favorites_count() -> int:
    """Get number of saved favorites"""
    favorites = load_favorites()
    return len(favorites)


def clear_favorites() -> bool:
    """Clear all saved favorites"""
    try:
        if FAVORITES_FILE.exists():
            FAVORITES_FILE.unlink()
        return True
    except Exception as e:
        print(f"Error clearing favorites: {e}")
        return False


# Auto-sync with session state
def sync_favorites_to_file(favorites: List[AssetItem]):
    """Sync session state favorites to file (background save)"""
    save_favorites(favorites)


def sync_favorites_from_file() -> List[AssetItem]:
    """Load favorites from file to session state"""
    return load_favorites()

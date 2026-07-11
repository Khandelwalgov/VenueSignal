import json
import os
from pathlib import Path
from app.domain.venue.models import Venue, Level, Zone, Node, Edge, Asset
from app.domain.venue.validator import validate_venue_graph

class VenueService:
    def __init__(self):
        self._venue: Venue = None
        self._validation_result = None

    def load_canonical_venue(self):
        # Determine the root path (one level above apps/api if running from api, or properly resolve it)
        # Assuming the API runs from apps/api and the data is in data/venues
        base_dir = Path(os.getcwd())
        if base_dir.name == "api":
            venue_path = base_dir.parent.parent / "data" / "venues" / "unity-stadium.json"
        else:
            venue_path = base_dir / "data" / "venues" / "unity-stadium.json"
            
        if not venue_path.exists():
            raise FileNotFoundError(f"Canonical venue file not found at {venue_path}")
            
        with open(venue_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        self._venue = Venue(**data)
        self._validation_result = validate_venue_graph(self._venue)
        
        if not self._validation_result.is_valid:
            error_msg = "; ".join(self._validation_result.errors)
            raise ValueError(f"Canonical venue failed validation: {error_msg}")
            
    def get_venue(self) -> Venue:
        if not self._venue:
            self.load_canonical_venue()
        return self._venue
        
    def get_validation_status(self):
        if not self._validation_result:
            self.load_canonical_venue()
        return self._validation_result.to_dict()

    def get_level(self, level_id: str):
        venue = self.get_venue()
        level = next((l for l in venue.levels if l.id == level_id), None)
        if not level:
            return None
            
        return {
            "level": level.model_dump(by_alias=True),
            "zones": [z.model_dump(by_alias=True) for z in venue.zones if z.level_id == level_id],
            "nodes": [n.model_dump(by_alias=True) for n in venue.nodes if n.level_id == level_id],
            "edges": [e.model_dump(by_alias=True) for e in venue.edges if self._is_edge_in_level(e, level_id)],
            "assets": [a.model_dump(by_alias=True) for a in venue.assets if a.level_id == level_id]
        }
        
    def _is_edge_in_level(self, edge: Edge, level_id: str) -> bool:
        from_node = next((n for n in self._venue.nodes if n.id == edge.from_node_id), None)
        to_node = next((n for n in self._venue.nodes if n.id == edge.to_node_id), None)
        if not from_node or not to_node:
            return False
        return from_node.level_id == level_id or to_node.level_id == level_id

    def get_asset(self, asset_id: str):
        venue = self.get_venue()
        return next((a for a in venue.assets if a.id == asset_id), None)

venue_service = VenueService()

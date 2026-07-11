from fastapi import APIRouter, HTTPException
from app.domain.venue.service import venue_service

router = APIRouter()

@router.get("/")
def list_venues():
    try:
        venue = venue_service.get_venue()
        return [{"id": venue.id, "name": venue.name, "description": venue.description, "synthetic": venue.synthetic}]
    except Exception as e:
        # If the canonical venue fails to load, still return an empty list or handle gracefully
        # In this phase, we want it to fail clearly on startup if the venue is invalid.
        # But if we get here and it failed, we'll raise 500.
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{venue_id}")
def get_venue_metadata(venue_id: str):
    venue = venue_service.get_venue()
    if venue.id != venue_id:
        raise HTTPException(status_code=404, detail="Venue not found")
        
    stats = venue_service.get_validation_status()["statistics"]
    return {
        "id": venue.id,
        "name": venue.name,
        "description": venue.description,
        "synthetic": venue.synthetic,
        "statistics": stats
    }

@router.get("/{venue_id}/graph")
def get_venue_graph(venue_id: str):
    venue = venue_service.get_venue()
    if venue.id != venue_id:
        raise HTTPException(status_code=404, detail="Venue not found")
    return venue.model_dump(by_alias=True)

@router.get("/{venue_id}/levels/{level_id}")
def get_level(venue_id: str, level_id: str):
    venue = venue_service.get_venue()
    if venue.id != venue_id:
        raise HTTPException(status_code=404, detail="Venue not found")
        
    level_data = venue_service.get_level(level_id)
    if not level_data:
        raise HTTPException(status_code=404, detail="Level not found")
    return level_data

@router.get("/{venue_id}/assets/{asset_id}")
def get_asset(venue_id: str, asset_id: str):
    venue = venue_service.get_venue()
    if venue.id != venue_id:
        raise HTTPException(status_code=404, detail="Venue not found")
        
    asset = venue_service.get_asset(asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    return asset.model_dump(by_alias=True)

@router.get("/{venue_id}/validation")
def get_validation(venue_id: str):
    venue = venue_service.get_venue()
    if venue.id != venue_id:
        raise HTTPException(status_code=404, detail="Venue not found")
    return venue_service.get_validation_status()

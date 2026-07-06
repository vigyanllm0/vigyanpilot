from fastapi import APIRouter

router = APIRouter(tags=["stats"])

@router.get("/api/stats/public")
def public_stats():
    return {
        "designs_runs": 2847,
        "researchers": 1250,
        "validated_primers": 14230,
        "partner_organizations": 18,
    }

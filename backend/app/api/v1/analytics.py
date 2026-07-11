import csv
import io
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_analytics_engine
from app.database import get_db
from app.services.analytics_engine import AnalyticsEngine
from app.schemas.analytics import FootfallMetrics, DwellMetrics, ZoneAnalytics, HeatmapData, BusinessAnalytics

router = APIRouter()

@router.get("/footfall", response_model=FootfallMetrics, summary="Get footfall counts")
async def get_footfall(
    camera_id: str = Query(..., description="Camera ID"),
    date: str = Query(None, description="Date in YYYY-MM-DD format"),
    db: AsyncSession = Depends(get_db),
    engine: AnalyticsEngine = Depends(get_analytics_engine)
):
    if not date:
        date = datetime.utcnow().strftime("%Y-%m-%d")
    return await engine.get_footfall(db, camera_id, date)

@router.get("/dwell", response_model=DwellMetrics, summary="Get dwell metrics")
async def get_dwell(
    camera_id: str = Query(..., description="Camera ID"),
    date: str = Query(None, description="Date in YYYY-MM-DD format"),
    db: AsyncSession = Depends(get_db),
    engine: AnalyticsEngine = Depends(get_analytics_engine)
):
    if not date:
        date = datetime.utcnow().strftime("%Y-%m-%d")
    return await engine.get_dwell_stats(db, camera_id, date)

@router.get("/zones", response_model=ZoneAnalytics, summary="Get real-time zone occupancy")
async def get_zones(
    camera_id: str = Query(..., description="Camera ID"),
    db: AsyncSession = Depends(get_db),
    engine: AnalyticsEngine = Depends(get_analytics_engine)
):
    return await engine.get_zone_analytics(db, camera_id)

@router.get("/heatmap", response_model=HeatmapData, summary="Get spatial coordinate heatmap data")
async def get_heatmap(
    camera_id: str = Query(..., description="Camera ID"),
    hours_ago: int = Query(24, ge=1, le=168, description="Aggregate hours limit"),
    db: AsyncSession = Depends(get_db),
    engine: AnalyticsEngine = Depends(get_analytics_engine)
):
    return await engine.get_heatmap_data(db, camera_id, hours_ago)

@router.get("/export", summary="Export daily reports as CSV")
async def export_csv(
    camera_id: str = Query(..., description="Camera ID"),
    date: str = Query(None, description="Date in YYYY-MM-DD format"),
    db: AsyncSession = Depends(get_db),
    engine: AnalyticsEngine = Depends(get_analytics_engine)
):
    if not date:
        date = datetime.utcnow().strftime("%Y-%m-%d")
        
    metrics = await engine.get_footfall(db, camera_id, date)
    
    # Generate CSV stream in memory
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Headers
    writer.writerow(["Edge AI CCTV Analytics Daily Report"])
    writer.writerow(["Camera ID", camera_id])
    writer.writerow(["Report Date", date])
    writer.writerow([])
    writer.writerow(["Hourly Trends Summary"])
    writer.writerow(["Hour", "Entries", "Exits"])
    
    for trend in metrics.hourly_trends:
        writer.writerow([trend.hour, trend.entries, trend.exits])
        
    writer.writerow([])
    writer.writerow(["Summary Totals"])
    writer.writerow(["Total Entries", metrics.total_entries])
    writer.writerow(["Total Exits", metrics.total_exits])
    
    output.seek(0)
    
    # Yield byte stream
    def iter_csv():
        yield output.getvalue().encode("utf-8")
        
    return StreamingResponse(
        iter_csv(),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=cctv_analytics_{camera_id}_{date}.csv"}
    )

@router.get("/business", response_model=BusinessAnalytics, summary="Get business analytics metrics (conversion rate, worker hours)")
async def get_business_analytics(
    camera_id: str = Query(..., description="Camera ID"),
    date: str = Query(None, description="Date in YYYY-MM-DD format"),
    db: AsyncSession = Depends(get_db),
    engine: AnalyticsEngine = Depends(get_analytics_engine)
):
    if not date:
        date = datetime.utcnow().strftime("%Y-%m-%d")
    return await engine.get_business_analytics(db, camera_id, date)

from pydantic import BaseModel, Field
from app.api.deps import get_alert_manager
from app.services.alert_manager import AlertManager

class POSScanRequest(BaseModel):
    camera_id: str = Field(..., description="Camera ID mapping to POS terminal")
    timestamp: float = Field(..., description="Timestamp of barcode scan event")
    upc: str = Field(..., description="Scanned barcode value")
    cashier_id: Optional[str] = None

@router.post("/pos/scan", summary="Receive real-time POS scan event for sweethearting validation")
async def pos_scan_webhook(
    payload: POSScanRequest,
    alert_manager: AlertManager = Depends(get_alert_manager)
):
    alert_manager.register_pos_scan(
        camera_id=payload.camera_id,
        timestamp=payload.timestamp,
        upc=payload.upc
    )
    return {"status": "event_registered"}


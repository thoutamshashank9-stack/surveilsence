from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Path
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.database import get_db
from app.models.alert import Alert
from app.models.enums import AlertSeverity, AlertStatus
from app.schemas.alert import AlertResponse, AlertAcknowledge

router = APIRouter()

@router.get("", response_model=List[AlertResponse], summary="List and filter alerts")
async def list_alerts(
    camera_id: Optional[str] = Query(None, description="Filter by camera ID"),
    severity: Optional[AlertSeverity] = Query(None, description="Filter by severity level"),
    status: Optional[AlertStatus] = Query(None, description="Filter by alert status"),
    start_date: Optional[datetime] = Query(None, description="Filter from timestamp"),
    end_date: Optional[datetime] = Query(None, description="Filter to timestamp"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db)
):
    query = select(Alert)
    conditions = []
    
    if camera_id:
        conditions.append(Alert.camera_id == camera_id)
    if severity:
        conditions.append(Alert.severity == severity)
    if status:
        conditions.append(Alert.status == status)
    if start_date:
        conditions.append(Alert.timestamp >= start_date)
    if end_date:
        conditions.append(Alert.timestamp <= end_date)
        
    if conditions:
        query = query.where(and_(*conditions))
        
    query = query.order_by(Alert.timestamp.desc()).offset(offset).limit(limit)
    res = await db.execute(query)
    return res.scalars().all()

@router.get("/stats", summary="Get alert statistics summary")
async def get_stats(db: AsyncSession = Depends(get_db)):
    """Return count summaries grouped by severity and status."""
    q_tot = select(func.count(Alert.id))
    q_act = select(func.count(Alert.id)).where(Alert.status == AlertStatus.ACTIVE)
    q_ack = select(func.count(Alert.id)).where(Alert.status == AlertStatus.ACKNOWLEDGED)
    
    total = (await db.execute(q_tot)).scalar() or 0
    active = (await db.execute(q_act)).scalar() or 0
    acknowledged = (await db.execute(q_ack)).scalar() or 0
    
    # Severity breakdown
    breakdown = {}
    for sev in AlertSeverity:
        q_sev = select(func.count(Alert.id)).where(Alert.severity == sev)
        breakdown[sev.value] = (await db.execute(q_sev)).scalar() or 0
        
    return {
        "total": total,
        "active_count": active,
        "acknowledged_count": acknowledged,
        "by_severity": breakdown
    }

@router.post("/{alert_id}/acknowledge", response_model=AlertResponse, summary="Acknowledge active alert")
async def acknowledge_alert(
    payload: AlertAcknowledge,
    alert_id: int = Path(..., description="The ID of the alert to acknowledge"),
    db: AsyncSession = Depends(get_db)
):
    alert = await db.get(Alert, alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
        
    alert.status = AlertStatus.ACKNOWLEDGED
    alert.acknowledged_at = datetime.utcnow()
    alert.acknowledged_by = payload.acknowledged_by
    # Store notes in metadata
    meta = dict(alert.metadata_json)
    meta["notes"] = payload.notes
    alert.metadata_json = meta
    
    await db.commit()
    await db.refresh(alert)
    return alert

@router.post("/{alert_id}/vlm-explain", response_model=AlertResponse, summary="Explain alert using VLM")
async def explain_alert_vlm(
    alert_id: int = Path(..., description="The ID of the alert to analyze"),
    db: AsyncSession = Depends(get_db)
):
    alert = await db.get(Alert, alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
        
    from app.services.vlm_service import VLMVerificationService
    import numpy as np
    
    # Instantiate VLM service
    vlm_service = VLMVerificationService()
    
    # Generate verification description using real screenshot if available
    import cv2
    import os
    
    screenshot_path = alert.metadata_json.get("screenshot_path")
    frame = None
    if screenshot_path and os.path.exists(screenshot_path):
        frame = cv2.imread(screenshot_path)
        
    if frame is None:
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        
    vlm_desc = await vlm_service.verify_frame(
        frame=frame,
        alert_type=alert.alert_type,
        zone_name=alert.zone_name or "Area"
    )
    
    # Update alert metadata with verification details
    meta = dict(alert.metadata_json)
    meta["vlm_description"] = vlm_desc
    meta["vlm_verified_at"] = datetime.utcnow().isoformat()
    alert.metadata_json = meta
    
    # Append the explanation to description
    if "VLM VERIFIED" not in alert.description:
        alert.description = f"{alert.description} — {vlm_desc}"
        
    await db.commit()
    await db.refresh(alert)
    return alert

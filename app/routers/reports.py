from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.reports import export_report

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/export")
def export_report_endpoint(
    format: Annotated[Literal["pdf", "xlsx"], Query()] = "xlsx",
    range: Annotated[Literal["daily", "weekly"], Query()] = "daily",
    db: Session = Depends(get_db),
):
    """Download a MineGuard report for the given range (daily|weekly)."""
    try:
        payload, filename, media = export_report(db, format, range)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return Response(
        content=payload,
        media_type=media,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
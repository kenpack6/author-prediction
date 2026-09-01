from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field

from author_prediction.server.dependencies import DbConn

router = APIRouter(prefix="/{project_id}/sources", tags=["sources"])


class SourceCreate(BaseModel):
    filename: str = Field(..., description="Filename of the source file")
    full_text: str = Field(..., description="Full text content of the source file")


class SourceListItemResponse(BaseModel):
    id: int
    filename: str
    processed_date: datetime | None = None
    project: int

    model_config = ConfigDict(from_attributes=True)


class SourceResponse(BaseModel):
    id: int
    filename: str
    full_text: str
    processed_date: datetime | None = None
    project: int

    model_config = ConfigDict(from_attributes=True)


@router.get("/", response_model=list[SourceListItemResponse])
async def list_sources(project_id: int, db: DbConn) -> list[dict[str, Any]]:
    """List all sources for a project without full_text."""
    rows = await db.fetch(
        "SELECT id, filename, processed_date, project FROM sources WHERE project = $1 ORDER BY id",
        project_id,
    )
    return [dict(row) for row in rows]


@router.post("/", response_model=SourceResponse, status_code=status.HTTP_201_CREATED)
async def create_source(project_id: int, source: SourceCreate, db: DbConn) -> dict[str, Any]:
    """Create a new source under a project."""
    row = await db.fetchrow(
        """
        INSERT INTO sources (filename, full_text, project)
        VALUES ($1, $2, $3)
        RETURNING id, filename, full_text, processed_date, project
        """,
        source.filename,
        source.full_text,
        project_id,
    )
    if not row:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create source")
    return dict(row)


@router.get("/{source_id}", response_model=SourceResponse)
async def get_source(project_id: int, source_id: int, db: DbConn) -> dict[str, Any]:
    """Get a source by ID under a project."""
    row = await db.fetchrow(
        "SELECT id, filename, full_text, processed_date, project FROM sources WHERE id = $1 AND project = $2",
        source_id,
        project_id,
    )
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source not found")
    return dict(row)


@router.delete("/{source_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_source(project_id: int, source_id: int, db: DbConn) -> None:
    """Delete a source by ID under a project."""
    result = await db.execute(
        "DELETE FROM sources WHERE id = $1 AND project = $2",
        source_id,
        project_id,
    )
    if result == "DELETE 0":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source not found")

from datetime import datetime

import asyncpg
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field

from author_prediction.server.dependencies import DbConn, Worker

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
    authors: list[int] = Field(default_factory=list, description="List of author IDs associated with the source")

    model_config = ConfigDict(from_attributes=True)


@router.get("/", response_model=list[SourceListItemResponse])
async def list_sources(project_id: int, db: DbConn) -> list[SourceListItemResponse]:
    """List all sources for a project without full_text."""
    rows = await db.fetch(
        "SELECT id, filename, processed_date, project FROM sources WHERE project = $1 ORDER BY id",
        project_id,
    )
    return [SourceListItemResponse.model_validate(dict(row)) for row in rows]


@router.post("/", response_model=SourceResponse, status_code=status.HTTP_201_CREATED)
async def create_source(project_id: int, source: SourceCreate, db: DbConn, worker: Worker) -> SourceResponse:
    """Create a new source under a project."""
    try:
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
    except asyncpg.UniqueViolationError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A source with this content already exists",
        )

    if not row:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create source")
    worker.put(row['id'], row['project'])
    result = dict(row)
    result["authors"] = []
    return SourceResponse.model_validate(result)


@router.get("/{source_id}", response_model=SourceResponse)
async def get_source(project_id: int, source_id: int, db: DbConn) -> SourceResponse:
    """Get a source by ID under a project with associated authors."""
    row = await db.fetchrow(
        """
        SELECT s.id, s.filename, s.full_text, s.processed_date, s.project,
               COALESCE(
                   ARRAY(SELECT sa.author FROM source_authors sa WHERE sa.source = s.id ORDER BY sa.author),
                   ARRAY[]::int[]
               ) AS authors
        FROM sources s
        WHERE s.id = $1 AND s.project = $2
        """,
        source_id,
        project_id,
    )
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source not found")
    return SourceResponse.model_validate(dict(row))

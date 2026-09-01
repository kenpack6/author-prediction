from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, ConfigDict

from author_prediction.server.dependencies import DbConn

router = APIRouter(prefix="/{project_id}/authors", tags=["authors"])


class AuthorResponse(BaseModel):
    id: int
    sources: int = 0

    model_config = ConfigDict(from_attributes=True)


@router.get("/", response_model=list[AuthorResponse])
async def list_authors(project_id: int, db: DbConn) -> list[AuthorResponse]:
    """List all authors for a project with sources count."""
    rows = await db.fetch(
        """
        SELECT a.id, COUNT(sa.source)::int AS sources
        FROM authors a
        LEFT JOIN source_authors sa ON sa.author = a.id
        WHERE a.project = $1
        GROUP BY a.id
        ORDER BY a.id
        """,
        project_id,
    )
    return [AuthorResponse.model_validate(dict(row)) for row in rows]


@router.get("/{author_id}", response_model=AuthorResponse)
async def get_author(project_id: int, author_id: int, db: DbConn) -> AuthorResponse:
    """Get an author by ID under a project with sources count."""
    row = await db.fetchrow(
        """
        SELECT a.id, COUNT(sa.source)::int AS sources
        FROM authors a
        LEFT JOIN source_authors sa ON sa.author = a.id
        WHERE a.project = $1 AND a.id = $2
        GROUP BY a.id
        """,
        project_id,
        author_id,
    )
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Author not found")
    return AuthorResponse.model_validate(dict(row))

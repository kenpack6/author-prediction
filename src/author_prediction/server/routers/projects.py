from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field

from author_prediction.server.dependencies import DbConn

router = APIRouter(prefix="/projects", tags=["projects"])


class ProjectCreate(BaseModel):
    name: str = Field(..., description="Name of the project")


class ProjectUpdate(BaseModel):
    name: str = Field(..., description="Updated name of the project")


class ProjectResponse(BaseModel):
    id: int
    name: str

    model_config = ConfigDict(from_attributes=True)


@router.get("/", response_model=list[ProjectResponse])
async def list_projects(db: DbConn) -> list[dict[str, Any]]:
    """List all projects."""
    rows = await db.fetch("SELECT id, name FROM projects ORDER BY id")
    return [dict(row) for row in rows]


@router.post("/", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(project: ProjectCreate, db: DbConn) -> dict[str, Any]:
    """Create a new project."""
    row = await db.fetchrow(
        "INSERT INTO projects (name) VALUES ($1) RETURNING id, name",
        project.name,
    )
    if not row:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create project")
    return dict(row)


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: int, db: DbConn) -> dict[str, Any]:
    """Get a project by ID."""
    row = await db.fetchrow(
        "SELECT id, name FROM projects WHERE id = $1",
        project_id,
    )
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return dict(row)


@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: int, project_update: ProjectUpdate, db: DbConn
) -> dict[str, Any]:
    """Update a project by ID."""
    row = await db.fetchrow(
        """
        UPDATE projects
        SET name = $1
        WHERE id = $2
        RETURNING id, name
        """,
        project_update.name,
        project_id,
    )
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return dict(row)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(project_id: int, db: DbConn) -> None:
    """Delete a project by ID."""
    result = await db.execute("DELETE FROM projects WHERE id = $1", project_id)
    if result == "DELETE 0":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

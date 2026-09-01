from author_prediction.server.routers.authors import router as authors_router
from author_prediction.server.routers.projects import router as projects_router
from author_prediction.server.routers.sources import router as sources_router

__all__ = ["authors_router", "projects_router", "sources_router"]

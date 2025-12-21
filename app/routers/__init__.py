from .upload import router as upload_router
from .cleaning import router as cleaning_router
from .insights import router as insights_router
from .charts import router as charts_router
from .ml import router as ml_router
from .export import router as export_router
from .preview import router as preview_router
from .auth import router as auth_router

__all__ = [
    "upload_router",
    "cleaning_router",
    "insights_router",
    "charts_router",
    "ml_router",
    "export_router",
    "preview_router",
    "auth_router"
]

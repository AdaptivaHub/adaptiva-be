from fastapi import APIRouter
from fastapi.responses import FileResponse
from app.models import ExportRequest, ErrorResponse
from app.services import export_data

router = APIRouter(prefix="/export", tags=["Export"])


@router.post(
    "/",
    response_class=FileResponse,
    responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
    summary="Export data",
    description="Export data and insights to PDF or PowerPoint format"
)
def export_file(request: ExportRequest):
    """
    Export dataset and insights to PDF or PPTX format.
    
    - **file_id**: The file identifier returned from upload
    - **export_format**: Format to export (pdf or pptx)
    - **include_insights**: Include data insights in export
    - **include_charts**: Include charts in export (future feature)
    - **chart_configs**: Chart configurations for export (future feature)
    
    Returns the exported file for download.
    """
    filepath = export_data(request)
    filename = filepath.split("/")[-1]
    
    media_type = "application/pdf" if request.export_format.value == "pdf" else "application/vnd.openxmlformats-officedocument.presentationml.presentation"
    
    return FileResponse(
        path=filepath,
        media_type=media_type,
        filename=filename
    )

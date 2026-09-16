from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.core.config import settings
from app.api.translate import router as translate_router
from app.api.watermark import router as watermark_router

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description=settings.DESCRIPTION,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# Configure CORS for Flutter client & browser access
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(translate_router, prefix=settings.API_PREFIX, tags=["PDF Translation"])
app.include_router(watermark_router, prefix="", tags=["PDF Watermark"])

@app.get("/", tags=["General"])
async def root():
    """API overview and links."""
    return {
        "project": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "status": "online",
        "documentation": "/docs",
        "endpoints": {
            "translate_pdf": "POST /api/translate-pdf",
            "watermark_pdf": "POST /editor/pdf/watermark"
        }
    }

@app.get("/health", tags=["General"])
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": settings.PROJECT_NAME}

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Fallback handler for unhandled exceptions to maintain JSON error response standard."""
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": f"An unexpected server error occurred: {str(exc)}"}
    )

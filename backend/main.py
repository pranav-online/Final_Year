from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from routes.auth import router as auth_router
from routes.disease import router as disease_router
from routes.weather import router as weather_router
from routes.crop import router as crop_router
from routes.market import router as market_router
from routes.notifications import router as notifications_router
from routes.region_routes import router as region_router
from routes.mandi_routes import router as mandi_router
from services.mandi.scheduler import start_scheduler, shutdown_scheduler
from config.database import ping_database
from pymongo.errors import PyMongoError
from contextlib import asynccontextmanager


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Daily mandi ingestion; set SCHEDULER_ENABLED=0 on all but one worker.
    start_scheduler()
    yield
    shutdown_scheduler()


app = FastAPI(
    title="ALIP - AgriLink Intelligence Platform",
    description="AI-Based Agricultural Decision Support System",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router)
app.include_router(disease_router)
app.include_router(weather_router)
app.include_router(crop_router)
# Before market_router: its /market/demand/{region} would otherwise capture
# fixed paths like /market/demand/overview.
app.include_router(mandi_router)
app.include_router(market_router)
app.include_router(notifications_router)
app.include_router(region_router, prefix="/market",
                   tags=["regions"])

@app.get("/")
async def root():
    return {
        "message": "Welcome to ALIP API",
        "status": "running"
    }

@app.get("/health/database")
async def database_health():
    try:
        await ping_database()
        return {"database": "connected"}
    except PyMongoError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection unavailable"
        ) from None

# app/main.py

from dotenv import load_dotenv
import os
import psycopg2

# Load env variables
load_dotenv()

import logging
from contextlib import asynccontextmanager
from fastapi import Depends, FastAPI, HTTPException
from fastapi.security import api_key

from .engine import RecommendationEngine
from .schemas import RecommendationRequest, RecommendationResponse
from .security import get_api_key

# --- App Configuration ---
logging.basicConfig(level=logging.INFO)

# --- Lifespan Event Handler ---
lifespan_context = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Code here runs on startup
    logging.info("Initializing recommendation engine...")
    try:
        lifespan_context["engine"] = RecommendationEngine()
        logging.info("Engine initialized successfully.")
    except Exception as e:
        logging.critical(f"Engine initialization failed: {e}")
        lifespan_context["engine"] = None
    
    yield
    
    # Code here runs on shutdown
    logging.info("Shutting down...")
    lifespan_context.clear()


app = FastAPI(
    title="Synapse Recommendation Service",
    description="A microservice for providing skill-based engineer recommendations.",
    version="1.0.0",
    lifespan=lifespan
)


# --- API Endpoints ---

@app.get("/health", status_code=200)
def health_check():
    """
    Checks the status of the service, including the recommendation model
    and the database connection.
    """
    engine = lifespan_context.get("engine")
    model_ready = bool(engine and engine.model)
    db_ok = False
    db_error = "Not checked"

    try:
        db_url = os.getenv("DATABASE_URL")
        if not db_url:
            raise ValueError("DATABASE_URL environment variable not set.")
        
        # Try to connect to the database
        conn = psycopg2.connect(db_url)
        # Run a simple query to ensure the connection is live
        conn.cursor().execute("SELECT 1")
        conn.close()
        db_ok = True
        db_error = None

    except Exception as e:
        logging.error(f"Database health check failed: {e}")
        db_error = str(e)
        db_ok = False

    if model_ready and db_ok:
        return {
            "status": "ok",
            "details": {"model_ready": True, "database_connected": True},
        }
    else:
        # Return a 503 Service Unavailable status if anything is wrong
        raise HTTPException(
            status_code=503,
            detail={
                "status": "degraded",
                "details": {
                    "model_ready": model_ready,
                    "database_connected": db_ok,
                    "database_error": db_error,
                },
            },
        )

@app.post("/recommend", response_model=RecommendationResponse)
async def recommend_engineers(
    request: RecommendationRequest,
    api_key: str = Depends(get_api_key)  
):
    """
    Accepts a list of required skill IDs and returns a ranked list of
    recommended engineers.
    """
    engine = lifespan_context.get("engine")
    if not engine or not engine.model:
        raise HTTPException(
            status_code=503, 
            detail="Recommendation engine is not available or failed to initialize."
        )

    recommendations = engine.get_recommendations(
        skill_ids=request.skill_ids,
        limit=request.limit
    )

    if not recommendations:
        return {"recommendations": []}

    return {"recommendations": recommendations}

@app.post("/refresh-model", status_code=202)
async def trigger_model_refresh(api_key: str = Depends(get_api_key)):
    """
    Triggers a refresh of the recommendation model.
    """
    engine = lifespan_context.get("engine")
    if not engine:
        raise HTTPException(
            status_code=503,
            detail="Recommendation engine is not available."
        )
    
    try:
        engine.refresh_model()
        return {"status": "accepted", "message": "Model refresh initiated."}
    except Exception as e:
        logging.error(f"Failed to trigger model refresh: {e}")
        raise HTTPException(
            status_code=500,
            detail="An error occurred while refreshing the model."
        )

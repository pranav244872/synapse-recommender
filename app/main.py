# app/main.py

from dotenv import load_dotenv

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
# This dictionary will hold our long-lived engine instance.
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
    
    yield # The application runs while the lifespan block is yielded
    
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
    """Simple health check to confirm the service is running."""
    engine = lifespan_context.get("engine")
    if engine and engine.model:
        return {"status": "ok", "model_ready": True}
    return {"status": "degraded", "model_ready": False}


@app.post("/recommend", response_model=RecommendationResponse)
async def recommend_engineers(
    request: RecommendationRequest,
    api_key: str = Depends(get_api_key)    
):
    """
    Accepts a list of required skill IDs and returns a ranked list of
    recommended engineers.

    This endpoint is protected and requires a Valid API Key
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
    This should be called by other internal services (e.g., the user service)
    after a new user is created or a task is completed.
    """
    engine = lifespan_context.get("engine")
    if not engine:
        raise HTTPException(
            status_code=503,
            detail="Recommendation engine is not available."
        )
    
    try:
        # In a production system, you might run this in the background
        # to avoid blocking the API response.
        engine.refresh_model()
        return {"status": "accepted", "message": "Model refresh initiated."}
    except Exception as e:
        logging.error(f"Failed to trigger model refresh: {e}")
        raise HTTPException(
            status_code=500,
            detail="An error occurred while refreshing the model."
        )

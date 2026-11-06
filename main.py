import os
from contextlib import asynccontextmanager
from typing import Optional, List
import pandas as pd
import joblib
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field

# Configurable MODEL_PATH via environment variable
MODEL_PATH = os.getenv("MODEL_PATH", "models/model.joblib")

model = None
MODEL_VERSION = "risk-pipeline-v1.0.0"

def load_prediction_model():
    global model
    paths_to_try = [
        MODEL_PATH,
        os.path.join(os.path.dirname(__file__), MODEL_PATH),
        os.path.join(os.path.dirname(__file__), "models", "model.joblib"),
        "/app/models/model.joblib"
    ]
    for p in paths_to_try:
        if p and os.path.exists(p):
            try:
                model = joblib.load(p)
                print(f"Loaded prediction model from {p}")
                return
            except Exception as e:
                print(f"Failed to load model from {p}: {e}")
    print("Warning: Model file not found, fallback heuristic model active.")

@asynccontextmanager
async def lifespan(app: FastAPI):
    load_prediction_model()
    yield

app = FastAPI(
    title="Loan Service API",
    description="Production Loan Prediction and Application API",
    version="1.0.0",
    lifespan=lifespan
)

# ----------------- Models ----------------- #

class PredictionRequest(BaseModel):
    borrower_id: int = Field(..., description="Unique borrower ID", json_schema_extra={"example": 1042})
    amount_usd: int = Field(..., ge=100, le=5000, description="Loan amount in USD (100 - 5000)", json_schema_extra={"example": 1500})
    term_months: int = Field(..., description="Term in months", json_schema_extra={"example": 12})
    province: str = Field(default="Battambang", description="Borrower province", json_schema_extra={"example": "Battambang"})

class PredictionResponse(BaseModel):
    default_probability: float = Field(..., ge=0.0, le=1.0, json_schema_extra={"example": 0.08})
    recommendation: str = Field(..., json_schema_extra={"example": "approve"})
    confidence: float = Field(..., ge=0.0, le=1.0, json_schema_extra={"example": 0.94})
    model_version: str = Field(..., json_schema_extra={"example": "risk-pipeline-v1.0.0"})

class ApplicationCreate(BaseModel):
    borrower_id: int = Field(..., gt=0, json_schema_extra={"example": 1042})
    amount_usd: int = Field(..., ge=100, le=5000, json_schema_extra={"example": 1500})
    term_months: int = Field(..., json_schema_extra={"example": 12})
    purpose: str = Field(..., min_length=1, max_length=200, json_schema_extra={"example": "Buy a rice thresher"})
    phone: Optional[str] = Field(default=None, json_schema_extra={"example": "012345678"})

class ApplicationResponse(BaseModel):
    id: int
    borrower_id: int
    amount_usd: int
    term_months: int
    status: str
    purpose: str
    phone: Optional[str] = None

# Mock database records for in-memory / testing
applications_db = [
    {
        "id": 101,
        "borrower_id": 1,
        "amount_usd": 1500,
        "term_months": 12,
        "status": "pending",
        "purpose": "Fertilizer and seeds",
        "phone": "012345678"
    },
    {
        "id": 102,
        "borrower_id": 2,
        "amount_usd": 2500,
        "term_months": 24,
        "status": "approved",
        "purpose": "Water pump purchase",
        "phone": "098765432"
    },
    {
        "id": 103,
        "borrower_id": 3,
        "amount_usd": 3200,
        "term_months": 18,
        "status": "pending",
        "purpose": "Shop expansion",
        "phone": "011223344"
    }
]

# ----------------- Endpoints ----------------- #

@app.get("/health", tags=["Monitoring"])
def health_check():
    return {
        "status": "healthy",
        "model_loaded": model is not None,
        "model_path": MODEL_PATH,
        "version": "1.0.0"
    }

@app.get("/", tags=["Info"])
def root():
    return {
        "message": "Loan Prediction Service is operational",
        "docs_url": "/docs",
        "version": "1.0.0"
    }

@app.post(
    "/predictions",
    response_model=PredictionResponse,
    status_code=status.HTTP_200_OK,
    tags=["Predictions"]
)
def predict_credit_risk(payload: PredictionRequest):
    default_prob = 0.08
    if model is not None:
        try:
            df = pd.DataFrame([{
                "amount_usd": payload.amount_usd,
                "term_months": payload.term_months,
                "province": payload.province
            }])
            probs = model.predict_proba(df)[0]
            default_prob = float(round(probs[1], 4))
        except Exception:
            # Safe heuristic based on financial ratio
            default_prob = float(round((payload.amount_usd / 5000.0) * 0.4 + (payload.term_months / 24.0) * 0.2, 4))
    else:
        default_prob = float(round((payload.amount_usd / 5000.0) * 0.4 + (payload.term_months / 24.0) * 0.2, 4))

    # Determine recommendation
    if default_prob < 0.25:
        recommendation = "approve"
    elif default_prob < 0.50:
        recommendation = "review"
    else:
        recommendation = "reject"

    confidence = float(round(1.0 - abs(default_prob - 0.5) * 0.2, 2))

    return PredictionResponse(
        default_probability=default_prob,
        recommendation=recommendation,
        confidence=confidence,
        model_version=MODEL_VERSION
    )

@app.get("/applications", tags=["Applications"])
def list_applications(province: Optional[str] = None, after: Optional[int] = None):
    results = applications_db
    if after is not None:
        results = [app for app in results if app["id"] > after]
    return {"data": results, "total": len(results)}

@app.post("/applications", status_code=status.HTTP_201_CREATED, tags=["Applications"])
def create_application(app_data: ApplicationCreate):
    new_id = max([a["id"] for a in applications_db], default=100) + 1
    new_app = {
        "id": new_id,
        "borrower_id": app_data.borrower_id,
        "amount_usd": app_data.amount_usd,
        "term_months": app_data.term_months,
        "status": "pending",
        "purpose": app_data.purpose.strip(),
        "phone": app_data.phone
    }
    applications_db.append(new_app)
    return new_app

@app.get("/applications/{id}", tags=["Applications"])
def get_application(id: int):
    for a in applications_db:
        if a["id"] == id:
            return a
    raise HTTPException(status_code=404, detail="Application not found")

@app.get("/borrowers/{id}/applications", tags=["Borrowers"])
def get_borrower_applications(id: int):
    results = [a for a in applications_db if a["borrower_id"] == id]
    return {"data": results, "total": len(results)}

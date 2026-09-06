from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.api.routes import cases

app = FastAPI(
    title="Medical Surgery Planner API",
    description="Bridge between React frontend and Python medical-imaging pipeline.",
    version="1.0.0"
)

# CORS configuration
# Allowing localhost:5173 (default Vite) and some common alternative ports
origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(cases.router)

@app.get("/api/health")
async def health_check():
    """Health check endpoint to verify backend is running."""
    return {"status": "ok"}

"""Main FastAPI application entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from contramate.api.interfaces.controllers.root_controller import router as root_router
from contramate.api.interfaces.controllers.chat_controller import router as chat_router
from contramate.api.interfaces.controllers.status_controller import router as status_router
from contramate.api.interfaces.controllers.contracts_controller import router as contracts_router
from contramate.api.interfaces.controllers.conversations_controller import router as conversations_router


app = FastAPI(
    title="Contramate API",
    description="A Conversational AI Agent Application for Contract Understanding using CUAD Dataset",
    version="0.1.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8501"],  # Next.js frontend + Streamlit
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(root_router)
app.include_router(chat_router)
app.include_router(status_router)
app.include_router(contracts_router)
app.include_router(conversations_router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
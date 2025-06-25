"""
FastAPI application entry point.
"""

from fastapi import FastAPI

app = FastAPI(
    title="Octopus API",
    description="A FastAPI application for the Octopus project",
    version="0.1.0"
)

@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "Hello World from Octopus!"}

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

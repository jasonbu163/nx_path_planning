# run.py
from app.main import app

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8765,
        workers=1,
        # loop="asyncio",
        timeout_keep_alive=30,
        limit_concurrency=15,
        reload=True
    )
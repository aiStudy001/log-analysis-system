"""
Application entry point
"""
from app import create_app

app = create_app()


if __name__ == "__main__":
    import uvicorn
    from app.config import settings

    uvicorn.run(
        app,
        host=settings.SERVER_HOST,
        port=settings.SERVER_PORT
    )

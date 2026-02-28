"""Run the application with uvicorn."""

import uvicorn

from src.configs.settings import get_instance

if __name__ == "__main__":
    settings = get_instance()
    uvicorn.run(
        "src.app:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
    )

import uvicorn
from tasmota_sim.web_server import app

def main():
    """Run the FastAPI web server."""
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=80,
        log_level="info"
    )

if __name__ == "__main__":
    main() 
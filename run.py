import os
from backend.app import create_app
from dotenv import load_dotenv
from waitress import serve

load_dotenv()

app = create_app()

if __name__ == '__main__':
    port = os.getenv("BACKEND_API")
    print(f"🚀 Starting Waitress Server on http://0.0.0.0:5001")
    serve(app, host='0.0.0.0', port=5001, threads=6)

import os
from backend.app import create_app
from dotenv import load_dotenv
from waitress import serve


load_dotenv()

app = create_app()

if __name__ == '__main__':
    port = int(os.getenv("BACKEND_API"))
    print(f"🚀 Starting Waitress Server on http://0.0.0.0:{port}")
    serve(app, host='0.0.0.0', port=port, threads=6)

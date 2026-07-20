# api/health.py
# Vercel endpoint: GET /api/health
# Preveri ali je Loom API živ in katera verzija teče.

from http.server import BaseHTTPRequestHandler
import json
from datetime import datetime, timezone


class handler(BaseHTTPRequestHandler):

    def do_GET(self):
        response = {
            "status": "ok",
            "service": "Loom",
            "version": "0.1.0",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(response).encode())

    def log_message(self, format, *args):
        pass  # tiho — Vercel ima lasten logging

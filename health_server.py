#!/usr/bin/env python3
"""
Health Check Server for Vocare Restaurant Assistant
Provides /health and /ready endpoints for Kubernetes health checks
"""

import asyncio
import json
import logging
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
from typing import Dict, Any

logger = logging.getLogger(__name__)

class HealthStatus:
    """Tracks the health status of the application"""

    def __init__(self):
        self.start_time = time.time()
        self.ready = False
        self.healthy = True
        self.checks = {}

    def set_ready(self, ready: bool = True):
        """Mark the application as ready to serve traffic"""
        self.ready = ready
        logger.info(f"Application ready status: {ready}")

    def set_healthy(self, healthy: bool = True):
        """Mark the application as healthy"""
        self.healthy = healthy
        logger.info(f"Application health status: {healthy}")

    def add_check(self, name: str, status: bool, message: str = ""):
        """Add a health check result"""
        self.checks[name] = {
            "status": status,
            "message": message,
            "timestamp": time.time()
        }

    def get_status(self) -> Dict[str, Any]:
        """Get the current status"""
        uptime = time.time() - self.start_time
        return {
            "status": "healthy" if self.healthy else "unhealthy",
            "ready": self.ready,
            "uptime_seconds": round(uptime, 2),
            "timestamp": time.time(),
            "checks": self.checks,
            "service": "vocare-restaurant-assistant",
            "version": "1.0.0"
        }

# Global health status instance
health_status = HealthStatus()

class HealthHandler(BaseHTTPRequestHandler):
    """HTTP handler for health check endpoints"""

    def log_message(self, format, *args):
        """Override to use our logger"""
        logger.debug(f"Health check: {format % args}")

    def do_GET(self):
        """Handle GET requests"""
        if self.path == "/health":
            self.handle_health()
        elif self.path == "/ready":
            self.handle_ready()
        elif self.path == "/":
            self.handle_root()
        else:
            self.send_error(404, "Not Found")

    def handle_health(self):
        """Handle /health endpoint"""
        status = health_status.get_status()

        if health_status.healthy:
            self.send_response(200)
        else:
            self.send_response(503)

        self.send_header('Content-Type', 'application/json')
        self.end_headers()

        response = json.dumps(status, indent=2)
        self.wfile.write(response.encode())

    def handle_ready(self):
        """Handle /ready endpoint"""
        if health_status.ready:
            self.send_response(200)
            response = {"status": "ready", "message": "Application is ready to serve traffic"}
        else:
            self.send_response(503)
            response = {"status": "not_ready", "message": "Application is not ready"}

        self.send_header('Content-Type', 'application/json')
        self.end_headers()

        self.wfile.write(json.dumps(response).encode())

    def handle_root(self):
        """Handle / endpoint"""
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()

        response = {
            "service": "vocare-restaurant-assistant",
            "status": "running",
            "endpoints": ["/health", "/ready"]
        }
        self.wfile.write(json.dumps(response).encode())

class HealthServer:
    """Health check server that runs in a separate thread"""

    def __init__(self, port: int = 8000):
        self.port = port
        self.server = None
        self.thread = None
        self.running = False

    def start(self):
        """Start the health server in a separate thread"""
        if self.running:
            logger.warning("Health server is already running")
            return

        try:
            self.server = HTTPServer(('0.0.0.0', self.port), HealthHandler)
            self.thread = threading.Thread(target=self._run_server, daemon=True)
            self.thread.start()
            self.running = True
            logger.info(f"Health server started on port {self.port}")

            # Mark as ready after a short delay
            threading.Timer(2.0, lambda: health_status.set_ready(True)).start()

        except Exception as e:
            logger.error(f"Failed to start health server: {e}")
            health_status.set_healthy(False)

    def _run_server(self):
        """Run the HTTP server"""
        try:
            self.server.serve_forever()
        except Exception as e:
            logger.error(f"Health server error: {e}")
            health_status.set_healthy(False)

    def stop(self):
        """Stop the health server"""
        if self.server:
            self.server.shutdown()
            self.server.server_close()

        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=5)

        self.running = False
        logger.info("Health server stopped")

# Global health server instance
health_server = HealthServer()

def start_health_server(port: int = 8000):
    """Start the health check server"""
    global health_server
    health_server = HealthServer(port)
    health_server.start()
    return health_server

def stop_health_server():
    """Stop the health check server"""
    global health_server
    if health_server:
        health_server.stop()

def set_ready(ready: bool = True):
    """Mark the application as ready"""
    health_status.set_ready(ready)

def set_healthy(healthy: bool = True):
    """Mark the application as healthy"""
    health_status.set_healthy(healthy)

def add_health_check(name: str, status: bool, message: str = ""):
    """Add a health check result"""
    health_status.add_check(name, status, message)
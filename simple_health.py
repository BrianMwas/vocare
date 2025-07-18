#!/usr/bin/env python3
"""
Simple health check script for Docker health checks
This is a lightweight alternative that doesn't interfere with the main application
"""

import sys
import socket
import time
import json
import os

def check_port(host, port, timeout=5):
    """Check if a port is open"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except Exception:
        return False

def check_health():
    """Perform health checks"""
    health_status = {
        "status": "healthy",
        "timestamp": time.time(),
        "checks": {}
    }

    # Check if LiveKit agent port is responding
    if check_port("localhost", 8081):
        health_status["checks"]["livekit_agent"] = {"status": True, "message": "LiveKit agent port responding"}
    else:
        health_status["checks"]["livekit_agent"] = {"status": False, "message": "LiveKit agent port not responding"}
        health_status["status"] = "unhealthy"

    # Check if health server port is responding (if running)
    if check_port("localhost", 8000):
        health_status["checks"]["health_server"] = {"status": True, "message": "Health server responding"}
    else:
        health_status["checks"]["health_server"] = {"status": False, "message": "Health server not responding"}

    # Check if process has been running for a reasonable time (startup grace period)
    uptime_file = "/tmp/app_start_time"
    if os.path.exists(uptime_file):
        with open(uptime_file, 'r') as f:
            start_time = float(f.read().strip())
        uptime = time.time() - start_time
        health_status["uptime_seconds"] = uptime

        if uptime < 30:  # 30 second grace period
            health_status["checks"]["startup"] = {"status": True, "message": f"Startup grace period: {uptime:.1f}s"}
        else:
            health_status["checks"]["startup"] = {"status": True, "message": "Application started successfully"}
    else:
        # Create the uptime file
        with open(uptime_file, 'w') as f:
            f.write(str(time.time()))
        health_status["checks"]["startup"] = {"status": True, "message": "Application starting"}

    return health_status

def main():
    """Main health check function"""
    try:
        health = check_health()

        if len(sys.argv) > 1 and sys.argv[1] == "--json":
            print(json.dumps(health, indent=2))

        if health["status"] == "healthy":
            sys.exit(0)
        else:
            sys.exit(1)

    except Exception as e:
        print(f"Health check error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
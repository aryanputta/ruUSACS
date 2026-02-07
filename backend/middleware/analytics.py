import time
import json
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from config.db import get_db_connection
from config.settings import settings

class AnalyticsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if not settings.analytics_enabled:
            return await call_next(request)
            
        start_time = time.time()
        
        # Process the request
        try:
            response = await call_next(request)
            duration = time.time() - start_time
            
            # Log successful request
            self._log_event("request_success", {
                "method": request.method,
                "url": str(request.url),
                "status_code": response.status_code,
                "duration_ms": int(duration * 1000)
            })
            
            return response
        except Exception as e:
            duration = time.time() - start_time
            # Log failed request
            self._log_event("request_failure", {
                "method": request.method,
                "url": str(request.url),
                "error": str(e),
                "duration_ms": int(duration * 1000)
            })
            raise e

    def _log_event(self, event_type: str, data: dict):
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO analytics_events (event_type, data) VALUES (?, ?)",
                (event_type, json.dumps(data))
            )
            conn.commit()
            conn.close()
        except Exception as ex:
            print(f"[ANALYTICS ERROR] Failed to log event: {ex}")

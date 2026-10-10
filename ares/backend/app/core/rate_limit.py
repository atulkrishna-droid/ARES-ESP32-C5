"""In-memory rate limiting for sensitive endpoints."""
import time
from collections import defaultdict
from typing import Dict, List
from fastapi import HTTPException, Request, status


class SimpleRateLimiter:
    def __init__(self, requests_per_minute: int = 30):
        self.rpm = requests_per_minute
        self.requests: Dict[str, List[float]] = defaultdict(list)

    def check_rate_limit(self, key: str) -> None:
        now = time.time()
        window_start = now - 60.0

        # Purge timestamps older than 60s
        self.requests[key] = [t for t in self.requests[key] if t > window_start]

        if len(self.requests[key]) >= self.rpm:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded. Maximum {self.rpm} requests per minute.",
                headers={"Retry-After": "60"},
            )

        self.requests[key].append(now)


auth_limiter = SimpleRateLimiter(requests_per_minute=20)
enroll_limiter = SimpleRateLimiter(requests_per_minute=30)


def rate_limit_auth(request: Request) -> None:
    client_ip = request.client.host if request.client else "127.0.0.1"
    auth_limiter.check_rate_limit(f"auth:{client_ip}")


def rate_limit_enrollment(request: Request) -> None:
    client_ip = request.client.host if request.client else "127.0.0.1"
    enroll_limiter.check_rate_limit(f"enroll:{client_ip}")

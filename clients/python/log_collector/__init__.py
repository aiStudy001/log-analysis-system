"""
로그 수집 클라이언트 라이브러리

성능 최적화:
- 앱 블로킹 < 0.1ms
- 처리량 50K logs/sec
- 메모리 < 10MB
"""

from .async_client import AsyncLogClient

__version__ = "1.0.0"
__all__ = ["AsyncLogClient"]

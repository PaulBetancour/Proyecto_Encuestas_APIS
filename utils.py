from __future__ import annotations

import functools
import inspect
import logging
import time
from typing import Any, Callable

logger = logging.getLogger("encuesta_api")


def log_request(handler: Callable[..., Any]) -> Callable[..., Any]:
    """
    Decorador personalizado para registrar metodo/ruta y tiempo.
    Conceptualmente es similar a @app.get/@app.post: ambos envuelven
    una funcion para agregar comportamiento adicional.
    """

    signature = inspect.signature(handler)

    def _extract_request(*args: Any, **kwargs: Any) -> Any:
        bound = signature.bind_partial(*args, **kwargs)
        return bound.arguments.get("request")

    if inspect.iscoroutinefunction(handler):

        @functools.wraps(handler)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            request = _extract_request(*args, **kwargs)
            method = getattr(request, "method", "N/A")
            path = getattr(request, "url", None)
            path_text = str(path.path) if path else "N/A"

            start = time.perf_counter()
            result = await handler(*args, **kwargs)
            elapsed = (time.perf_counter() - start) * 1000
            logger.info("%s %s procesada en %.2f ms", method, path_text, elapsed)
            return result

        async_wrapper.__signature__ = signature
        return async_wrapper

    @functools.wraps(handler)
    def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
        request = _extract_request(*args, **kwargs)
        method = getattr(request, "method", "N/A")
        path = getattr(request, "url", None)
        path_text = str(path.path) if path else "N/A"

        start = time.perf_counter()
        result = handler(*args, **kwargs)
        elapsed = (time.perf_counter() - start) * 1000
        logger.info("%s %s procesada en %.2f ms", method, path_text, elapsed)
        return result

    sync_wrapper.__signature__ = signature
    return sync_wrapper

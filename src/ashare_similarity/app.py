from __future__ import annotations

from pathlib import Path
import re

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from ashare_similarity import runtime as runtime_module
from ashare_similarity.config import get_default_config
from ashare_similarity.search.response_cache import PredictionResponseCache, SearchResponseCache
from ashare_similarity.web.routes import router as web_router


def _static_dir() -> Path:
    package_dir = Path(__file__).resolve().parent
    return package_dir / "static"


def _translate_validation_message(message: str) -> str:
    if message == "Field required":
        return "该字段为必填项"
    if message == "Input should be a valid integer":
        return "请输入有效整数"
    if message == "Input should be a valid date":
        return "请输入有效日期"
    if message == "Input should be a valid datetime":
        return "请输入有效日期时间"

    lower_bound = re.match(r"Input should be greater than or equal to (.+)", message)
    if lower_bound:
        return f"输入值必须大于或等于 {lower_bound.group(1)}"

    upper_bound = re.match(r"Input should be less than or equal to (.+)", message)
    if upper_bound:
        return f"输入值必须小于或等于 {upper_bound.group(1)}"

    return message


def create_app() -> FastAPI:
    config = get_default_config()
    app = FastAPI(title="A股K线相似检索系统")
    app.state.runtime = runtime_module.get_runtime()
    app.state.app_config = config
    app.state.search_response_cache = SearchResponseCache()
    app.state.prediction_response_cache = PredictionResponseCache()
    static_dir = _static_dir()
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        del request
        messages: list[str] = []
        for error in exc.errors():
            location = " -> ".join(str(item) for item in error.get("loc", []) if item not in {"body", "query"})
            translated = _translate_validation_message(str(error.get("msg", "请求参数不合法")))
            messages.append(f"{location}: {translated}" if location else translated)
        detail = "请求参数校验失败"
        if messages:
            detail = f"{detail}：{'；'.join(messages)}"
        return JSONResponse(status_code=422, content={"detail": detail})

    app.include_router(web_router)
    return app

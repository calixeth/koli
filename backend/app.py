import logging
import os
import time
from contextlib import asynccontextmanager

import fastapi
import uvicorn
from agents import set_default_openai_key
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import ORJSONResponse
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from starlette.responses import JSONResponse

from common.log import setup_logger
from common.response import RestResponse
from common.tracing import Otel
from config import SETTINGS
from middleware.auth_middleware import JWTAuthMiddleware
from middleware.trace_middleware import TraceIdMiddleware
from routes import api_router, voice_router, auth_router, twitter_tts_router

# from services.twitter_tts_processor import start_twitter_tts_processor, stop_twitter_tts_processor

Otel.init()
setup_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logging.info("Starting lifespan")
    yield
    logging.info("Stopping lifespan")


#     await start_twitter_tts_processor()
#     logger.info("Twitter TTS background processor started successfully")
#     yield
#     await stop_twitter_tts_processor()
#     logger.info("Twitter TTS background processor stopped successfully")
#

logger = logging.getLogger(__name__)
app = FastAPI(lifespan=lifespan)
FastAPIInstrumentor.instrument_app(app)
app.add_middleware(JWTAuthMiddleware)
app.add_middleware(TraceIdMiddleware)
app.include_router(api_router.router)
app.include_router(voice_router.router)
app.include_router(auth_router.router)
# Include Twitter TTS router
app.include_router(twitter_tts_router.router, tags=["Twitter TTS"])


@app.get("/openapi.json", include_in_schema=False)
def custom_openapi():
    """
    http://127.0.0.1:8080/openapi.json
    """
    return JSONResponse(content=app.openapi())


@app.exception_handler(Exception)
async def default_exception_handler(request: fastapi.Request, exc: Exception):
    """"""
    logger.error("M default_exc_handler", exc_info=True)
    resp = ORJSONResponse(
        RestResponse(code=500, msg=str(exc)).model_dump(),
        status_code=200
    )

    tid = Otel.get_tid()
    if tid:
        resp.headers["X-Trace-Id"] = tid
    return resp


@app.middleware("http")
async def log_requests(request: Request, call_next):
    path = request.url.path

    start_time = time.time()

    if not "health" in path and not "upload_file" in path:
        body_bytes = await request.body()
        body_str = body_bytes.decode("utf-8") if body_bytes else ""

        logger.info(f"➡️  {request.method} {request.url}")
        if body_str:
            logger.info(f"🧾  Request body: {body_str}")

    try:
        response = await call_next(request)
    except Exception as e:
        logger.exception(f"❌ Exception while handling request: {e}")
        raise

    process_time = (time.time() - start_time) * 1000
    logger.info(f"⬅️  {request.method} {request.url} "
                f"completed in {process_time:.2f}ms "
                f"status={response.status_code}")
    return response


# ---- 捕获 422 验证错误 ----
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    body = await request.body()
    logger.error("⚠️ Validation error on %s", request.url)
    logger.error("Request body: %s", body.decode("utf-8") if body else "<empty>")
    logger.error("Details: %s", exc.errors())

    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors()},
    )


if __name__ == '__main__':
    set_default_openai_key(SETTINGS.OPENAI_API_KEY)
    os.environ["OPENAI_API_KEY"] = SETTINGS.OPENAI_API_KEY
    os.environ["FAL_KEY"] = SETTINGS.FA_KEY

    uvicorn.run(app, host=SETTINGS.HOST, port=SETTINGS.PORT, workers=SETTINGS.WORKERS, log_config="log_config.yaml")

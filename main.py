import uvicorn
from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
from redis import asyncio as aioredis
from starlette.middleware.cors import CORSMiddleware

from src.exception import APIException
from src.optivum.router import router as optivum_router
from src.response import APIResponse

app: FastAPI = FastAPI(
    title="Timetable API",
    contact={
        "name": "Marioneq4958",
        "url": "https://github.com/marioneq4958",
        "email": "marioneq4958@gmail.com",
    },
    license_info={
        "name": "Apache 2.0",
        "url": "https://www.apache.org/licenses/LICENSE-2.0.html",
    },
)

origins: list[str] = ["http://localhost", "https://plan.dk-gl.eu"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(optivum_router)


@app.on_event("startup")
async def startup() -> None:
    redis = aioredis.from_url(
        "redis://localhost", encoding="utf8", decode_responses=True
    )
    FastAPICache.init(RedisBackend(redis), prefix="fastapi-cache")


@app.exception_handler(404)
def not_found_error_exception(request: Request, exc) -> JSONResponse:
    return JSONResponse(
        status_code=404,
        content=jsonable_encoder(
            APIResponse(message="Not Found").dict(exclude_none=True)
        ),
    )


@app.exception_handler(500)
def internal_server_error_exception(request: Request, exc) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content=jsonable_encoder(
            APIResponse(message="Internal Server Error", detail=str(exc)).dict(
                exclude_none=True
            )
        ),
    )


@app.exception_handler(RequestValidationError)
def request_validation_exception(request: Request, exc) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content=jsonable_encoder(
            APIResponse(message="Request Validation Error", detail=exc.errors()).dict(
                exclude_none=True
            )
        ),
    )


@app.exception_handler(APIException)
def api_exception(request: Request, exc: APIException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.code,
        content=jsonable_encoder(
            APIResponse(message=exc.message).dict(exclude_none=True)
        ),
    )


if __name__ == "__main__":
    uvicorn.run("main:app")

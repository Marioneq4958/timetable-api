from typing import Union
from urllib.parse import urljoin

from aiohttp import ClientSession
from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse
from fastapi_cache.decorator import cache
from pydantic import HttpUrl

from src.exception import APIException
from src.optivum.models.context import Context
from src.optivum.models.unit import Unit, SortedUnitsList
from src.optivum.models.unit_type import UnitType
from src.response import APIResponse
from src.optivum.models.lesson import Lesson
from src.optivum.utils import get_units_list_url, get_school_logo_path

router = APIRouter(prefix="/optivum", tags=["Optivum"])


@router.get(
    "/getContext",
    response_model=APIResponse[Context],
    response_model_by_alias=True,
)
@cache(expire=28800)
async def get_context(
    base_url: HttpUrl = Query(alias="baseURL"),
    sort_units: bool = Query(alias="sortUnits", default=False),
) -> APIResponse[Context]:
    list_url: str = await get_units_list_url(base_url)
    context: Context = await Context.get(list_url, sort_units)
    return APIResponse(data=context)


@router.get(
    "/getUnits",
    response_model=APIResponse[Union[list[Unit], SortedUnitsList]],
    response_model_by_alias=True,
)
@cache(expire=28800)
async def get_units(
    base_url: HttpUrl = Query(alias="baseURL"),
    sort: bool = Query(alias="sort", default=False),
) -> APIResponse[Union[list[Unit], SortedUnitsList]]:
    list_url: str = await get_units_list_url(base_url)
    units: list[Unit] = await Unit.get(list_url)
    return APIResponse(data=SortedUnitsList.get(units) if sort else units)


@router.get("/getSchoolLogo", response_class=StreamingResponse)
@cache(expire=28800)
async def get_school_logo(
    base_url: HttpUrl = Query(alias="baseURL"),
) -> StreamingResponse:
    list_url: str = await get_units_list_url(base_url)
    session: ClientSession = ClientSession()
    try:
        response = await session.get(list_url)
    except:
        raise APIException(504, "Gateway timeout")
    path: str = get_school_logo_path(await response.text())
    logo_url: str = urljoin(list_url, path)
    try:
        response = await session.get(logo_url)
    except:
        raise APIException(504, "Gateway timeout")
    content = response.content.iter_chunked(1024)
    await session.close()
    return StreamingResponse(content, media_type=response.headers["Content-Type"])


@router.get(
    "/getLessons",
    response_model=APIResponse[list[Lesson]],
    response_model_by_alias=True,
)
@cache(expire=28800)
async def get_lessons(
    base_url: HttpUrl = Query(alias="baseURL"),
    empty_lessons: bool = Query(alias="emptyLessons", default=False),
    unit_type: UnitType = Query(alias="unitType"),
    unit_id: int = Query(alias="unitId"),
) -> APIResponse[list[list[Lesson]]]:
    list_url = await get_units_list_url(base_url)
    lessons: list[Lesson] = await Lesson.get(
        list_url, unit_type, unit_id, empty_lessons
    )
    return APIResponse(data=lessons)

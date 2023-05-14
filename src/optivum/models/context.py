from typing import Optional, Union

from aiohttp import ClientSession
from pydantic import BaseModel, Field

from src.exception import APIException
from src.optivum.models.unit import SortedUnitsList, Unit
from src.optivum.utils import (
    get_school_name,
    get_timetable_generation_date,
    get_timetable_validation_date,
    get_unit_url,
)


class Context(BaseModel):
    school_name: Optional[str] = Field(alias="schoolName")
    generation_date: Optional[str] = Field(alias="generationDate")
    validation_date: Optional[str] = Field(alias="validationDate")
    units: Union[list[Unit], SortedUnitsList]

    class Config:
        allow_population_by_field_name = True

    @staticmethod
    async def get(list_url: str, sort_units: bool) -> "Context":
        session: ClientSession = ClientSession()
        try:
            response = await session.get(list_url)
        except:
            raise APIException(504, "Gateway timeout")
        school_name: Optional[str] = get_school_name(await response.text())
        units: list[Unit] = await Unit.get(list_url)
        generation_date = None
        validation_date = None
        if units:
            url: str = get_unit_url(list_url, units[0].id, units[0].type)
            try:
                response = await session.get(url)
            except:
                raise APIException(504, "Gateway timeout")
            html: str = await response.text()
            generation_date = get_timetable_generation_date(html)
            validation_date = get_timetable_validation_date(html)
        await session.close()
        return Context(
            school_name=school_name,
            generation_date=generation_date,
            validation_date=validation_date,
            units=SortedUnitsList.get(units) if sort_units else units,
        )

from enum import Enum
from typing import Optional
from urllib.parse import urljoin

from aiohttp import ClientSession
from bs4 import BeautifulSoup
from pydantic import BaseModel, Field

from src.exception import APIException
from src.optivum.models.unit_type import UnitType
from src.optivum.utils import (
    verify_timetable_page,
    extract_unit_code_and_name,
    extract_unit_type_and_id_from_url,
)


class UnitsListVariant(Enum):
    DEFAULT = 1
    SELECT = 2
    HOME_BUTTONS = 3

    @staticmethod
    def get(html: str) -> "UnitsListVariant":
        units_list_variant_tag = {
            UnitsListVariant.SELECT: "select",
            UnitsListVariant.HOME_BUTTONS: ".menu",
        }
        soup = BeautifulSoup(html, "html.parser")
        units_list_variant: UnitsListVariant = UnitsListVariant.DEFAULT
        for variant in units_list_variant_tag:
            if soup.select(units_list_variant_tag[variant]):
                units_list_variant = variant
                break
        return units_list_variant


class Unit(BaseModel):
    id: Optional[int]
    code: Optional[str]
    name: Optional[str]
    full_name: str = Field(alias="fullName")
    type: UnitType

    class Config:
        allow_population_by_field_name = True

    @staticmethod
    async def get(list_url: str) -> list["Unit"]:
        session: ClientSession = ClientSession()
        try:
            response = await session.get(str(list_url))
        except:
            raise APIException(504, "Gateway timeout")
        text = await response.text(encoding="utf-8")
        if not verify_timetable_page(text):
            raise APIException(400, 'Invalid "baseURL"')
        variant: UnitsListVariant = UnitsListVariant.get(text)
        if variant is UnitsListVariant.HOME_BUTTONS:
            units: list[Unit] = []
            soup = BeautifulSoup(text, "html.parser")
            for a_tag in soup.select('a[hidefocus="true"]'):
                url: str = urljoin(str(list_url), a_tag["href"])
                response = await session.get(url)
                units = units + Unit.parse_html(
                    await response.text(encoding="utf-8"), variant
                )
        else:
            units: list[Unit] = Unit.parse_html(text, variant)
        await session.close()
        return units

    @staticmethod
    def parse_html(html: str, variant: UnitsListVariant) -> list["Unit"]:
        units: list[Unit] = []
        soup = BeautifulSoup(html, "html.parser")
        if variant is not UnitsListVariant.SELECT:
            a_tags: list = soup.select("a")
            for a_tag in a_tags:
                if not a_tag.has_attr("href"):
                    continue
                unit_type, unit_id = extract_unit_type_and_id_from_url(a_tag["href"])
                if not unit_type or not unit_id:
                    continue
                unit_code, unit_name = extract_unit_code_and_name(
                    a_tag.text.strip(), unit_type
                )
                units.append(
                    Unit(
                        id=unit_id,
                        code=unit_code,
                        name=unit_name,
                        full_name=a_tag.text,
                        type=unit_type,
                    )
                )
        else:
            select_tags: list = soup.select("select")
            for select_tag in select_tags:
                unit_type: UnitType = UnitType.get_by_code(select_tag["name"][0])
                if unit_type is UnitType.UNKNOWN:
                    continue
                for option_tag in select_tag.select("option"):
                    if not option_tag.has_attr("value"):
                        continue
                    unit_code, unit_name = extract_unit_code_and_name(
                        option_tag.text, unit_type
                    )
                    units.append(
                        Unit(
                            id=option_tag["value"],
                            code=unit_code,
                            name=unit_name,
                            full_name=option_tag.text.strip(),
                            type=unit_type,
                        )
                    )
        return units


class SortedUnitsList(BaseModel):
    branches: list[Unit]
    teachers: list[Unit]
    rooms: list[Unit]

    @staticmethod
    def get(units: list[Unit]) -> "SortedUnitsList":
        return SortedUnitsList(
            branches=[unit for unit in units if unit.type is UnitType.BRANCH],
            teachers=[unit for unit in units if unit.type is UnitType.TEACHER],
            rooms=[unit for unit in units if unit.type is UnitType.ROOM],
        )

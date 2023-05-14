import re
from typing import Optional
from urllib.parse import urljoin

from aiohttp import ClientSession
from bs4 import BeautifulSoup

from src.exception import APIException
from src.optivum.models.unit_type import UnitType


def extract_unit_code_and_name(
    full_name: str, unit_type: UnitType
) -> tuple[Optional[str], Optional[str]]:
    if unit_type is UnitType.TEACHER:
        match = re.search(
            r"^(?P<name>[A-Za-zżźćńółęąśŻŹĆĄŚĘŁÓŃ]\.[0-9A-Za-zżźćńółęąśŻŹĆĄŚĘŁÓŃ \-]*)(?: \((?P<code>[A-Za-zżźćńółęąśŻŹĆĄŚĘŁÓŃ0-9_]{2})\))?$",
            full_name,
        )
        if match:
            return match["code"], match["name"].strip()
        return full_name, None
    match = re.search(
            r"^(?P<code>[0-9A-Za-z_/\-]*) (?P<name>[0-9A-Za-zżźćńółęąśŻŹĆĄŚĘŁÓŃ \-_./]*)",
            full_name,
    )
    if match:
        return match["code"], match["name"].strip()
    return full_name, None


def verify_timetable_page(html: str) -> bool:
    soup = BeautifulSoup(html, "html.parser")
    return (
        soup.select_one('meta[name="description"]')
        and " programu Plan lekcji Optivum firmy VULCAN"
        in soup.select_one('meta[name="description"]')["content"]
    )


async def get_units_list_url(url: str) -> str:
    session: ClientSession = ClientSession()
    if len(url) <= 5:
        raise APIException(400, 'Invalid "baseURL"')
    if url[-5:] != ".html":
        if url[-1] == "/":
            url = f"{url}index.html"
        else:
            url = f"{url}/index.html"
    elif extract_unit_type_and_id_from_url(url) != (None, None):
        url = urljoin(url, "../index.html")
    try:
        response = await session.get(url)
    except:
        raise APIException(504, "Gateway timeout")
    html: str = await response.text()
    if not verify_timetable_page(html):
        raise APIException(400, 'Invalid "baseURL"')
    soup = BeautifulSoup(html, "html.parser")
    if soup.select("frame"):
        url = urljoin(url, "lista.html")
    await session.close()
    return url


def get_school_name(html: str) -> Optional[str]:
    soup = BeautifulSoup(html, "html.parser")
    meta_description_tag = soup.select_one('meta[name="description"]')
    if not meta_description_tag and meta_description_tag.has_attr("content"):
        return None
    content = meta_description_tag["content"].replace("/n", "")
    if ". Plan lekcji" in content:
        return content.split(". Plan lekcji")[0].strip() or None
    elif ". Lista oddziałów, nauczycieli i sal" in content:
        return content.split(". Lista oddziałów, nauczycieli i sal")[0].strip() or None
    else:
        return None


def get_timetable_generation_date(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    timetable_info_tag = soup.select_one("td.op > table >  tr > td")
    generation_date: str = (
        timetable_info_tag.text.split("za pomocą programu")[0]
        .replace("wygenerowano", "")
        .replace("\n", "")
        .replace("\r", "")
        .strip()
    )
    return generation_date


def get_timetable_validation_date(html: str) -> Optional[str]:
    soup = BeautifulSoup(html, "html.parser")
    td_align_left_tags = soup.select(
        'div > table[cellpadding="10"] > tr > td[align="left"]'
    )
    validation_date = None
    for td_align_left_tag in td_align_left_tags:
        if "Obowiązuje od:" in td_align_left_tag.text:
            validation_date = (
                td_align_left_tag.text.replace("Obowiązuje od:", "")
                .replace("\r", "")
                .replace("\n", "")
                .strip()
            )
            break
    return validation_date


def get_school_logo_path(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    img_logo_tag = soup.select_one('.logo > img[alt="Logo szkoły"]')
    if not img_logo_tag or not img_logo_tag.has_attr("src"):
        raise APIException(400, "School logo was not found")
    return img_logo_tag["src"]


def get_unit_url(list_url: str, unit_id: int, unit_type: UnitType) -> str:
    return urljoin(str(list_url), f"plany/{unit_type.get_code()}{unit_id}.html")


def extract_unit_type_and_id_from_url(
    url: str,
) -> tuple[Optional[UnitType], Optional[int]]:
    match = re.search(r"(?P<type>[ons])(?P<id>\d+)\.html", url)
    if match:
        return UnitType.get_by_code(match["type"]), int(match["id"])
    return None, None

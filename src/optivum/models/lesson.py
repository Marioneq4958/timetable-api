from typing import Optional
from datetime import time

from aiohttp import ClientSession
from bs4 import BeautifulSoup
from pydantic import BaseModel, Field

from src.exception import APIException
from src.optivum.models.unit_type import UnitType
from src.optivum.utils import (
    verify_timetable_page,
    get_unit_url,
    extract_unit_type_and_id_from_url,
)


class Day(BaseModel):
    id: int
    name: str


class TimeSlot(BaseModel):
    id: int
    number: Optional[int]
    name: str
    start: time
    end: time

    @staticmethod
    def parse_html(row: str, row_index: int) -> "TimeSlot":
        soup = BeautifulSoup(row, "html.parser")
        number_tag = soup.select_one("td.nr")
        hours_tag = soup.select_one("td.g")
        if number_tag.text.isnumeric():
            number = int(number_tag.text)
        else:
            number = None
        start: time = time(*map(int, hours_tag.text.split("-")[0].strip().split(":")))
        end: time = time(*map(int, hours_tag.text.split("-")[1].strip().split(":")))
        return TimeSlot(
            id=row_index + 1, number=number, name=number_tag.text, start=start, end=end
        )


class UnitInfo(BaseModel):
    id: Optional[int]
    code: Optional[str]

    class Config:
        allow_population_by_field_name = True


class BranchInfo(BaseModel):
    id: Optional[int]
    code: Optional[str]
    group_code: Optional[str] = Field(alias="groupCode")
    interbranch_group_code: Optional[str] = Field(alias="interbranchGroupCode")

    class Config:
        allow_population_by_field_name = True


class Lesson(BaseModel):
    day: Day
    time_slot: TimeSlot = Field(alias="timeSlot")
    subject_code: Optional[str] = Field(alias="subjectCode")
    room: Optional[UnitInfo]
    branches: Optional[list[BranchInfo]]
    teachers: Optional[list[UnitInfo]]
    comment: Optional[str]

    class Config:
        allow_population_by_field_name = True

    @staticmethod
    async def get(
        list_url: str, unit_type: UnitType, unit_id: int, empty_lessons: bool
    ) -> list["Lesson"]:
        url: str = get_unit_url(list_url, unit_id, unit_type)
        session: ClientSession = ClientSession()
        try:
            response = await session.get(url)
        except:
            raise APIException(504, "Gateway timeout")
        html: str = await response.text(encoding="utf-8")
        if not verify_timetable_page(html):
            raise APIException(400, "Invalid unit")
        soup = BeautifulSoup(html, "html.parser")
        await session.close()
        return Lesson.parse_html_table(
            str(soup.select_one("table.tabela")), empty_lessons
        )

    @staticmethod
    def parse_html_table(html: str, empty_lessons: bool) -> list["Lesson"]:
        lessons: list[Lesson] = []
        soup = BeautifulSoup(html, "html.parser")
        row_tags: list = [
            row_tag for row_tag in soup.select("tr") if not row_tag.select("th")
        ]
        th_tags: list = soup.select("th")
        for row_tag_index, row_tag in enumerate(row_tags):
            time_slot: TimeSlot = TimeSlot.parse_html(str(row_tag), row_tag_index)
            lesson_tags: list = row_tag.select("td.l")
            for lesson_tag_index, lesson_tag in enumerate(lesson_tags):
                day: Day = Day(
                    id=lesson_tag_index + 1, name=th_tags[lesson_tag_index + 2].text
                )
                raw_lesson_groups: list = [
                    BeautifulSoup(raw_lesson_group, "html.parser")
                    for raw_lesson_group in "".join(
                        map(str, lesson_tag.contents)
                    ).split("<br/>")
                ]
                for raw_lesson_group in raw_lesson_groups:
                    raw_lesson_group = (
                        raw_lesson_group.find("span", recursive=False, style=True)
                        or raw_lesson_group
                    )
                    lesson_group = Lesson.parse_html(
                        "".join(map(str, raw_lesson_group.contents)), time_slot, day
                    )
                    if (
                        lesson_group.subject_code
                        or lesson_group.comment
                        or empty_lessons
                    ):
                        lessons.append(lesson_group)
        return sorted(lessons, key=lambda lesson: (lesson.day.id, lesson.time_slot.id))

    @staticmethod
    def parse_html(html: str, time_slot: TimeSlot, day: Day) -> "Lesson":
        soup = BeautifulSoup(html, "html.parser")

        # Comment
        if not soup.select(".p"):
            comment = soup.text.strip() or None
            return Lesson(day=day, time_slot=time_slot, comment=comment)

        # Subject
        subject_code: str = "".join(
            [subject_tag.text for subject_tag in soup.select(".p")]
        )

        # Group name
        if "-" in subject_code:
            group_code = subject_code.split("-")[-1]
            subject_code = subject_code.replace(f"-{group_code}", "")
        else:
            group_code = None

        # Interbranch group code
        if "#" in subject_code and len(soup.select(".p")) >= 2:
            interbranch_group_code = subject_code.split("#")[-1]
            subject_code = subject_code.replace(f"#{interbranch_group_code}", "")
        else:
            interbranch_group_code = None
        [subject_tag.extract() for subject_tag in soup.select(".p")]

        # Room
        room_tag = soup.select_one(".s")
        room = None
        if room_tag:
            if room_tag.text != "@":
                room = UnitInfo(
                    id=extract_unit_type_and_id_from_url(room_tag["href"])[1]
                    if room_tag.has_attr("href")
                    else None,
                    code=room_tag.text,
                )
            room_tag.extract()

        # Teachers
        teacher_tags: list = soup.select(".n")
        teachers: list[UnitInfo] = []
        for teacher_tag in teacher_tags:
            teachers.append(
                UnitInfo(
                    id=extract_unit_type_and_id_from_url(teacher_tag["href"])[1]
                    if teacher_tag.has_attr("href")
                    else None,
                    code=teacher_tag.text,
                )
            )
            teacher_tag.extract()

        # Branches
        branches: list[BranchInfo] = []
        for raw_branch in "".join(map(str, soup.contents)).split(","):
            if raw_branch.strip() or group_code:
                if "-" in raw_branch:
                    group_code = raw_branch.split("-")[1]
                branch_tag = BeautifulSoup(raw_branch, "html.parser").select_one(".o")
                branches.append(
                    BranchInfo(
                        id=extract_unit_type_and_id_from_url(branch_tag["href"])[1]
                        if branch_tag and branch_tag.has_attr("href")
                        else None,
                        code=branch_tag.text if branch_tag else None,
                        group_code=group_code.strip() if group_code else None,
                        interbranch_group_code=interbranch_group_code,
                    )
                )

        return Lesson(
            time_slot=time_slot,
            day=day,
            subject_code=subject_code,
            room=room,
            teachers=teachers,
            branches=branches,
        )

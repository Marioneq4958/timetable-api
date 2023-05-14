from enum import IntEnum


class UnitType(IntEnum):
    UNKNOWN = 0
    BRANCH = 1
    TEACHER = 2
    ROOM = 3

    @staticmethod
    def get_by_code(code: str) -> "UnitType":
        unit_types_codes: dict[UnitType, str] = {
            UnitType.BRANCH: "o",
            UnitType.TEACHER: "n",
            UnitType.ROOM: "s",
        }
        unit_type: UnitType = UnitType.UNKNOWN
        for type in unit_types_codes:
            if unit_types_codes[type] == code:
                unit_type = type
                break
        return unit_type

    def get_code(self) -> str:
        if self is UnitType.BRANCH:
            return "o"
        elif self is UnitType.TEACHER:
            return "n"
        elif self is UnitType.ROOM:
            return "s"
        else:
            return ""

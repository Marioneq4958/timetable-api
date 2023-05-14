class APIException(Exception):
    def __init__(self, code: int, message: str, detail: str = None) -> None:
        self.code = code
        self.message = message
        self.detail = detail

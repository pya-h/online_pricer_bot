
class NoLatestDataException(Exception):

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(self.message)


class InvalidInputException(Exception):

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(self.message)

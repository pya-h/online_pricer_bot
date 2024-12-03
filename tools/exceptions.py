class NoLatestDataException(Exception):

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(f"No latest data to {self.message}")


class InvalidInputException(Exception):

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(f"Invalid {self.message}")


class CacheFailureException(Exception):

    def __init__(self, cause: Exception) -> None:
        self.message = (
            f"ذخیره نتایج API برای استفاده کاربران VIP با خطا مواجه شد. لطفا هر جه سریع تر موضوع را به دولوپر اطلاع دهید."
        )
        self.message += f"\nعلت خطا: {cause.__str__()}"
        super().__init__(f"Invalid {self.message}")


class NoSuchThingException(Exception):

    def __init__(self, id: int, thing: str | None = None) -> None:
        self.thing = thing or "Entity"
        self.message = f"{self.thing} with id={id} does not exist!"
        super().__init__(self.message)


class InvalidKeyboardException(Exception):
    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(f"Invalid keyboard used: {self.message}")


class MaxAddedCommunityException(Exception):
    def __init__(self, community_type: str) -> None:
        self.message = f"You can not add another {community_type} anymore."
        super().__init__(self.message)


class UserNotAllowedException(Exception):
    def __init__(self, user_id: int, forbidden_action_title: str) -> None:
        self.message = f"User with id={user_id} is not allowed to {forbidden_action_title}."
        super().__init__(self.message)

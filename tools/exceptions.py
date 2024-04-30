
class NoLatestDataException(Exception):

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(f'No latest data to {self.message}')


class InvalidInputException(Exception):

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(f'Invalid {self.message}')


class CacheFailureException(Exception):

    def __init__(self, cause: Exception) -> None:
        self.message = f'ذخیره نتایج API برای استفاده کاربران VIP با خطا مواجه شد. لطفا هر جه سریع تر موضوع را به دولوپر اطلاع دهید.'
        self.message += f'\nعلت خطا: {cause.__str__()}'
        super().__init__(f'Invalid {self.message}')

class NotPlusException(Exception):

    def __init__(self, chat_id: int) -> None:
        self.message = f"Account with chat_id={chat_id} is not VIP now!"
        super().__init__(self.message)


class NoSuchPlusPlanException(Exception):

    def __init__(self, plan_id: int) -> None:
        self.message = f"PlusPlan with id={plan_id} does not exist!"
        super().__init__(self.message)


class InvalidKeyboardException(Exception):
    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(f'Invalid keyboard used: {self.message}')


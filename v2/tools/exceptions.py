
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

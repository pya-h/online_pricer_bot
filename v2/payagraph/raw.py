
class CanBeKeyboardItemInterface:
    '''This is used for for example passing argument to InlineKeyboard.Arrange'''
    def title(self) -> str:
        pass
    def value(self) -> int:
        pass


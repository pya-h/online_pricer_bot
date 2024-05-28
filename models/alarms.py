

class PriceAlarm:


    def __init__(self, chat_id, currency_symbol: str, target_price: int | float, target_unit: str = 'IRT', id: int = 0) -> None:
        self.id = id
        self.chat_id = chat_id
        self.currency_symbol = currency_symbol
        self.target_price = target_price
        self.target_unit = target_unit



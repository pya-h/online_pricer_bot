from api.archived_codes import PriceSeek
from api.api_async import run_async

ps = PriceSeek()

# run_async(ps.get_all)
print(ps.extract_price('<p id="ss" sadasdfd id="usdmax" s fsd>100,000</>'))

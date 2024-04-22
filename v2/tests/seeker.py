from api.price_seek import PriceSeek, run_async

ps = PriceSeek()

# run_async(ps.get_all)
print(ps.extract_price('<p id="ss" sadasdfd id="usdmax" s fsd>100,000</>'))
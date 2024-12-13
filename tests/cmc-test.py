from api.crypto_service import CoinMarketCapService
from decouple import config
from json import dumps
import asyncio
from time import time, sleep
from math import ceil


def save(data: dict, dest: str | None = None):
    f = open(dest or "tests/api-result.json", "w")
    f.write(dumps(data, ensure_ascii=False, indent=4))
    f.close()


def find_missing_tokens(limit=1000):
    api_key = config("COINMARKETCAP_API_KEY")
    cmc = CoinMarketCapService(api_key, cmc_coin_fetch_limit=limit)

    async def get_coins():
        res = await cmc.get_request()
        return res

    fetch_time = time()
    coins = asyncio.run(get_coins())
    fetch_time = time() - fetch_time
    missings = []
    for coin in cmc.coinsInPersian:
        if coin not in coins:
            missings.append(coin)

    return missings, fetch_time

def fix_symbols():
    api_key = config("COINMARKETCAP_API_KEY")
    cmc = CoinMarketCapService(api_key)
    dc = {}
    for c in cmc.coinsInPersian:
        dc[c.upper()] = cmc.coinsInPersian[c]
    save(dc)


def list_tokens(tokens: list[str], line_limit: int = 10):
    res = ''
    num_of_tokens = len(tokens)
    i, lines = 0, int(num_of_tokens / line_limit)
    while i < lines:
        res += f"{',\t'.join(tokens[i*line_limit:(i + 1)*line_limit])}\n\t\t\t"
        i += 1
    if lines * line_limit < num_of_tokens:
        res += f"{',\t'.join(tokens[lines * line_limit:num_of_tokens])}\n"
    return res

def get_number_of_free_accounts_required(credit_using: float, fetch_cycle_in_minutes: int = 10, cmc_max_credit_in_month: int = 10000):
    #  For fetching every {fetch_cycle_in_minutes} minutes
    credit_in_month = credit_using * 24 * 60 * 30 / fetch_cycle_in_minutes
    accounts_required = credit_in_month / cmc_max_credit_in_month
    return accounts_required, ceil(accounts_required)

def full_test():
    test_limit = 500
    limit_step = 500
    result_file = 'cmc-limit-test.txt'
    f = open(result_file, "w")
    credit_base = 0.005
    while test_limit <= 5000:
        missings, fetch_time = find_missing_tokens(test_limit)
        credit_used = credit_base * test_limit
        required_accounts_report = ''
        for cycle in [5, 10, 20, 30]:
            min_required, logical_required = get_number_of_free_accounts_required(credit_used, cycle)
            required_accounts_report += f"\t\tFree Accounts Required for {cycle} min schedule:\tMinimum:{min_required:.1f},\tLogical:{logical_required}\n"
        f.write(f'''
        Limit: {test_limit}
        Number of missing tokens: {len(missings)}            
        Credit Used: {credit_used}
{required_accounts_report}
        Fetch time: {fetch_time:.3f} seconds ([{fetch_time * 1000:.2f} milliseconds])
        Missing tokens:
            {list_tokens(missings)}
                
    - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        ''')
        print(f'Test on limit={test_limit} done.')
        test_limit += limit_step
        sleep(1)
    f.close()

full_test()
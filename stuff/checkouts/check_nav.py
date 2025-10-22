from tools.manuwriter import load_json

navasan_data = load_json('nav.json', 'api/data')
fiat_tokens = load_json('national-currencies.en.json', 'api/data')
gold_tokens = load_json('golds.en.json', 'api/data')

fiat_not_founds = 0

for item in fiat_tokens:
    item = item.lower()
    if item not in navasan_data:
        fiat_not_founds += 1
        print(f"FIAT: {item}")

gold_not_founds = 0
for item in gold_tokens:
    item = item.lower()
    if item not in navasan_data:
        gold_not_founds += 1
        print(f"GOLD: {item}")

print("Total not founds:")
print(f"Fiat: {fiat_not_founds}")
print(f"Gold: {gold_not_founds}")

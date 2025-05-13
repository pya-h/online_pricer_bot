from models.account import Account

chats = Account.Everybody()

for chat_id in chats:
    try:
        acc = Account.Get(chat_id)
        i = acc.desired_coins.index('MATIC')
        acc.desired_coins[i] = 'POL'
        acc.save()
        print(acc.chat_id, 'Fixed')
    except Exception as x:
        pass

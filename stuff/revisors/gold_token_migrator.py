"""
Migration script: Replace old GoldService token names with new Navasan equivalents
in all database currency lists (accounts, channels, groups) and alarms.
"""

import time
from db.interface import DatabaseInterface

# Old token → New Navasan token (None means remove)
TOKEN_MAP = {
    "TALA_18": "18AYAR",
    "TALA_24": None,
    "TALA_MESGHAL": "ABSHODEH",
    "SEKE_EMAMI": "SEKKEH",
    "SEKE_BAHAR": "BAHAR",
    "SEKE_NIM": "NIM",
    "SEKE_ROB": "ROB",
    "SEKE_GERAMI": "GERAMI",
    "ONS": None,
    "ONSNOGHRE": None,
    "PALA": None,
    "ONSPALA": None,
    "OIL": None,
}

OLD_TOKENS = set(TOKEN_MAP.keys())


def migrate_token_list(raw: str) -> tuple:
    """Migrate a semicolon-separated token list.
    Returns (new_raw_string, replaced_count, removed_count)
    """
    if not raw:
        return raw, 0, 0

    tokens = raw.rstrip(";").split(";")
    new_tokens = []
    replaced = 0
    removed = 0

    for token in tokens:
        if token in TOKEN_MAP:
            replacement = TOKEN_MAP[token]
            if replacement is not None:
                new_tokens.append(replacement)
                replaced += 1
            else:
                removed += 1
        else:
            new_tokens.append(token)

    return ";".join(new_tokens) if new_tokens else "", replaced, removed


def main():
    db = DatabaseInterface.get()
    print("Connected to database.")
    time.sleep(1)

    stats = {
        "accounts_checked": 0,
        "accounts_updated": 0,
        "accounts_tokens_replaced": 0,
        "accounts_tokens_removed": 0,
        "channels_checked": 0,
        "channels_updated": 0,
        "channels_tokens_replaced": 0,
        "channels_tokens_removed": 0,
        "groups_checked": 0,
        "groups_updated": 0,
        "groups_tokens_replaced": 0,
        "groups_tokens_removed": 0,
        "alarms_checked": 0,
        "alarms_updated": 0,
        "alarms_deleted": 0,
    }

    # --- Migrate Accounts ---
    print("\n[1/4] Migrating accounts...")
    rows = db.execute(
        True,
        f"SELECT {db.ACCOUNT_ID}, {db.ACCOUNT_CURRENCIES}, {db.ACCOUNT_CALC_CURRENCIES} FROM {db.TABLE_ACCOUNTS}",
    )
    if rows:
        for row in rows:
            stats["accounts_checked"] += 1
            chat_id, currencies_raw, calc_currencies_raw = row

            new_curr, curr_rep, curr_rem = migrate_token_list(currencies_raw)
            new_calc, calc_rep, calc_rem = migrate_token_list(calc_currencies_raw)

            total_replaced = curr_rep + calc_rep
            total_removed = curr_rem + calc_rem

            if total_replaced > 0 or total_removed > 0:
                db.execute(
                    False,
                    f"UPDATE {db.TABLE_ACCOUNTS} SET {db.ACCOUNT_CURRENCIES}=%s, {db.ACCOUNT_CALC_CURRENCIES}=%s WHERE {db.ACCOUNT_ID}=%s",
                    new_curr,
                    new_calc,
                    chat_id,
                )
                stats["accounts_updated"] += 1
                stats["accounts_tokens_replaced"] += total_replaced
                stats["accounts_tokens_removed"] += total_removed

    print(f"   Checked: {stats['accounts_checked']}, Updated: {stats['accounts_updated']}")

    # --- Migrate Channels ---
    print("\n[2/4] Migrating channels...")
    rows = db.execute(
        True,
        f"SELECT {db.CHANNEL_ID}, {db.CHANNEL_CURRENCIES} FROM {db.TABLE_CHANNELS}",
    )
    if rows:
        for row in rows:
            stats["channels_checked"] += 1
            channel_id, currencies_raw = row

            new_curr, replaced, removed = migrate_token_list(currencies_raw)

            if replaced > 0 or removed > 0:
                db.execute(
                    False,
                    f"UPDATE {db.TABLE_CHANNELS} SET {db.CHANNEL_CURRENCIES}=%s WHERE {db.CHANNEL_ID}=%s",
                    new_curr,
                    channel_id,
                )
                stats["channels_updated"] += 1
                stats["channels_tokens_replaced"] += replaced
                stats["channels_tokens_removed"] += removed

    print(f"   Checked: {stats['channels_checked']}, Updated: {stats['channels_updated']}")

    # --- Migrate Groups ---
    print("\n[3/4] Migrating groups...")
    rows = db.execute(
        True,
        f"SELECT {db.GROUP_ID}, {db.GROUP_CURRENCIES} FROM {db.TABLE_GROUPS}",
    )
    if rows:
        for row in rows:
            stats["groups_checked"] += 1
            group_id, currencies_raw = row

            new_curr, replaced, removed = migrate_token_list(currencies_raw)

            if replaced > 0 or removed > 0:
                db.execute(
                    False,
                    f"UPDATE {db.TABLE_GROUPS} SET {db.GROUP_CURRENCIES}=%s WHERE {db.GROUP_ID}=%s",
                    new_curr,
                    group_id,
                )
                stats["groups_updated"] += 1
                stats["groups_tokens_replaced"] += replaced
                stats["groups_tokens_removed"] += removed

    print(f"   Checked: {stats['groups_checked']}, Updated: {stats['groups_updated']}")

    # --- Migrate Alarms ---
    print("\n[4/4] Migrating alarms...")
    rows = db.execute(
        True,
        f"SELECT {db.PRICE_ALARM_ID}, {db.PRICE_ALARM_TARGET_TOKEN} FROM {db.TABLE_PRICE_ALARMS}",
    )
    alarms_to_delete = []
    if rows:
        for row in rows:
            stats["alarms_checked"] += 1
            alarm_id, token = row

            if token in TOKEN_MAP:
                replacement = TOKEN_MAP[token]
                if replacement is not None:
                    db.execute(
                        False,
                        f"UPDATE {db.TABLE_PRICE_ALARMS} SET {db.PRICE_ALARM_TARGET_TOKEN}=%s WHERE {db.PRICE_ALARM_ID}=%s",
                        replacement,
                        alarm_id,
                    )
                    stats["alarms_updated"] += 1
                else:
                    alarms_to_delete.append(alarm_id)

    if alarms_to_delete:
        placeholders = ",".join(["%s"] * len(alarms_to_delete))
        db.execute(
            False,
            f"DELETE FROM {db.TABLE_PRICE_ALARMS} WHERE {db.PRICE_ALARM_ID} IN ({placeholders})",
            *alarms_to_delete,
        )
        stats["alarms_deleted"] = len(alarms_to_delete)

    print(f"   Checked: {stats['alarms_checked']}, Updated: {stats['alarms_updated']}, Deleted: {stats['alarms_deleted']}")

    # --- Report ---
    print("\n" + "=" * 50)
    print("         MIGRATION REPORT")
    print("=" * 50)
    print(f"\n  Accounts:")
    print(f"    Checked:  {stats['accounts_checked']}")
    print(f"    Updated:  {stats['accounts_updated']}")
    print(f"    Tokens replaced: {stats['accounts_tokens_replaced']}")
    print(f"    Tokens removed:  {stats['accounts_tokens_removed']}")
    print(f"\n  Channels:")
    print(f"    Checked:  {stats['channels_checked']}")
    print(f"    Updated:  {stats['channels_updated']}")
    print(f"    Tokens replaced: {stats['channels_tokens_replaced']}")
    print(f"    Tokens removed:  {stats['channels_tokens_removed']}")
    print(f"\n  Groups:")
    print(f"    Checked:  {stats['groups_checked']}")
    print(f"    Updated:  {stats['groups_updated']}")
    print(f"    Tokens replaced: {stats['groups_tokens_replaced']}")
    print(f"    Tokens removed:  {stats['groups_tokens_removed']}")
    print(f"\n  Alarms:")
    print(f"    Checked:  {stats['alarms_checked']}")
    print(f"    Updated (token replaced): {stats['alarms_updated']}")
    print(f"    Deleted (no equivalent):  {stats['alarms_deleted']}")

    total_changes = (
        stats["accounts_tokens_replaced"]
        + stats["accounts_tokens_removed"]
        + stats["channels_tokens_replaced"]
        + stats["channels_tokens_removed"]
        + stats["groups_tokens_replaced"]
        + stats["groups_tokens_removed"]
        + stats["alarms_updated"]
        + stats["alarms_deleted"]
    )
    print(f"\n  Total changes: {total_changes}")
    print("=" * 50)


if __name__ == "__main__":
    main()

import json
import re
import time

import requests

PAGE_URL = "https://www.gempaytopup.com/stalk-ml"
DEFAULT_ENDPOINT = "https://www.gempaytopup.com/cek-id/mobile-legends"
ISAN_URL = "https://api.isan.eu.org/nickname/ml"
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36"
)
CACHE_TTL_SECONDS = 15 * 60

_lookup_cache = {}


def _cache_key(uid, zone):
    return f"{uid}:{zone}"


def _get_cached(uid, zone):
    entry = _lookup_cache.get(_cache_key(uid, zone))
    if not entry:
        return None
    data, expires_at = entry
    if expires_at < time.time():
        _lookup_cache.pop(_cache_key(uid, zone), None)
        return None
    return data


def _set_cached(uid, zone, data):
    _lookup_cache[_cache_key(uid, zone)] = (data, time.time() + CACHE_TTL_SECONDS)


def _normalize_result(data):
    if not isinstance(data, dict):
        return data
    if data.get("nickname"):
        data.setdefault("username", data["nickname"])
    if data.get("outcome") == "found":
        data.pop("message", None)
    return data


def _lookup_gempay(uid, zone):
    session = requests.Session()
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/json",
        "Origin": "https://www.gempaytopup.com",
        "Referer": PAGE_URL,
    }

    page = session.get(PAGE_URL, headers={"User-Agent": USER_AGENT}, timeout=20)
    page.raise_for_status()

    csrf_match = re.search(r'<meta name="csrf-token" content="([^"]+)">', page.text)
    token_match = re.search(r"initialToken:\s*'([^']+)'", page.text)
    endpoint_match = re.search(r"endpoint:\s*'([^']+)'", page.text)

    if not csrf_match or not token_match:
        raise ValueError("could not extract CSRF token or lookup token from page")

    endpoint = DEFAULT_ENDPOINT
    if endpoint_match:
        endpoint = endpoint_match.group(1).replace("\\/", "/")

    payload = {
        "tujuan": {
            "user_id": str(uid),
            "zone_id": str(zone),
        },
        "lookup_token": token_match.group(1),
        "website": "",
    }
    headers["Content-Type"] = "application/json"
    headers["X-CSRF-TOKEN"] = csrf_match.group(1)

    response = session.post(endpoint, headers=headers, json=payload, timeout=20)
    response.raise_for_status()
    return response.json()


def _lookup_isan(uid, zone):
    response = requests.get(
        ISAN_URL,
        params={"id": uid, "zone": zone},
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
        timeout=15,
    )
    response.raise_for_status()
    data = response.json()
    if not data.get("success") or not data.get("name"):
        message = data.get("message") or "Player not found"
        return {"error": message}

    return {
        "outcome": "found",
        "nickname": data.get("name"),
        "username": data.get("name"),
        "region": data.get("country") or "Unknown",
        "country_code": data.get("country_code"),
    }


def stalk_mlbb(uid, zone):
    """
    Look up MLBB player nickname and region.

    Args:
        uid (str): Player's UID
        zone (str): Player's zone/server ID

    Returns:
        dict: Player information response
    """
    uid = str(uid)
    zone = str(zone)

    cached = _get_cached(uid, zone)
    if cached:
        return cached

    try:
        data = _normalize_result(_lookup_gempay(uid, zone))
        if isinstance(data, dict) and (data.get("nickname") or data.get("username")):
            _set_cached(uid, zone, data)
            return data
        if isinstance(data, dict) and data.get("outcome") == "found":
            _set_cached(uid, zone, data)
            return data
    except requests.exceptions.HTTPError as e:
        status = e.response.status_code if e.response is not None else None
        print(f"GemPay lookup failed ({status}): {e}")
    except (requests.exceptions.RequestException, ValueError, json.JSONDecodeError) as e:
        print(f"GemPay lookup failed: {e}")

    try:
        data = _normalize_result(_lookup_isan(uid, zone))
        if isinstance(data, dict) and not data.get("error"):
            _set_cached(uid, zone, data)
        return data
    except (requests.exceptions.RequestException, json.JSONDecodeError) as e:
        print(f"Fallback lookup failed: {e}")
        return None


def main():
    print("=== MLBB Player Stalker ===")
    print("============================")

    while True:
        try:
            uid = input("Enter player UID: ").strip()
            zone = input("Enter player zone/server ID: ").strip()

            if not uid or not zone:
                print("Please enter both UID and zone!")
                continue

            print(f"\nStalking player with UID: {uid} and Zone: {zone}")
            print("Fetching data...")

            result = stalk_mlbb(uid, zone)

            if result:
                print("\n=== Player Information ===")
                print(json.dumps(result, indent=2, ensure_ascii=False))

                if isinstance(result, dict) and result.get("outcome") not in (None, "found"):
                    message = result.get("message") or result.get("error")
                    if message:
                        print(f"\nMessage: {message}")
            else:
                print("\nFailed to fetch player information!")

            another = input("\nDo you want to stalk another player? (y/n): ").strip().lower()
            if another != "y":
                print("Goodbye!")
                break

        except KeyboardInterrupt:
            print("\n\nProgram interrupted. Goodbye!")
            break
        except Exception as e:
            print(f"An unexpected error occurred: {e}")


if __name__ == "__main__":
    main()

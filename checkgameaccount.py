import requests
import json
import pickle
import os

def load_cookies_from_pkl(file_path='checkidcookies.pkl'):
    """
    Load cookies from a pickle file and return formatted cookie string for headers
    """
    try:
        if not os.path.exists(file_path):
            print(f"Cookie file not found: {file_path}")
            return None
            
        with open(file_path, 'rb') as f:
            cookies = pickle.load(f)
            
        # If cookies is a list of dicts (common format for browser export)
        if isinstance(cookies, list):
            cookie_string = "; ".join([f"{c['name']}={c['value']}" for c in cookies])
        # If cookies is a dict
        elif isinstance(cookies, dict):
            cookie_string = "; ".join([f"{k}={v}" for k, v in cookies.items()])
        else:
            print("Unknown cookie format")
            return None
            
        return cookie_string
    except Exception as e:
        print(f"Error loading cookies: {e}")
        return None

def stalk_mlbb(uid, zone):
    """
    Function to stalk MLBB player information
    
    Args:
        uid (str): Player's UID
        zone (str): Player's zone/server ID
    
    Returns:
        dict: Player information response
    """
    
    # URL for the stalk endpoint
    url = "https://www.gempaytopup.com/stalk-ml"
    
    # Load cookies dynamically
    cookie_header = load_cookies_from_pkl()
    
    # Headers from the request
    headers = {
        'Host': 'www.gempaytopup.com',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36',
        'Content-Type': 'application/json',
        'Accept': '*/*',
        'Sec-Gpc': '1',
        'Accept-Language': 'en-GB,en;q=0.9',
        'Origin': 'https://www.gempaytopup.com',
        'Sec-Fetch-Site': 'same-origin',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Dest': 'empty',
        'Referer': 'https://www.gempaytopup.com/stalk-ml',
        'Priority': 'u=1, i'
    }
    
    # Add Cookie header if loaded successfully, otherwise use default/empty or handle error
    # Note: If no cookies, the request might fail if the site requires them (XSRF/Session)
    if cookie_header:
        headers['Cookie'] = cookie_header
        # Attempt to extract X-Csrf-Token from cookies if possible, or use a hardcoded/extracted one?
        # The previous code had a hardcoded X-Csrf-Token. 
        # Usually, this token matches the XSRF-TOKEN cookie (decoded).
        # For now, let's keep the hardcoded one or try to extract from cookie string if present.
        
        # Simple extraction for XSRF-TOKEN
        try:
            import urllib.parse
            if 'XSRF-TOKEN=' in cookie_header:
                start = cookie_header.find('XSRF-TOKEN=') + 11
                end = cookie_header.find(';', start)
                if end == -1: end = len(cookie_header)
                token_encoded = cookie_header[start:end]
                token_decoded = urllib.parse.unquote(token_encoded)
                # Sometimes the cookie value is base64 or encrypted, but X-Csrf-Token header usually expects the decrypted value
                # If the hardcoded one worked, let's see. 
                # Let's try using the one from pickle if we can parse it, otherwise we might need to fetch the page first to get fresh tokens.
                # BUT, the prompt just says "use checkidcookies.pkl for cookies".
                # We will trust the cookies in the file are sufficient.
                # However, X-Csrf-Token header is often required for POST.
                # Let's try to extract it from the cookie string if possible.
                
                # Note: The previous hardcoded token '5ls8tiVvRaex9T0c4Ql2t2bC1bwybokVWwLFK6Xn' doesn't look like a standard JWT XSRF token.
                # It might be a Laravel session token or similar.
                # If we don't have a fresh token, we might fail.
                # Let's assume the user provided valid cookies that include session.
                pass
        except:
            pass
    else:
        # Fallback to the hardcoded cookies if file fails? 
        # Or just proceed without (likely fail)
        print("Warning: No cookies loaded. Request might fail.")
        # We can keep the old hardcoded ones as fallback if you want, but the user asked to use the file.
        # Let's stick to the file.

    # We still need X-Csrf-Token. 
    # If it's not dynamic, we keep the old one? 
    # Or we scrape it? 
    # For now, let's keep the old headers but REPLACE the 'Cookie' header.
    # AND we should probably keep the X-Csrf-Token if it's static, OR the user's pkl implies they have a session.
    # However, CSRF tokens usually expire. 
    # Ideally, we should GET the page first to get a fresh token if we can't extract it.
    # But let's start by just swapping the Cookie header.
    
    # Wait, the previous code had a specific X-Csrf-Token.
    # If that token is tied to the session in the cookie, we need the matching one.
    # If the user only provided cookies, we might be missing the CSRF header value unless we scrape it.
    # Let's try to request the page first to get the CSRF token if we are using requests.
    
    # Strategy:
    # 1. Load cookies into session.
    # 2. GET the page to get XSRF token (if needed) or just try POST if the cookie file has everything.
    # 3. Use the session to POST.
    
    s = requests.Session()
    
    # Load cookies into session
    if os.path.exists('checkidcookies.pkl'):
        try:
            with open('checkidcookies.pkl', 'rb') as f:
                cookies_data = pickle.load(f)
                if isinstance(cookies_data, list):
                    for c in cookies_data:
                        # Adaptation for playwright/selenium cookie format to requests
                        c_dict = {
                            'name': c.get('name'),
                            'value': c.get('value'),
                            'domain': c.get('domain'),
                            'path': c.get('path')
                        }
                        # Filter keys that requests.add_cookie supports or just set simple
                        s.cookies.set(c['name'], c['value'], domain=c.get('domain'), path=c.get('path'))
                elif isinstance(cookies_data, dict):
                    requests.utils.add_dict_to_cookiejar(s.cookies, cookies_data)
        except Exception as e:
            print(f"Error loading pickle: {e}")
            
    # Now we need the X-Csrf-Token.
    # Usually it's in a meta tag <meta name="csrf-token" content="...">
    # Let's fetch the main page first.
    try:
        main_page = s.get("https://www.gempaytopup.com/stalk-ml", headers={
            'User-Agent': headers['User-Agent']
        })
        
        # Extract CSRF token
        import re
        csrf_token = None
        match = re.search(r'<meta name="csrf-token" content="([^"]+)">', main_page.text)
        if match:
            csrf_token = match.group(1)
            headers['X-Csrf-Token'] = csrf_token
        
    except Exception as e:
        print(f"Error fetching main page for CSRF: {e}")

    
    # Payload with dynamic uid and zone
    payload = {
        "uid": str(uid),
        "zone": str(zone)
    }
    
    try:
        # Send POST request using the session (which has the cookies)
        # Update headers with the ones we prepared (including new CSRF if found)
        # Note: s.post will merge session cookies with request
        response = s.post(
            url, 
            headers=headers, 
            json=payload,
            timeout=10
        )
        
        # Check if request was successful
        response.raise_for_status()
        
        # Parse JSON response
        data = response.json()
        
        return data
        
    except requests.exceptions.RequestException as e:
        print(f"Error making request: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"Error parsing response: {e}")
        return None

def main():
    """
    Main function to get user input and display results
    """
    print("=== MLBB Player Stalker ===")
    print("============================")
    
    # Get user input
    while True:
        try:
            uid = input("Enter player UID: ").strip()
            zone = input("Enter player zone/server ID: ").strip()
            
            if not uid or not zone:
                print("Please enter both UID and zone!")
                continue
            
            # Confirm input
            print(f"\nStalking player with UID: {uid} and Zone: {zone}")
            print("Fetching data...")
            
            # Make the request
            result = stalk_mlbb(uid, zone)
            
            if result:
                print("\n=== Player Information ===")
                print(json.dumps(result, indent=2, ensure_ascii=False))
                
                # Check if there's an error message in the response
                if isinstance(result, dict) and 'error' in result:
                    print(f"\nError from server: {result['error']}")
                elif isinstance(result, dict) and 'message' in result:
                    print(f"\nMessage: {result['message']}")
            else:
                print("\nFailed to fetch player information!")
            
            # Ask if user wants to stalk another player
            another = input("\nDo you want to stalk another player? (y/n): ").strip().lower()
            if another != 'y':
                print("Goodbye!")
                break
                
        except KeyboardInterrupt:
            print("\n\nProgram interrupted. Goodbye!")
            break
        except Exception as e:
            print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    main()
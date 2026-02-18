import requests
import json

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
    
    # Headers from the request
    headers = {
        'Host': 'www.gempaytopup.com',
        'Cookie': 'XSRF-TOKEN=eyJpdiI6IlZTSGdaZ3Z4RzdKL0h4U3F3bVVpc1E9PSIsInZhbHVlIjoiY2M2bG5HWFlEYjNCYmd4YnR4Q1pZMXFtQytKTXU5OU0rTWdhclEvQ1VLUE1JaGUzc0JzbFNMd3BtWkRiSkxoem9wSGhDRThuUUFxQW5yZy9VM3M2WGF2T25yK2hCdFUreE8yWkFVeGVwQlFPV0IzbEZObjdrckNzTzB5TXQ2bnMiLCJtYWMiOiJiODFmNzA0YThiZjg1NTZmNWUwYzY1YzI3ZDQ2ODg3OWRlMDZlZTJkZGZkNGRhOWViOTYwNjIxMDZiNWM5MWM4IiwidGFnIjoiIn0%3D; gempay_topup_session=eyJpdiI6InczdkNPNTFwVFBkU3dyRHhxajlXUmc9PSIsInZhbHVlIjoiRm1ZU1lKRXVZUnViOHdHaEtaOVlubVloOVlFcVRCMjcvRkR6Z0Fsb3BNYlUrd1JiZmg4QURSK1M2NWxpZVYxRzA5a3l5VUdmaFNjSGw0RTZsbUgzR3FDbXdEVE5HU3NGeDdoTjVic25kTGtoVHoxYlowWkV6Z1dveUhObWZZa2oiLCJtYWMiOiJhZDg2ZjZiMDQ3NTc2NjUyNTU2ZDJkM2NhZDI3OGE3OGRmZTQxMDhjMDRhZDM2MGVhNzQ5ODE5NDc5MTY2ZTNiIiwidGFnIjoiIn0%3D',
        'X-Csrf-Token': '5ls8tiVvRaex9T0c4Ql2t2bC1bwybokVWwLFK6Xn',
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
    
    # Payload with dynamic uid and zone
    payload = {
        "uid": str(uid),
        "zone": str(zone)
    }
    
    try:
        # Send POST request
        response = requests.post(
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
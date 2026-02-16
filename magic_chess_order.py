import requests
import time
import re
from urllib.parse import unquote, quote, urlencode
import json
import sys

class SmileOneBot:
    def __init__(self, cookies_file='cookies.txt', uid=None, sid=None, productid=None):
        self.session = requests.Session()
        
        # Store dynamic inputs
        self.uid = uid
        self.sid = sid
        self.productid = productid
        self.csrf_token = None
        self.flowid = None
        
        # Load cookies from file
        self._load_cookies_from_file(cookies_file)
        
        # Set up base headers
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'Accept-Language': 'en-GB,en;q=0.9',
            'Origin': 'https://www.smile.one',
            'Referer': 'https://www.smile.one/merchant/game/magicchessgogo?source=other',
            'X-Requested-With': 'XMLHttpRequest',
            'Sec-Fetch-Site': 'same-origin',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Dest': 'empty',
            'Accept-Encoding': 'gzip, deflate'
        })
        
        # Extract CSRF from cookie
        self._extract_csrf_from_cookie()
        
        # Try to extract UID/SID from cookies if not provided
        self._extract_ids_from_cookies()
        
    def _load_cookies_from_file(self, filename):
        """Load cookies from text file (format: key=value; key2=value2)"""
        try:
            with open(filename, 'r') as f:
                cookie_content = f.read().strip()
            
            # Remove "Cookie: " prefix if present
            if cookie_content.startswith('Cookie:'):
                cookie_content = cookie_content[7:].strip()
            
            # Parse cookies
            cookies = {}
            for item in cookie_content.split(';'):
                item = item.strip()
                if '=' in item:
                    key, value = item.split('=', 1)
                    cookies[key.strip()] = value.strip()
            
            # Update session cookies
            self.session.cookies.update(cookies)
            print(f"✅ Loaded {len(cookies)} cookies from {filename}")
            
        except FileNotFoundError:
            print(f"❌ Error: {filename} not found!")
            sys.exit(1)
        except Exception as e:
            print(f"❌ Error loading cookies: {e}")
            sys.exit(1)
    
    def _extract_csrf_from_cookie(self):
        """Extract CSRF token from cookie"""
        csrf_cookie = self.session.cookies.get('_csrf')
        if csrf_cookie:
            decoded = unquote(csrf_cookie)
            # Extract token from format: "552004eba3515d8d93a4d177de4e66c0a115076d4bd3f11f1188e16de8c19a01a%3A2%3A..."
            match = re.search(r'([a-f0-9]{64})', decoded)
            if match:
                self.csrf_token = match.group(1)
                print(f"✅ Extracted CSRF token")
                return True
        
        print("⚠️ Could not extract CSRF token from cookie")
        return False
    
    def _extract_ids_from_cookies(self):
        """Try to extract UID and SID from input_data cookie if not provided"""
        input_data_cookie = self.session.cookies.get('input_data')
        
        if input_data_cookie and (not self.uid or not self.sid):
            decoded = unquote(input_data_cookie)
            # Look for uid and sid patterns
            uid_match = re.search(r'uid%22%3Bs%3A8%3A%22(\d+)%22', decoded)
            sid_match = re.search(r'sid%22%3Bs%3A4%3A%22(\d+)%22', decoded)
            
            if uid_match and not self.uid:
                self.uid = uid_match.group(1)
                print(f"✅ Extracted UID from cookies: {self.uid}")
            
            if sid_match and not self.sid:
                self.sid = sid_match.group(1)
                print(f"✅ Extracted SID from cookies: {self.sid}")
    
    def validate_inputs(self):
        """Validate that required inputs are available"""
        missing = []
        if not self.uid:
            missing.append("UID")
        if not self.sid:
            missing.append("SID/Zone")
        if not self.productid:
            missing.append("Product ID")
        
        if missing:
            print(f"❌ Missing required inputs: {', '.join(missing)}")
            print("\nPlease provide them when initializing the bot:")
            print("  bot = SmileOneBot(uid='YOUR_UID', sid='YOUR_SID', productid='YOUR_PRODUCT_ID')")
            return False
        
        print(f"\n📌 Using:")
        print(f"   - UID: {self.uid}")
        print(f"   - SID/Zone: {self.sid}")
        print(f"   - Product ID: {self.productid}")
        return True
    
    def check_role(self):
        """Step 1: Check game role"""
        print("\n📋 Step 1: Checking game role...")
        
        url = "https://www.smile.one/br/merchant/game/checkrole"
        params = {"product": "magicchessgogo"}
        data = {
            "uid": self.uid,
            "sid": self.sid,
            "checkrole": "1"
        }
        
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        }
        
        try:
            response = self.session.post(url, params=params, data=data, headers=headers)
            
            if response.status_code == 200:
                print(f"✅ Role check successful")
                try:
                    result = response.json()
                    print(f"   Response: {json.dumps(result, indent=2)}")
                    
                    # Check if role exists
                    if result.get('code') == 0 or result.get('status') == 'success':
                        print("   ✅ Game role verified")
                    else:
                        print("   ⚠️ Game role may not exist")
                        
                except:
                    print(f"   Response: {response.text[:100]}")
                return True
            else:
                print(f"❌ Role check failed (Status: {response.status_code})")
                print(f"   Response: {response.text[:200]}")
                return False
                
        except Exception as e:
            print(f"❌ Error in role check: {e}")
            return False
    
    def check_customer(self):
        """Step 2: Check customer"""
        print("\n📋 Step 2: Checking customer...")
        
        url = "https://www.smile.one/merchant/customer"
        data = {"check": "check"}
        
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        }
        
        try:
            response = self.session.post(url, data=data, headers=headers)
            
            if response.status_code == 200:
                print(f"✅ Customer check successful")
                try:
                    result = response.json()
                    print(f"   Response: {json.dumps(result, indent=2)}")
                except:
                    print(f"   Response: {response.text[:100]}")
                return True
            else:
                print(f"❌ Customer check failed (Status: {response.status_code})")
                return False
                
        except Exception as e:
            print(f"❌ Error in customer check: {e}")
            return False
    
    def create_order(self):
        """Step 3: Create order"""
        print("\n📋 Step 3: Creating order...")
        
        url = "https://www.smile.one/br/merchant/game/createorder"
        params = {"product": "magicchessgogo"}
        data = {
            "uid": self.uid,
            "sid": self.sid,
            "productid": self.productid,
            "channel_method": "smilecoin",
            "external": "false"
        }
        
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        }
        
        try:
            response = self.session.post(url, params=params, data=data, headers=headers)
            
            if response.status_code == 200:
                print(f"✅ Order created successfully")
                try:
                    result = response.json()
                    print(f"   Response: {json.dumps(result, indent=2)}")
                    
                    # Extract flowid from different possible response formats
                    if isinstance(result, dict):
                        if 'flowid' in result:
                            self.flowid = result['flowid']
                        elif 'data' in result and isinstance(result['data'], dict):
                            if 'flowid' in result['data']:
                                self.flowid = result['data']['flowid']
                        elif 'order' in result and isinstance(result['order'], dict):
                            if 'flowid' in result['order']:
                                self.flowid = result['order']['flowid']
                    
                    if self.flowid:
                        print(f"   📌 Flow ID: {self.flowid}")
                    else:
                        print("   ⚠️ No flow ID in response")
                        
                except Exception as e:
                    print(f"   Response: {response.text[:200]}")
                    print(f"   ⚠️ Error parsing response: {e}")
                
                return True
            else:
                print(f"❌ Order creation failed (Status: {response.status_code})")
                print(f"   Response: {response.text[:200]}")
                return False
                
        except Exception as e:
            print(f"❌ Error in order creation: {e}")
            return False
    
    def process_payment(self):
        """Step 4: Process payment"""
        print("\n📋 Step 4: Processing payment...")
        
        if not self.flowid:
            print("❌ No flow ID available. Cannot process payment.")
            return False
        
        # Update headers for payment request
        payment_headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Dest': 'document'
        }
        
        url = "https://www.smile.one/merchant/game/pay"
        
        # Prepare payment data
        payment_data = {
            "_csrf": self.csrf_token if self.csrf_token else "",
            "uid": self.uid,
            "sid": self.sid,
            "email": "",
            "pay_methond": "smilecoin",
            "channel_method": "smilecoin",
            "flowid": self.flowid,
            "pay_country": "",
            "coupon_id": "",
            "zipcode": "",
            "product": "magicchessgogo",
            "productid": self.productid,
            "external": "false"
        }
        
        try:
            response = self.session.post(url, data=payment_data, headers=payment_headers, allow_redirects=True)
            
            if response.status_code in [200, 302]:
                print(f"✅ Payment processed")
                print(f"   Final URL: {response.url}")
                
                # Check response for success indicators
                response_text_lower = response.text.lower()
                if any(indicator in response_text_lower for indicator in ['success', 'thank', 'completed', '订单']):
                    print("   ✅ Payment appears successful!")
                elif response.status_code == 302:
                    print("   ⏩ Redirected - checking next page...")
                    
                    # Follow redirect if needed
                    if response.next:
                        redirect_response = self.session.get(response.next.url)
                        if redirect_response.status_code == 200:
                            print("   ✅ Redirect successful")
                
                return True
            else:
                print(f"❌ Payment failed (Status: {response.status_code})")
                print(f"   Response: {response.text[:200]}")
                return False
                
        except Exception as e:
            print(f"❌ Error in payment: {e}")
            return False
    
    def check_messages(self):
        """Step 5: Check messages (optional)"""
        print("\n📋 Step 5: Checking messages...")
        
        url = "https://www.smile.one/message/message"
        
        headers = {
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Dest': 'document'
        }
        
        try:
            response = self.session.get(url, headers=headers)
            
            if response.status_code == 200:
                print(f"✅ Messages checked")
                return True
            else:
                print(f"❌ Message check failed (Status: {response.status_code})")
                return False
                
        except Exception as e:
            print(f"❌ Error checking messages: {e}")
            return False
    
    def run_full_flow(self):
        """Execute the complete order flow"""
        print("="*50)
        print("🚀 Starting Magic Chess GoGo Order Flow")
        print("="*50)
        
        # Validate inputs first
        if not self.validate_inputs():
            return False
        
        # Step 1: Check role
        if not self.check_role():
            print("❌ Failed at role check. Aborting.")
            return False
        
        time.sleep(1)
        
        # Step 2: Check customer
        if not self.check_customer():
            print("❌ Failed at customer check. Aborting.")
            return False
        
        time.sleep(1)
        
        # Step 3: Create order
        if not self.create_order():
            print("❌ Failed at order creation. Aborting.")
            return False
        
        time.sleep(1)
        
        # Step 4: Process payment
        if not self.process_payment():
            print("❌ Failed at payment. Aborting.")
            return False
        
        time.sleep(1)
        
        # Step 5: Check messages (optional)
        self.check_messages()
        
        print("\n" + "="*50)
        print("✅ Magic Chess GoGo Order Flow Completed!")
        print("="*50)
        return True



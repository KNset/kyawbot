import requests
import urllib.parse
from typing import Dict, Any
import subprocess
import json


class SmileOneOrder:
    def __init__(self, region=None):
        self.cookie_file = "cookies.txt"
        if region == "BR":
            self.base_url = "https://www.smile.one"
        else:
            self.base_url = "https://www.smile.one/ph"
        
        # Create session first
        self.session = requests.Session()

        # Load cookies if file exists
        self.load_cookies()

        self.common_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "X-Requested-With": "XMLHttpRequest",
        }

        # Update session headers
        self.session.headers.update(self.common_headers)
        self.session.headers.update({
            "Referer": f"{self.base_url}/merchant/mobilelegends",
        })

    def load_cookies(self):
        """Load cookies from file and check if they're valid"""
        try:
            with open(self.cookie_file, "r", encoding="utf-8") as f:
                cookie_string = f.read().strip()
            if cookie_string:
                self.session.headers.update({"Cookie": cookie_string})
                print("[INFO] Cookies loaded from file")
                return True
        except FileNotFoundError:
            print("[ERROR] No cookies.txt found! You need to login first.")
        return False

    def check_session_valid(self):
        """Check if the current session is still valid"""
        url = f"{self.base_url}/merchant/customer"
        response = self.session.post(url, data="check=check")
        return response.status_code == 200 and response.json().get("code") == 200

    # ---------- Utility: extract csrf from cookie ----------
    def get_csrf(self):
        cookies = self.session.headers.get("Cookie", "")
        for item in cookies.split(";"):
            item = item.strip()
            if item.startswith("_csrf="):
                csrf_raw = item.split("=", 1)[1]
                return urllib.parse.unquote(csrf_raw)
        return None

    # ---------- Step 1 ----------
    def step1_check_customer(self):
        url = f"{self.base_url}/merchant/customer"

        headers = self.common_headers.copy()
        headers.update({
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "Accept": "application/json, text/javascript, */*; q=0.01",
        })

        data = "check=check"

        response = self.session.post(url, headers=headers, data=data)
        print("Step 1 Status:", response.status_code)
        if response.status_code != 200:
            print("❌ Session may be expired!")
            return None
        return response.json()

    # ---------- Step 2: Check Role ----------
    def step2_check_role(self, user_id: str, zone_id: str, product_id: str):
        """
        Step 2 — Check role before querying order
        """
        url = f"{self.base_url}/merchant/mobilelegends/checkrole"
        
        headers = self.common_headers.copy()
        headers.update({
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Origin": self.base_url,
            "Referer": f"{self.base_url}/merchant/mobilelegends?source=other",
            "Sec-Fetch-Site": "same-origin",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Dest": "empty",
        })
        
        payload = {
            "user_id": user_id,
            "zone_id": zone_id,
            "pid": product_id,
            "checkrole": "1",
            "pay_methond": "",
            "channel_method": ""
        }

        response = self.session.post(url, headers=headers, data=payload)
        print("Step 2 Check Role Status:", response.status_code)
        print("Step 2 Check Role Response:", response.text)
        
        try:
            return response.json() if response.status_code == 200 else None
        except Exception as e:
            print(f"Error parsing checkrole response: {e}")
            return {"error": "parse_error", "raw_response": response.text}

    # ---------- Step 3: Query order (replace with curl) ----------
    def step3_query_order(self, user_id: str, zone_id: str, product_id: str):
        """
        Step 3 — Query order before payment using exact curl command.
        """
        curl_cmd = [
            "curl", "-s", "-X", "POST",
            f"{self.base_url}/merchant/mobilelegends/query",
            "-H", "Content-Type: application/x-www-form-urlencoded",
            "-d", f"user_id={user_id}&zone_id={zone_id}&pid={product_id}&checkrole=&pay_methond=smilecoin&channel_method=smilecoin"
        ]

        result = subprocess.run(curl_cmd, capture_output=True, encoding='utf-8', errors='replace', text=True)
        response_text = result.stdout
        print("Step 3 Query Response:", response_text)

        try:
            # Sometimes curl output might contain headers or other info if not silent
            # Try to find the JSON object part
            if "{" in response_text:
                json_start = response_text.find("{")
                json_end = response_text.rfind("}") + 1
                json_str = response_text[json_start:json_end]
                json_data = json.loads(json_str)
            else:
                json_data = json.loads(response_text)
        except Exception:
            return {
                "code": result.returncode,
                "error": "invalid_json",
                "raw": response_text
            }

        if json_data.get("code") != 200:
            return {
                "code": json_data.get("code", result.returncode),
                "error": "query_failed",
                "raw": json_data
            }

        flowid = json_data.get("flowid")
        return {
            "code": 200,
            "flowid": flowid,
            "username": json_data.get("username"),
            "data": json_data
        }

    # ---------- Step 4: Pay order (FIXED with x-redirect handling) ----------
    def step4_pay_order(self, flowid: str, user_id: str, zone_id: str, product_id: str):
        url = f"{self.base_url}/merchant/mobilelegends/pay"

        csrf_token = self.get_csrf()
        if not csrf_token:
            raise ValueError("❌ No _csrf found in cookie")

        headers = self.common_headers.copy()
        headers.update({
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Origin": self.base_url,
            "Referer": f"{self.base_url}/merchant/mobilelegends",
        })

        data = {
            "_csrf": csrf_token,
            "user_id": user_id,
            "zone_id": zone_id,
            "pay_methond": "smilecoin",
            "product_id": product_id,
            "channel_method": "smilecoin",
            "flowid": flowid,
            "email": "",
            "coupon_id": ""
        }

        print(f"[DEBUG] Pay data: {data}")
        print(f"[DEBUG] CSRF token: {csrf_token}")

        response = self.session.post(url, headers=headers, data=data, allow_redirects=False)
        print("Step 4 Pay Status:", response.status_code)
        print("Step 4 Response Headers:", dict(response.headers))
        
        # Check for x-redirect header (indicates login required)
        x_redirect = response.headers.get("x-redirect")
        if x_redirect and "login" in x_redirect:
            print("❌ SESSION EXPIRED! Redirected to login page.")
            print("💡 You need to refresh your cookies by logging in again.")
            return {
                "status": "session_expired",
                "redirect_url": x_redirect,
                "code": response.status_code,
                "message": "Session expired, login required"
            }

        redirect_url = response.headers.get("Location")
        print("Redirect →", redirect_url)

        # If no redirect but 200 status, check response content
        if response.status_code == 200 and not redirect_url:
            try:
                json_response = response.json()
                print("Step 4 JSON Response:", json_response)
                return {
                    "status": "direct_response",
                    "code": response.status_code,
                    "content": response.text,
                    "json": json_response
                }
            except:
                return {
                    "status": "no_redirect_200",
                    "code": response.status_code,
                    "content": response.text
                }
        
        if not redirect_url:
            return {
                "status": "no_redirect",
                "code": response.status_code,
                "content": response.text,
                "headers": dict(response.headers)
            }

        if redirect_url.startswith("/"):
            redirect_url = self.base_url + redirect_url

        # Follow the redirect
        follow_response = self.session.get(redirect_url, headers=headers)
        print("Redirect Follow Status:", follow_response.status_code)
        
        return {
            "status": "redirect_followed",
            "redirect_url": redirect_url,
            "final_status": follow_response.status_code,
            "content": follow_response.text
        }

    # ---------- Step 5: Get message ----------
    def step5_get_message(self):
        url = f"{self.base_url}/message/message"

        headers = self.common_headers.copy()
        headers.update({
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        })

        response = self.session.get(url, headers=headers)
        print("Step 5 Message Status:", response.status_code)

        if response.status_code == 200:
            return response.text

        return None

    # ---------- Execute full flow ----------
    def execute_order_flow(self, user_id: str, zone_id: str, product_id: str):
        print("\n=== Starting Smile.One Order Flow ===")
        print(f"User: {user_id}  Zone: {zone_id}  Product: {product_id}")

        # First check if session is valid
        if not self.check_session_valid():
            print("❌ Session is not valid! Please login again and update cookies.txt")
            return {"error": "session_expired", "message": "Please login again"}

        step1 = self.step1_check_customer()
        if not step1:
            print("❌ Step 1 failed - session issue")
            return {"error": "session_issue"}

        step2 = self.step2_check_role(user_id, zone_id, product_id)
        step3 = self.step3_query_order(user_id, zone_id, product_id)

        if not step3 or step3.get("code") != 200:
            print(f"This is step 3 : {step3}")
            print("❌ Step 3 failed")
            return {"error": "query failed"}

        flowid = step3.get("flowid")
        print("FlowID:", flowid)

        step4 = self.step4_pay_order(flowid, user_id, zone_id, product_id)
        
        # Check if payment failed due to session
        if step4.get("status") == "session_expired":
            return {
                "step1": step1,
                "step2": step2,
                "step3": step3,
                "step4": step4,
                "success": False,
                "error": "session_expired"
            }
            
        step5 = self.step5_get_message()

        return {
            "step1": step1,
            "step2": step2,
            "step3": step3,
            "step4": step4,
            "step5": step5,
            "success": True
        }

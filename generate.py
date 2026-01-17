import browser_cookie3

DOMAIN = "smile.one"  # <-- change to your target domain
OUTPUT = "cookies.txt"

def save_cookie_header():
    print("[*] Reading cookies from VPS browser profile...")

    # Load cookies from Chrome
    cookies = browser_cookie3.chrome(domain_name=DOMAIN)

    # Convert to header string
    header_string = "; ".join([f"{c.name}={c.value}" for c in cookies])

    with open(OUTPUT, "w") as f:
        f.write(header_string)

    print(f"[✓] Saved to {OUTPUT}")
    print(header_string)


if __name__ == "__main__":
    save_cookie_header()

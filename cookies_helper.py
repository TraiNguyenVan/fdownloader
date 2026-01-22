import json
import os

def parse_netscape_cookies(file_path):
    cookies = []
    with open(file_path, 'r') as f:
        for line in f:
            if line.startswith('#') or not line.strip():
                continue
            parts = line.strip().split('\t')
            if len(parts) >= 7:
                cookie = {
                    'domain': parts[0],
                    'path': parts[2],
                    'secure': parts[3] == 'TRUE',
                    'expires': int(parts[4]) if parts[4] != '0' else -1,
                    'name': parts[5],
                    'value': parts[6]
                }
                # Playwright expects 'sameSite' and 'httpOnly' sometimes, 
                # but basic keys often suffice. 
                # Ensure domain starts with dot if needed or clean it up.
                cookies.append(cookie)
    return cookies

def convert_to_playwright_json(input_path, output_path):
    if not os.path.exists(input_path):
        print(f"Cookie file not found: {input_path}")
        return

    cookies = parse_netscape_cookies(input_path)
    state = {"cookies": cookies, "origins": []}
    
    with open(output_path, 'w') as f:
        json.dump(state, f, indent=2)
    print(f"Converted {len(cookies)} cookies to {output_path}")

if __name__ == "__main__":
    # Example usage: check if cookies.txt exists, if so, convert to facebook_cookies.json
    if os.path.exists("cookies.txt") and not os.path.exists("facebook_cookies.json"):
        convert_to_playwright_json("cookies.txt", "facebook_cookies.json")

import argparse
import sys
import os
import json
import time
import requests
from playwright.sync_api import sync_playwright

DOWNLOAD_DIR = "/app/downloads"

def load_cookies(context, cookie_file):
    if os.path.exists(cookie_file):
        print(f"Loading cookies from {cookie_file}...")
        try:
            with open(cookie_file, 'r') as f:
                state = json.load(f)
                # Handle both 'state.json' format (Playwright storage state) and simple list of cookies
                if isinstance(state, dict) and "cookies" in state:
                    context.add_cookies(state["cookies"])
                elif isinstance(state, list):
                    context.add_cookies(state)
                else:
                    print("Unknown cookie format. Expecting list or dict with 'cookies' key.")
        except Exception as e:
            print(f"Error loading cookies: {e}")
    else:
        print(f"Warning: {cookie_file} not found. Proceeding without specific auth (public posts might work).")

def download_image(url, filename, cookies=None):
    try:
        # Use requests for efficient binary download, sharing cookies if possible?
        # Actually, simply using requests.get might fail if the image URL requires auth.
        # But usually FB cdn URLs are public once generated.
        # Let's try requests first.
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        res = requests.get(url, headers=headers, stream=True)
        if res.status_code == 200:
            with open(filename, 'wb') as f:
                for chunk in res.iter_content(1024):
                    f.write(chunk)
            print(f"Saved: {filename}")
            return True
        else:
            print(f"Failed to download {url}: Status {res.status_code}")
            return False
    except Exception as e:
        print(f"Error downloading {url}: {e}")
        return False

def main(post_url):
    with sync_playwright() as p:
        browser = p.firefox.launch(headless=True)
        # Use a larger viewport to ensure images are loaded/visible
        context = browser.new_context(
            viewport={"width": 1366, "height": 768},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0"
        )
        
        load_cookies(context, "/app/facebook_cookies.json")
        page = context.new_page()
        
        print(f"Navigating to {post_url}...")
        try:
            page.goto(post_url, wait_until="domcontentloaded", timeout=60000)
            time.sleep(5) # Allow meaningful render
        except Exception as e:
            print(f"Navigation warning: {e}")

        if not os.path.exists(DOWNLOAD_DIR):
            os.makedirs(DOWNLOAD_DIR)
        
        # Check login
        if "log in" in page.title().lower():
             print("Detected Login Wall! Cookies might be invalid.")
             page.screenshot(path=os.path.join(DOWNLOAD_DIR, "debug_login_wall.png"))
             return

        # Attempt to find the post content
        # Strategy: Look for "Photo" style attachments.
        
        print("Scanning for clickable images...")
        
        # Candidates: 
        # 1. Standard img tags
        # 2. Divs with role=img
        # 3. Links wrapping images
        
        candidates = page.locator('div[role="main"] img, div[role="feed"] img, div[role="article"] img').all()
        if not candidates:
             # Fallback to general search
             candidates = page.locator('img').all()
        
        print(f"Found {len(candidates)} candidate 'img' tags.")
        
        clicked = False
        
        # Sort by size (largest first) to avoid clicking emojis or icons
        valid_candidates = []
        for img in candidates:
            if not img.is_visible(): continue
            box = img.bounding_box()
            if box and box['width'] > 70 and box['height'] > 70:
                valid_candidates.append((img, box['width'] * box['height']))
        
        # Sort descending by area
        valid_candidates.sort(key=lambda x: x[1], reverse=True)
        
        print(f"Filtered to {len(valid_candidates)} images > 70x70.")
        
        # Prepare a function to check theater mode
        def is_theater_open():
             # Check broadly for dialogs or the close button
             # Use first to avoid strict mode errors if multiple dialogs exist
             return (page.locator('[role="dialog"]').first.is_visible() or 
                     page.locator('[aria-label="Close"]').first.is_visible() or
                     page.locator('[aria-label="Đóng"]').first.is_visible() or # Vietnamese
                     "photo" in page.url or "theater" in page.url)

        # Check if already open (maybe from a previous stray click or default state)
        if is_theater_open():
             print("Theater mode already detected! skipping clicks.")
             clicked = True
        else:
            for i, (img, area) in enumerate(valid_candidates[:5]): 
                print(f"Trying candidate {i} (Area: {area})...")
                try:
                    # Check before clicking (maybe previous iteration worked but we missed the check?)
                    if is_theater_open():
                         print("Theater mode detected (late)!")
                         clicked = True
                         break

                    img.scroll_into_view_if_needed()
                    time.sleep(1)
                    img.click(timeout=5000, force=True)
                    time.sleep(3)
                    
                    if is_theater_open():
                        print("Theater mode detected after click!")
                        clicked = True
                        break
                    
                    print("Click didn't trigger theater mode. Trying next...")
                    
                except Exception as e:
                    print(f"Click failed: {e}")
        
        if not clicked:
            print("Failed to enter theater mode.")
            page.screenshot(path=os.path.join(DOWNLOAD_DIR, "debug_failed_click.png"))
            browser.close()
            return

        # --- In Theater Mode ---
        print("Entered Theater Mode. Starting download loop.")
        
        seen_urls = set()
        seen_fbids = set()
        count = 0
        consecutive_errors = 0
        
        while True:
            time.sleep(1) 
            
            # 0. Cycle detection via URL (Run specific check first)
            try:
                current_url = page.url
                # Extract fbid from URL if possible
                import re
                fbid_match = re.search(r'[?&]fbid=(\d+)', current_url)
                current_id = fbid_match.group(1) if fbid_match else current_url
                
                if current_id in seen_fbids:
                    print(f"Cycle detected! We are back at ID/URL: {current_id[-20:]}. Stopping.")
                    break
                seen_fbids.add(current_id)
            except Exception as e:
                print(f"Cycle check error: {e}")

            try:
                # Find dialog context if possible
                dialog = page.locator('[role="dialog"]').first
                if not dialog.is_visible():
                    dialog = page.locator('body') # Fallback
                
                # Best selector for high-res
                # Try multiple logic
                spotlight_found = False
                src = None
                
                # 1. Look for image with specific attributes
                 # English and Vietnamese aria labels for the main image?
                 # Usually the main image structure is stable.
                candidates = dialog.locator('img').all()
                
                # Heuristic: The largest image in the dialog is the one we want.
                largest_area = 0
                best_img = None
                
                for img in candidates:
                     if not img.is_visible(): continue
                     box = img.bounding_box()
                     if box:
                         area = box['width'] * box['height']
                         if area > largest_area:
                             largest_area = area
                             best_img = img
                
                if best_img and largest_area > 20000: # reasonable size
                     src = best_img.get_attribute('src')
                
                if src and src not in seen_urls:
                    seen_urls.add(src)
                    count += 1
                    filename = os.path.join(DOWNLOAD_DIR, f"image_{count:03d}.jpg")
                    print(f"Downloading {count}: {src[:40]}...")
                    download_image(src, filename)
                    consecutive_errors = 0
                else:
                    time.sleep(1)
                    consecutive_errors += 1
                    if consecutive_errors > 8:
                         print(f"No new image found for a while. Stopping.")
                         break

                # Next button
                # Add Vietnamese label "Ảnh tiếp theo"
                next_selectors = [
                    '[aria-label="Next photo"]', 
                    '[aria-label="Next"]',
                    '[aria-label="Ảnh tiếp theo"]', 
                    '[aria-label="Tiếp"]'
                ]
                
                clicked_next = False
                for sel in next_selectors:
                    btn = dialog.locator(sel)
                    if btn.count() > 0 and btn.first.is_visible():
                        print(f"Clicking next: {sel}")
                        btn.first.click()
                        clicked_next = True
                        time.sleep(2)
                        break
                
                if not clicked_next:
                    print("Next button hidden. Trying keyboard and coordinate click...")
                    page.keyboard.press("ArrowRight")
                    time.sleep(1)
                    
                    # Coordinate fallback: Click right side of screen (95% width, 50% height)
                    vp = page.viewport_size
                    if vp:
                        x = vp['width'] * 0.95
                        y = vp['height'] * 0.5
                        print(f"Clicking valid coordinate fallback at {x},{y}")
                        page.mouse.click(x, y)
                    
                    time.sleep(2)
            
            except Exception as e:
                print(f"Error in loop: {e}")
                break

        print(f"Total downloaded: {count}")
        browser.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python main.py <facebook_post_url>")
        # Default for testing if no arg provided
        sys.exit(1)
        
    url = sys.argv[1]
    main(url)

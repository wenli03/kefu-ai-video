from playwright.sync_api import sync_playwright
import time, os

output_dir = os.path.join(os.path.dirname(__file__), 'screenshots')
os.makedirs(output_dir, exist_ok=True)

p = sync_playwright().start()
b = p.chromium.launch(headless=True)
page = b.new_page(viewport={"width": 420, "height": 812})

# 1. Initial page
page.goto("http://localhost:5173/customer", wait_until="networkidle")
page.wait_for_timeout(2000)
page.screenshot(path=os.path.join(output_dir, "01-initial.png"))
print("01-initial.png")

# 2. Click call button
page.locator("button", has_text="联系客服").click()
page.wait_for_timeout(2000)
page.screenshot(path=os.path.join(output_dir, "02-connected.png"))
print("02-connected.png")

# 3. Send message and get response
page.locator("input[placeholder]").fill("理赔")
page.locator("button", has_text="发送").click()
page.wait_for_timeout(3000)
page.screenshot(path=os.path.join(output_dir, "03-claim-response.png"))
print("03-claim-response.png")

# 4. Send goodbye
page.locator("input[placeholder]").fill("再见")
page.locator("button", has_text="发送").click()
page.wait_for_timeout(3000)
page.screenshot(path=os.path.join(output_dir, "04-goodbye.png"))
print("04-goodbye.png")

# 5. After session ended (back to idle)
page.wait_for_timeout(3000)
page.screenshot(path=os.path.join(output_dir, "05-session-ended.png"))
print("05-session-ended.png")

b.close()
p.stop()
print("Done - 5 screenshots saved")

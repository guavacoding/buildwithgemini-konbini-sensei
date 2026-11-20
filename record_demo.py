import os
import time
from playwright.sync_api import sync_playwright

output_dir = "/config/Desktop/BuildWithGemini/konbini-sensei/demo_recordings"
os.makedirs(output_dir, exist_ok=True)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(
        record_video_dir=output_dir,
        record_video_size={"width": 1280, "height": 720},
        viewport={"width": 1280, "height": 720}
    )
    page = context.new_page()

    print("Opening page...")
    page.goto("http://localhost:8080")
    page.wait_for_selector("#input")
    time.sleep(2)

    # Prompt 1: Core app domain (Japanese convenience store conversation learning)
    prompt1 = "我想在便利商店買便當並微波加熱，店員通常會問我什麼？我該怎麼用日文回答？"
    print("Typing prompt 1...")
    page.click("#input")
    for ch in prompt1:
        page.keyboard.type(ch, delay=40)
    time.sleep(0.5)
    page.click("button")

    print("Waiting for prompt 1 response...")
    # Wait until user message bubble and agent bubble appear
    page.wait_for_selector(".msg.user")
    # Wait for the agent's bubble (second .msg element)
    page.wait_for_function("document.querySelectorAll('.msg').length >= 2", timeout=90000)
    print("Prompt 1 response received!")
    time.sleep(6)

    # Prompt 2: Tool call, database lookup, and image generation
    prompt2 = "我想買唐揚雞便當，請幫我查詢店內庫存並生成一張美味的商品插圖！"
    print("Typing prompt 2...")
    page.click("#input")
    for ch in prompt2:
        page.keyboard.type(ch, delay=40)
    time.sleep(0.5)
    page.click("button")

    print("Waiting for prompt 2 response (including tool execution & image generation)...")
    page.wait_for_function("document.querySelectorAll('.msg').length >= 4", timeout=120000)
    print("Prompt 2 response received!")
    time.sleep(8)

    # Scroll smoothly to show the full result
    page.evaluate("document.getElementById('log').scrollTop = document.getElementById('log').scrollHeight")
    time.sleep(3)

    print("Closing browser context...")
    context.close()
    video_path = page.video.path()
    browser.close()
    print("Recorded video saved at:", video_path)


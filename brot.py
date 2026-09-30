from playwright.sync_api import sync_playwright

captured = []

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(user_agent="TaskCrawler/1.0", locale="fa-IR")
    page = context.new_page()

    def on_response(response):
        if response.request.resource_type in ("xhr", "fetch"):
            captured.append(response)

    page.on("response", on_response)

    # اینجا (فقط برای دیباگ) صبر می‌کنیم شبکه آروم بگیره، نه فقط domcontentloaded
    page.goto("http://podcast.iranseda.ir/", wait_until="networkidle", timeout=30000)

    print("=== XHR/fetch calls موقع لود صفحه اصلی ===")
    for r in captured:
        print(r.status, r.url)

    content = page.content()
    print("\nطول content بعد از networkidle:", len(content))
    print("آیا 'podcasthome' توش هست؟:", "podcasthome" in content)

    print("\n=== بدنه‌ی پاسخ‌هایی که شبیه JSON هستن ===")
    for r in captured:
        try:
            body = r.text()
            print("\n---", r.url, "---")
            print(body[:1500])
        except Exception as e:
            print("(نتونستم body رو بخونم برای", r.url, "-", e, ")")

    browser.close()
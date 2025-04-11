from utils import ocr_math_expression, process_math_expression
from playwright.sync_api import sync_playwright
import time

with sync_playwright() as p:
    browser = p.firefox.launch(headless=False, args=["--no-sandbox"], firefox_user_prefs={
        "pdfjs.disabled": False,
        "browser.download.folderList": 2,
        "browser.download.manager.showWhenStarting": False,
        "browser.download.dir": "/home/adam/Documents/Dev/judgement_scraper_playwright/pdfs/",
        "browser.helperApps.neverAsk.saveToDisk": "application/pdf",
        "browser.download.manager.useWindow": False,
        "browser.download.manager.showAlertOnComplete": False,
        "browser.download.manager.focusWhenStarting": False,
    })
    context = browser.new_context(
        accept_downloads=True,
    )
    page = context.new_page()

    TARGET_URL = "https://judgments.ecourts.gov.in/pdfsearch/"

    # Navigate to the web page
    page.goto(TARGET_URL)

    captcha_image = page.query_selector("#captcha_image") 
    captcha_image.screenshot(path="captcha.png")

    image_path = "captcha.png"
    extracted_text = ocr_math_expression("captcha.png")
    captcha_result = process_math_expression(extracted_text)
    final_result = captcha_result.split("\n")[-1].split(":")[-1].strip()
    page.fill("#captcha", final_result)
    page.click("#main_search")
    time.sleep(5) 

    url = "https://judgments.ecourts.gov.in/pdfsearch/?p=pdf_search/openpdfcaptcha"

    jsession_id = context.cookies()[0]['value']
    judgement_search_id = context.cookies()[2]['value']
    
    page.click("#link_0")
    page.click("button#download.toolbarButton.hiddenMediumView")
    with page.expect_download() as download_info:
        # page.click("button.toolbarButton.download", timeout=5000)
        # page.click(".toolbarButton[title='Download']")
        page.click("button[data-l10n-id='download']")
        
    # Save the downloaded file
    download = download_info.value
    download.save_as("pdfs/2025_3_516_539.pdf")
    print(f"PDF downloaded to")
    time.sleep(10)

    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:131.0) Gecko/20100101 Firefox/131.0",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Referer": "https://judgments.ecourts.gov.in/",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "X-Requested-With": "XMLHttpRequest",
        "Origin": "https://judgments.ecourts.gov.in",
        "Sec-GPC": "1",
        "Connection": "keep-alive",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
        "TE": "trailers",
        # "Cookie": "JUDGEMENTSSEARCH_SESSID=3lqtn5slhb32rgivlf7vgrsg85; JSESSION=96295920"
        "Cookie": f"JUDGEMENTSSEARCH_SESSID={judgement_search_id}; JSESSION={jsession_id}",
    }

    data = {
        "val": "0",
        "lang_flg": "undefined",
        "path": "2025_3_516_539",
        "citation_year": "2025",
        "fcourt_type": "3",
        "file_type": "undefined",
        "nc_display": "2025INSC347",
        "ajax_req": "true",
        "app_token": "",
    }

    response = page.request.post(url, headers=headers, data=data)
    print(response.status)
    print(response.text())

    context.close()

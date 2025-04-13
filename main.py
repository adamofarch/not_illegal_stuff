from utils import ocr_math_expression, process_math_expression
from playwright.sync_api import sync_playwright
import requests
import time
import os

with sync_playwright() as p:
    browser = p.firefox.launch(
        headless=False, # There are numourous issues with headless mode right now
        args=["--no-sandbox"], 
        firefox_user_prefs={
            "pdfjs.disabled": False,
        }
    )

    context = browser.new_context(
        accept_downloads=True,
        viewport={"width": 1920, "height": 1080},
    )
    page = context.new_page()

    TARGET_URL = "https://judgments.ecourts.gov.in/pdfsearch/"

    try:
        page.goto(TARGET_URL) # This usually times out for some reason (might be fixed if rotating proxies with excellent speeds or providers are used) but when it doesn't, it works like a charm
    except Exception as e:
        print(f"Error navigating to {TARGET_URL}: {e}")
        context.close()

    captcha_image = page.query_selector("#captcha_image") 
    captcha_image.screenshot(path="captcha.png")

    image_path = "captcha.png"
    extracted_text = ocr_math_expression("captcha.png")
    captcha_result = process_math_expression(extracted_text) 
    final_result = captcha_result.split("\n")[-1].split(":")[-1].strip()
    page.fill("#captcha", final_result)
    page.click("#main_search")
    time.sleep(5) 
    
    while page.wait_for_selector("#example_pdf_next"):
        for i in range(0, 10):
            link = page.query_selector(f"#link_{i}")
            pdf_name = link.get_attribute("aria-label").split(" pdf")[0].strip()
            print("PDF Name:", pdf_name)
            page.click(f"#link_{i}")

            object_xpath = "//object[contains(@data, '.pdf')]" 
            page.wait_for_selector(object_xpath)
            object_element = page.query_selector(object_xpath)

            if object_element:
                data_attribute = object_element.get_attribute("data")

                if data_attribute:

                    pdf_url = "https://judgments.ecourts.gov.in/" + data_attribute
                    try:
                        # Need to use requests instead of playwright's requests, they're gonna suck since they don't support stream and chunked transfer
                        response = requests.get(pdf_url, stream=True) 
                        response.raise_for_status()

                        output_path = os.path.join(os.getcwd(), f"pdfs/{pdf_name}.pdf")
                        with open(output_path, "wb") as f:
                            for chunk in response.iter_content(chunk_size=1048576):
                                f.write(chunk)

                        print(f"Successfully downloaded PDF to: {output_path}")
                    except Exception as e:
                        print(f"Error downloading PDF: {e}")

                    page.click("//button[@id='modal_close' and ./span[@aria-hidden='true']]")
        page.click("#example_pdf_next")

    
    """BEWARE: THIS REQUEST THING IS ASS RIGHT NOW, I have tried building request manually and 
        engineered every header, it usually breaks, works only when I put in already validated 
        JUDGEMENTSSEARCH_SESSID and JSESSION, sometimes it uses a third cookie which is obviously stored but
        the pattern when and why does it use it is still a mystery to me""" 

    # url = "https://judgments.ecourts.gov.in/pdfsearch/?p=pdf_search/openpdfcaptcha"

    # jsession_id = context.cookies()[0]['value']
    # judgement_search_id = context.cookies()[2]['value']
    #
    # time.sleep(10)
    #
    # headers = {
    #     "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:131.0) Gecko/20100101 Firefox/131.0",
    #     "Accept": "application/json, text/javascript, */*; q=0.01",
    #     "Accept-Language": "en-US,en;q=0.5",
    #     "Accept-Encoding": "gzip, deflate, br, zstd",
    #     "Referer": "https://judgments.ecourts.gov.in/",
    #     "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    #     "X-Requested-With": "XMLHttpRequest",
    #     "Origin": "https://judgments.ecourts.gov.in",
    #     "Sec-GPC": "1",
    #     "Connection": "keep-alive",
    #     "Sec-Fetch-Dest": "empty",
    #     "Sec-Fetch-Mode": "cors",
    #     "Sec-Fetch-Site": "same-origin",
    #     "TE": "trailers",
    #     # "Cookie": "JUDGEMENTSSEARCH_SESSID=3lqtn5slhb32rgivlf7vgrsg85; JSESSION=96295920"
    #     "Cookie": f"JUDGEMENTSSEARCH_SESSID={judgement_search_id}; JSESSION={jsession_id}",
    # }
    #
    # data = {
    #     "val": "0",
    #     "lang_flg": "undefined",
    #     "path": "2025_3_516_539",
    #     "citation_year": "2025",
    #     "fcourt_type": "3",
    #     "file_type": "undefined",
    #     "nc_display": "2025INSC347",
    #     "ajax_req": "true",
    #     "app_token": "",
    # }
    #
    # response = page.request.post(url, headers=headers, data=data)
    # print(response.status)
    # print(response.text())

    context.close()

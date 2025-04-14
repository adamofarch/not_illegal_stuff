from utils import ocr_math_expression, process_math_expression
from playwright.sync_api import sync_playwright, TimeoutError
import requests
import time
import os
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("scraper.log"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


def solve_captcha(page, captcha_id="captcha_image", captcha_input_id="captcha"):
    """Solve a captcha on the page"""
    try:
        # Wait for captcha image to be visible
        page.wait_for_selector(f"#{captcha_id}", timeout=5000)

        # Screenshot the captcha
        captcha_image = page.query_selector(f"#{captcha_id}")
        captcha_image.screenshot(path="captcha.png")

        # Process the captcha
        extracted_text = ocr_math_expression("captcha.png")
        captcha_result = process_math_expression(extracted_text)
        final_result = captcha_result.split("\n")[-1].split(":")[-1].strip()

        # Fill in the captcha
        page.fill(f"#{captcha_input_id}", final_result)

        logger.info(f"Solved captcha: {extracted_text} = {final_result}")
        return True
    except Exception as e:
        logger.error(f"Error solving captcha: {e}")
        return False


def handle_pdf_modal_captcha(page):
    """Handle the captcha that appears in the PDF modal"""
    try:
        # Check if the PDF modal captcha is visible
        if page.query_selector("#captcha_image_pdf") is not None:
            logger.info("PDF modal captcha detected")

            # Solve the captcha
            captcha_image = page.query_selector("#captcha_image_pdf")
            captcha_image.screenshot(path="captcha_pdf.png")

            extracted_text = ocr_math_expression("captcha_pdf.png")
            captcha_result = process_math_expression(extracted_text)
            final_result = captcha_result.split("\n")[-1].split(":")[-1].strip()

            # Fill in the captcha
            page.fill("#captchapdf", final_result)

            # Click the submit button
            submit_button = page.query_selector("input[value='submit']")
            if submit_button:
                submit_button.click()

            logger.info(f"Solved PDF modal captcha: {extracted_text} = {final_result}")
            return True
    except Exception as e:
        logger.error(f"Error handling PDF modal captcha: {e}")

    return False


def create_directories():
    """Create necessary directories for downloads"""
    os.makedirs("pdfs", exist_ok=True)


def download_pdf(pdf_url, pdf_name):
    """Download a PDF file"""
    try:
        response = requests.get(pdf_url, stream=True)
        response.raise_for_status()

        output_path = os.path.join(os.getcwd(), f"pdfs/{pdf_name}.pdf")
        with open(output_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=1048576):
                f.write(chunk)

        logger.info(f"Successfully downloaded PDF to: {output_path}")
        return True
    except Exception as e:
        logger.error(f"Error downloading PDF: {e}")
        return False


def main():
    create_directories()

    with sync_playwright() as p:
        browser = p.firefox.launch(
            headless=False,
            args=["--no-sandbox"],
            firefox_user_prefs={
                "pdfjs.disabled": False,
            },
        )

        context = browser.new_context(
            accept_downloads=True,
            viewport={"width": 1920, "height": 1080},
        )
        page = context.new_page()

        TARGET_URL = "https://judgments.ecourts.gov.in/pdfsearch/"

        try:
            page.goto(TARGET_URL)
            logger.info(f"Successfully navigated to {TARGET_URL}")
        except Exception as e:
            logger.error(f"Error navigating to {TARGET_URL}: {e}")
            context.close()
            return

        # Solve initial captcha
        if not solve_captcha(page):
            logger.error("Failed to solve initial captcha")
            context.close()
            return

        # Click search button
        page.click("#main_search")
        time.sleep(2)

        # Wait for results page to load
        try:
            page.wait_for_selector("#example_pdf", timeout=10000)
            logger.info("Successfully loaded search results page")
        except TimeoutError:
            logger.error("Timed out waiting for search results")
            context.close()
            return

        # Initialize pagination variables
        current_page = 1
        keep_scraping = True

        while keep_scraping:
            logger.info(f"Processing page {current_page} of results")

            # Process each PDF link on the current page
            try:
                # Get number of results on this page
                rows = page.query_selector_all("#example_pdf tbody tr")
                num_results = len(rows)
                logger.info(f"Found {num_results} results on page {current_page}")

                for i in range(0, num_results):
                    # Try to find and click the link
                    try:
                        link = page.query_selector(f"#link_{i}")
                        if not link:
                            logger.warning(
                                f"Link #{i} not found on page {current_page}"
                            )
                            continue

                        pdf_name = (
                            link.get_attribute("aria-label").split(" pdf")[0].strip()
                        )
                        logger.info(f"Processing PDF #{i}: {pdf_name}")
                        link.click()

                        # Wait for PDF object to load or for captcha to appear
                        try:
                            object_xpath = "//object[contains(@data, '.pdf')]"
                            page.wait_for_selector(object_xpath, timeout=5000)
                            object_element = page.query_selector(object_xpath)

                            if object_element:
                                data_attribute = object_element.get_attribute("data")

                                if data_attribute:
                                    pdf_url = (
                                        "https://judgments.ecourts.gov.in/"
                                        + data_attribute
                                    )
                                    download_pdf(pdf_url, pdf_name)

                                # Close the modal
                                close_button = page.query_selector(
                                    "//button[@id='modal_close' and ./span[@aria-hidden='true']]"
                                )
                                if close_button:
                                    close_button.click()
                                    time.sleep(1)

                        except TimeoutError:
                            # Check if captcha appeared instead
                            if handle_pdf_modal_captcha(page):
                                # Try again to wait for the PDF
                                try:
                                    page.wait_for_selector(object_xpath, timeout=5000)
                                    object_element = page.query_selector(object_xpath)

                                    if object_element:
                                        data_attribute = object_element.get_attribute(
                                            "data"
                                        )

                                        if data_attribute:
                                            pdf_url = (
                                                "https://judgments.ecourts.gov.in/"
                                                + data_attribute
                                            )
                                            download_pdf(pdf_url, pdf_name)

                                    # Close the modal
                                    close_button = page.query_selector(
                                        "//button[@id='modal_close' and ./span[@aria-hidden='true']]"
                                    )
                                    if close_button:
                                        close_button.click()
                                        time.sleep(1)
                                except TimeoutError:
                                    logger.error(
                                        f"Failed to load PDF after solving captcha for {pdf_name}"
                                    )
                                    # Try to close the modal anyway
                                    try:
                                        close_button = page.query_selector(
                                            "//button[@id='modal_close' and ./span[@aria-hidden='true']]"
                                        )
                                        if close_button:
                                            close_button.click()
                                            time.sleep(1)
                                    except Exception as e:
                                        logger.error(f"Error closing modal: {e}")
                            else:
                                logger.error(
                                    f"PDF load timeout and no captcha detected for {pdf_name}"
                                )
                                # Try to close the modal anyway
                                try:
                                    close_button = page.query_selector(
                                        "//button[@id='modal_close' and ./span[@aria-hidden='true']]"
                                    )
                                    if close_button:
                                        close_button.click()
                                        time.sleep(1)
                                except Exception as e:
                                    logger.error(f"Error closing modal: {e}")

                    except Exception as e:
                        logger.error(f"Error processing PDF #{i}: {e}")
                        # Try to close any open modal
                        try:
                            close_button = page.query_selector(
                                "//button[@id='modal_close' and ./span[@aria-hidden='true']]"
                            )
                            if close_button:
                                close_button.click()
                                time.sleep(1)
                        except Exception:
                            pass

                # Check if there's a next page
                next_button = page.query_selector("#example_pdf_next")
                if next_button and "disabled" not in (
                    next_button.get_attribute("class") or ""
                ):
                    next_button.click()
                    current_page += 1
                    time.sleep(2)

                    # Check if we need to solve a new captcha
                    if page.query_selector("#captcha_image") is not None:
                        logger.info("New page captcha detected")
                        if not solve_captcha(page):
                            logger.error("Failed to solve page navigation captcha")
                            break

                    # Wait for the next page to load
                    try:
                        page.wait_for_selector("#example_pdf", timeout=10000)
                    except TimeoutError:
                        logger.error("Timed out waiting for next page")
                        keep_scraping = False
                else:
                    logger.info("No more pages available, ending scrape")
                    keep_scraping = False

            except Exception as e:
                logger.error(f"Error processing page {current_page}: {e}")
                keep_scraping = False

        logger.info("Scraping completed")
        context.close()


if __name__ == "__main__":
    main()

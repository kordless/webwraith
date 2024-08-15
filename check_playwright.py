from playwright.sync_api import sync_playwright

def main():
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            browser.close()
        print("Playwright Chromium is installed and working correctly.")
    except Exception as e:
        print(f"Error: {e}")
        print("Playwright Chromium might not be installed correctly.")

if __name__ == "__main__":
    main()
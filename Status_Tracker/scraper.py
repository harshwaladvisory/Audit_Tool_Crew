import logging
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
import time

# options = Options()
# driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

logger = logging.getLogger(__name__)

class CharityStatusScraper:
    def __init__(self):
        self.driver = None
        self.setup_driver()
    
    def setup_driver(self):
        """Setup Chrome WebDriver with appropriate options"""
        try:
            chrome_options = Options()
            chrome_options.add_argument("--headless=new")  # Run in background
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--window-size=1920,1080")
            chrome_options.add_argument("--disable-extensions")
            chrome_options.add_argument("--disable-plugins")
            chrome_options.add_argument("--disable-images")
            chrome_options.add_argument("--disable-logging")
            chrome_options.add_argument("--disable-background-timer-throttling")
            chrome_options.add_argument("--disable-backgrounding-occluded-windows")
            chrome_options.add_argument("--disable-renderer-backgrounding")
            chrome_options.add_argument("--disable-features=TranslateUI")
            chrome_options.add_argument("--disable-ipc-flooding-protection")
            chrome_options.add_argument("--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36")
            
            # # Use system-installed Chromium and ChromeDriver
            # import subprocess
            # try:
            #     chromium_path = subprocess.check_output(["which", "chromium"]).decode().strip()
            #     chromedriver_path = subprocess.check_output(["which", "chromedriver"]).decode().strip()
            #     chrome_options.binary_location = chromium_path
            #     service = Service(chromedriver_path)
            #     logger.info(f"Using system Chromium: {chromium_path}")
            #     logger.info(f"Using system ChromeDriver: {chromedriver_path}")
            # except subprocess.CalledProcessError:
            #     # Fallback to webdriver-manager if system binaries not found
            #     logger.warning("System Chromium/ChromeDriver not found, falling back to webdriver-manager")
            #     service = Service(ChromeDriverManager().install())
            
            # Always use webdriver-manager to fetch correct ChromeDriver path
            driver_path = ChromeDriverManager().install()
            logger.info(f"Using ChromeDriver path: {driver_path}")

            # Set up service using the downloaded driver
            service = Service(driver_path)

            # Launch the Chrome browser
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            self.driver.set_page_load_timeout(60)
            self.driver.implicitly_wait(10)

            logger.info("Chrome WebDriver initialized successfully")
            
        except Exception as e:
            logger.error(f"Error setting up WebDriver: {str(e)}")
            raise Exception(f"Failed to initialize web browser: {str(e)}")
        # driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    
    def get_charity_status(self, ein):
        """
        Scrape charity status for a given EIN from California DOJ website
        
        Args:
            ein (str): 9-digit EIN number (digits only)
            
        Returns:
            str: Registry status or error message
        """
        if not self.driver:
            raise Exception("WebDriver not initialized")
        
        url = "https://rct.doj.ca.gov/Verification/Web/Search.aspx?facility=y"
        
        try:
            logger.info(f"Navigating to {url}")
            self.driver.get(url)
            
            # Wait for page to load
            # wait = WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.ID, "t_web_lookup__federal_id")))
            wait = WebDriverWait(self.driver, 10)
            
            # Wait for the FEIN input field to be present
            fein_input = wait.until(
                EC.presence_of_element_located((By.ID, "t_web_lookup__federal_id"))
            )
            
            # Clear and enter EIN
            fein_input.clear()
            fein_input.send_keys(ein)
            logger.info(f"Entered EIN: {ein}")
            
            # Find and click search button
            search_button = self.driver.find_element(By.ID, "sch_button")
            search_button.click()
            logger.info("Clicked search button")
            
            # Efficient status extraction with timeout protection
            page_source = ""
            try:
                # Quick wait and capture page
                time.sleep(1)
                page_source = self.driver.page_source
                
                # Check for no results
                if any(phrase in page_source.lower() for phrase in [
                    "no records found", "no results", "no matches", "not found"
                ]):
                    logger.info("No records found for this EIN")
                    return "Not Found"
                
                # Direct regex approach for complete multi-word status capture
                import re
                
                # Primary pattern: Charity Registration followed by complete status
                primary_pattern = r'<span[^>]*>Charity Registration</span></td><td[^>]*><span[^>]*>([^<]+)</span></td>'
                matches = re.findall(primary_pattern, page_source, re.IGNORECASE | re.DOTALL)
                
                if matches:
                    status = matches[0].strip()
                    logger.info(f"Found complete registry status: {status}")
                    return status
                
                # Secondary pattern: Any status cell with complete text including dashes/additional text
                status_patterns = [
                    r'<td[^>]*><span[^>]*>(Current[^<]*(?:\s*[-–]\s*[^<]*)?)</span></td>',
                    r'<td[^>]*><span[^>]*>(Delinquent[^<]*(?:\s*[-–]\s*[^<]*)?)</span></td>',
                    r'<td[^>]*><span[^>]*>(Exempt[^<]*(?:\s*[-–]\s*[^<]*)?)</span></td>',
                    r'<td[^>]*><span[^>]*>(Suspended[^<]*(?:\s*[-–]\s*[^<]*)?)</span></td>',
                    r'<td[^>]*><span[^>]*>(Revoked[^<]*(?:\s*[-–]\s*[^<]*)?)</span></td>',
                    r'<td[^>]*><span[^>]*>(Active[^<]*(?:\s*[-–]\s*[^<]*)?)</span></td>',
                    r'<td[^>]*><span[^>]*>(Good Standing[^<]*(?:\s*[-–]\s*[^<]*)?)</span></td>'
                ]
                
                for pattern in status_patterns:
                    matches = re.findall(pattern, page_source, re.IGNORECASE)
                    if matches:
                        status = matches[0].strip()
                        # Filter out obvious non-status matches
                        if not any(word in status.lower() for word in ['menu', 'nav', 'link', 'button', 'header']):
                            logger.info(f"Found complete status: {status}")
                            return status
                
                # Fallback: Look for EIN presence
                if ein in page_source:
                    logger.info("EIN found but status unclear")
                    return "Found - Status Unclear"
                
                logger.warning("No clear results found")
                return "Not Found"
                
            except Exception as e:
                logger.error(f"Error processing results: {str(e)}")
                return "Search Error"
            
        except TimeoutException:
            logger.error("Timeout waiting for page elements")
            return "Website Timeout"
        except WebDriverException as e:
            logger.error(f"WebDriver error: {str(e)}")
            return "Browser Error"
        except Exception as e:
            # logger.error(f"Unexpected error processing EIN {ein}: {str(e)}")
            # return f"Processing Error"
            import traceback
            logger.error(f"Unexpected error processing EIN {ein}: {str(e)}\n{traceback.format_exc()}")
            return f"Processing Error: {str(e)}"

    
    def close(self):
        """Close the WebDriver"""
        if self.driver:
            try:
                self.driver.quit()
                logger.info("WebDriver closed successfully")
            except Exception as e:
                logger.error(f"Error closing WebDriver: {str(e)}")
            finally:
                self.driver = None

    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

import os
import time
import csv
import random
import pandas as pd
import logging
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementNotInteractableException
from webdriver_manager.chrome import ChromeDriverManager
from fake_useragent import UserAgent
from fuzzywuzzy import fuzz

# Import utility functions
from utils import setup_logger, retry, sanitize_data, validate_phone, validate_email


class IndiaMartScraper:
    def __init__(self, headless=False):
        self.base_url = "https://www.indiamart.com/"
        self.driver = None
        self.leads = []
        self.logger = setup_logger()
        self.headless = headless
        self.setup_driver()
        
    def setup_driver(self):
        """Set up the Selenium WebDriver with appropriate options"""
        self.logger.info("Setting up the browser...")
        try:
            ua = UserAgent()
            user_agent = ua.random
            
            # Create Chrome options
            chrome_options = Options()
            
            # Configure headless mode if requested
            if self.headless:
                self.logger.info("Running in headless mode")
                chrome_options.add_argument("--headless=new")
                chrome_options.add_argument("--window-size=1920,1080")
            
            chrome_options.add_argument(f"user-agent={user_agent}")
            chrome_options.add_argument("--disable-notifications")
            chrome_options.add_argument("--disable-popup-blocking")
            chrome_options.add_argument("--start-maximized")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--no-sandbox")
            
            # Let Selenium handle the driver download and management
            self.driver = webdriver.Chrome(options=chrome_options)
            self.logger.info("Browser setup complete")
        except Exception as e:
            self.logger.error(f"Failed to set up browser: {e}")
            raise
        
    @retry(max_attempts=3, delay=2)
    def login(self):
        """Navigate to IndiaMART and handle the login process"""
        self.logger.info("Navigating to IndiaMART login page...")
        
        # Go directly to the mobile login page
        try:
            self.driver.get("https://m.indiamart.com/login/")
            self.logger.info("Navigated directly to the mobile login page")
            time.sleep(3)  # Wait for the page to load
        except Exception as e:
            self.logger.error(f"Failed to navigate to IndiaMART mobile login page: {e}")
            return False
        
        # Wait for the page to load
        time.sleep(5)
        
        # Save screenshot of the current page for debugging
        self.driver.save_screenshot("login_page.png")
        self.logger.info(f"Current page title: {self.driver.title}")
        self.logger.info(f"Current URL: {self.driver.current_url}")
        
        try:
            # Try to find the login form or modal
            # First, check if we need to click a sign-in button to show the login form
            login_buttons = [
                "//a[contains(text(), 'Sign In')]",
                "//button[contains(text(), 'Sign In')]",
                "//div[contains(text(), 'Sign In')]",
                "//span[contains(text(), 'Sign In')]"
            ]
            
            for selector in login_buttons:
                try:
                    elements = self.driver.find_elements(By.XPATH, selector)
                    for element in elements:
                        if element.is_displayed():
                            element.click()
                            self.logger.info(f"Clicked on login button: {selector}")
                            time.sleep(2)  # Wait for login form to appear
                            break
                except Exception as e:
                    self.logger.debug(f"Login button selector {selector} failed: {e}")
                    continue
            
            # Try different possible selectors for the mobile input field
            mobile_input_selectors = [
                "//input[@id='mobile']",
                "//input[@name='mobile']",
                "//input[@placeholder='Mobile Number']",
                "//input[@placeholder='Enter Mobile Number']",
                "//input[@type='tel']",
                "//input[contains(@class, 'mobile')]",
                "//input[@type='text']",  # More generic fallback
                "//form//input"  # Very generic fallback
            ]
            
            mobile_input = None
            for selector in mobile_input_selectors:
                try:
                    elements = self.driver.find_elements(By.XPATH, selector)
                    for element in elements:
                        if element.is_displayed():
                            mobile_input = element
                            self.logger.info(f"Found mobile input with selector: {selector}")
                            break
                    if mobile_input:
                        break
                except Exception as e:
                    self.logger.debug(f"Mobile input selector {selector} failed: {e}")
                    continue
            
            if not mobile_input:
                # Try to switch to iframe if present
                iframes = self.driver.find_elements(By.TAG_NAME, "iframe")
                if iframes:
                    self.logger.info(f"Found {len(iframes)} iframes, trying to switch to them")
                    for iframe in iframes:
                        try:
                            self.driver.switch_to.frame(iframe)
                            self.logger.info("Switched to iframe")
                            
                            # Try to find mobile input in iframe
                            for selector in mobile_input_selectors:
                                try:
                                    elements = self.driver.find_elements(By.XPATH, selector)
                                    for element in elements:
                                        if element.is_displayed():
                                            mobile_input = element
                                            self.logger.info(f"Found mobile input in iframe with selector: {selector}")
                                            break
                                    if mobile_input:
                                        break
                                except Exception as e:
                                    self.logger.debug(f"Mobile input selector in iframe {selector} failed: {e}")
                                    continue
                            
                            if mobile_input:
                                break
                            else:
                                self.driver.switch_to.default_content()
                        except Exception as e:
                            self.logger.debug(f"Failed to switch to iframe: {e}")
                            self.driver.switch_to.default_content()
            
            if not mobile_input:
                self.logger.error("Could not find mobile input field")
                self.driver.save_screenshot("mobile_input_not_found.png")
                
                # Print page source for debugging
                with open("page_source.html", "w", encoding="utf-8") as f:
                    f.write(self.driver.page_source)
                self.logger.info("Saved page source to page_source.html")
                
                return False
            
            # Enter mobile number automatically
            # Ask the user to input their mobile number
            mobile_number = input("Enter your 10-digit mobile number for IndiaMART login: ")
            # Validate the mobile number
            mobile_number = validate_phone(mobile_number)
            if not mobile_number or len(mobile_number) != 10:
                self.logger.error("Invalid mobile number. Please enter a valid 10-digit number.")
                print("Invalid mobile number. Please enter a valid 10-digit number.")
                return False
                
            mobile_input.clear()
            mobile_input.send_keys(mobile_number)
            self.logger.info(f"Automatically entered mobile number: {mobile_number}")
            
            # Find and click the submit button
            submit_button_selectors = [
                "//button[contains(text(), 'Submit')]",
                "//button[contains(text(), 'Get OTP')]",
                "//button[contains(text(), 'Continue')]",
                "//button[@type='submit']",
                "//button[contains(@class, 'submit')]",
                "//input[@type='submit']",
                "//button",  # Generic fallback
                "//input[@type='button']"
            ]
            
            submit_button = None
            for selector in submit_button_selectors:
                try:
                    elements = self.driver.find_elements(By.XPATH, selector)
                    for element in elements:
                        if element.is_displayed():
                            submit_button = element
                            self.logger.info(f"Found submit button with selector: {selector}")
                            break
                    if submit_button:
                        break
                except Exception as e:
                    self.logger.debug(f"Submit button selector {selector} failed: {e}")
                    continue
            
            if not submit_button:
                self.logger.error("Could not find submit button")
                self.driver.save_screenshot("submit_button_not_found.png")
                return False
            
            # Click the submit button
            submit_button.click()
            self.logger.info("Clicked submit button to get OTP")
            
            # Wait for OTP input field to appear
            time.sleep(3)
            
        except Exception as e:
            self.logger.error(f"Error during login process: {e}")
            self.driver.save_screenshot("login_process_error.png")
            return False
        
        # Handle OTP verification
        try:
            time.sleep(3)
            
            # Try to find the OTP input field
            otp_input_selectors = [
                "//input[@id='otp']",
                "//input[@name='otp']",
                "//input[@placeholder='Enter OTP']",
                "//input[@placeholder='OTP']",
                "//input[@type='text'][contains(@placeholder, 'OTP')]",
                "//input[contains(@class, 'otp')]"
            ]
            
            otp_input = None
            for selector in otp_input_selectors:
                try:
                    elements = self.driver.find_elements(By.XPATH, selector)
                    for element in elements:
                        if element.is_displayed():
                            otp_input = element
                            self.logger.info(f"Found OTP input with selector: {selector}")
                            break
                    if otp_input:
                        break
                except Exception as e:
                    self.logger.debug(f"OTP input selector {selector} failed: {e}")
                    continue
            
            if not otp_input:
                self.logger.error("Could not find OTP input field")
                self.driver.save_screenshot("otp_input_not_found.png")
                return False
            
            # Enter OTP
            otp = input("Enter the OTP received: ")
            otp_input.clear()
            otp_input.send_keys(otp)
            self.logger.info("Entered OTP")
            
            # Find and click the verify button
            verify_button_selectors = [
                "//button[contains(text(), 'Verify')]",
                "//button[contains(text(), 'Submit')]",
                "//button[contains(text(), 'Continue')]",
                "//button[@type='submit']",
                "//button[contains(@class, 'verify')]",
                "//button[contains(@class, 'submit')]",
                "//input[@type='submit']"
            ]
            
            verify_button = None
            for selector in verify_button_selectors:
                try:
                    elements = self.driver.find_elements(By.XPATH, selector)
                    for element in elements:
                        if element.is_displayed():
                            verify_button = element
                            self.logger.info(f"Found verify button with selector: {selector}")
                            break
                    if verify_button:
                        break
                except Exception as e:
                    self.logger.debug(f"Verify button selector {selector} failed: {e}")
                    continue
            
            if not verify_button:
                self.logger.error("Could not find verify button")
                self.driver.save_screenshot("verify_button_not_found.png")
                return False
            
            # Click the verify button
            verify_button.click()
            self.logger.info("Clicked verify button")
            
            # Wait for login to complete
            time.sleep(5)
            
            # Take a screenshot of the page after login attempt
            self.driver.save_screenshot("after_login.png")
            
            # Check if login was successful - multiple possible indicators
            page_source = self.driver.page_source
            success_indicators = [
                "Sign in" not in page_source,
                "Sign In" not in page_source,
                "My Orders" in page_source,
                "My Account" in page_source,
                "Logout" in page_source,
                "Sign Out" in page_source,
                "My Profile" in page_source,
                "Dashboard" in page_source
            ]
            
            if any(success_indicators):
                self.logger.info("Login successful!")
                return True
            else:
                self.logger.warning("Login failed. Please try again.")
                self.driver.save_screenshot("login_failed.png")
                return False
                
        except Exception as e:
            self.logger.error(f"Error during OTP verification: {e}")
            self.driver.save_screenshot("otp_verification_error.png")
            return False
                
        except Exception as e:
            self.logger.error(f"Error during login: {e}")
            return False
    
    @retry(max_attempts=3, delay=2)
    def search_product(self, keyword):
        """Search for a product using the given keyword"""
        self.logger.info(f"Searching for: {keyword}")
        
        try:
            # Navigate to the search page
            self.driver.get(self.base_url)
            
            # Find the search input field and enter the keyword
            search_input = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "search-input"))
            )
            search_input.clear()
            search_input.send_keys(keyword)
            
            # Click the search button
            search_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//button[@type='submit']"))
            )
            search_button.click()
            
            # Wait for search results to load
            time.sleep(5)
            
            self.logger.info("Search completed. Now scraping results...")
            return True
            
        except Exception as e:
            self.logger.error(f"Error during search: {e}")
            return False
    
    def extract_seller_info(self, seller_element):
        """Extract information from a seller listing element"""
        seller_info = {
            "Company Name": "",
            "Company Profile URL": "",
            "Price": "Not Listed",
            "Address": "",
            "Phone Number": "",
            "Product Title/Description": "",
            "Relevancy Score (%)": 0
        }
        
        try:
            # Extract company name - based on the image, company names appear to be in elements with class names like "Sixit Sports"
            try:
                # Try to find company name in various formats
                seller_info["Company Name"] = seller_element.find_element(By.CSS_SELECTOR, ".company-name, .clg, .FM_b").text.strip()
            except NoSuchElementException:
                # Try to find any bold text that might be the company name
                try:
                    company_elements = seller_element.find_elements(By.CSS_SELECTOR, "b, strong, .FM_b")
                    if company_elements:
                        seller_info["Company Name"] = company_elements[0].text.strip()
                except NoSuchElementException:
                    pass
            
            # Extract product title/description - based on the image, product titles appear with the ball type
            try:
                # First try specific product title selectors
                seller_info["Product Title/Description"] = seller_element.find_element(By.CSS_SELECTOR, ".prd-title, .prod-name").text.strip()
            except NoSuchElementException:
                try:
                    # Try to find any text that might contain the product description
                    # From the image, we can see product descriptions like "Green Sixit Cricket Tennis Ball"
                    desc_elements = seller_element.find_elements(By.XPATH, ".//div[contains(@class, 'FM_') and not(contains(@class, 'price')) and not(contains(@class, 'contact'))]")
                    for element in desc_elements:
                        text = element.text.strip()
                        if text and len(text) > 5 and "ball" in text.lower():
                            seller_info["Product Title/Description"] = text
                            break
                except NoSuchElementException:
                    pass
            
            # Extract price information - based on the image, prices appear as "₹ 500/Dozen" or "₹ 70/Piece"
            try:
                # Look for price elements with currency symbols
                price_elements = seller_element.find_elements(By.XPATH, ".//*[contains(text(), '₹') or contains(text(), 'Rs') or contains(@class, 'price') or contains(@class, 'prc')]")
                for element in price_elements:
                    price_text = element.text.strip()
                    if price_text and ('₹' in price_text or 'Rs' in price_text or '/' in price_text):
                        seller_info["Price"] = price_text
                        break
            except NoSuchElementException:
                # Keep the default "Not Listed" value
                pass
            
            # Extract address - based on the image, locations appear like "Bengaluru" or "Mumbai"
            try:
                # Look for location elements
                address_elements = seller_element.find_elements(By.XPATH, ".//*[contains(@class, 'loctn') or contains(@class, 'location') or contains(text(), 'Delhi') or contains(text(), 'Mumbai') or contains(text(), 'Bengaluru')]")
                for element in address_elements:
                    address_text = element.text.strip()
                    if address_text and len(address_text) > 2 and not ('₹' in address_text or 'Rs' in address_text):
                        seller_info["Address"] = address_text
                        break
            except NoSuchElementException:
                pass
            
            # Extract company profile URL
            try:
                # Try to find company profile links
                company_links = seller_element.find_elements(By.CSS_SELECTOR, "a.company-name, a.clg, a[href*='indiamart.com']")
                for link in company_links:
                    href = link.get_attribute("href")
                    if href and "indiamart.com" in href and not href.endswith(".pdf"):
                        seller_info["Company Profile URL"] = href
                        break
            except Exception:
                # If no specific company link found, try to find any link that might lead to the company profile
                try:
                    links = seller_element.find_elements(By.TAG_NAME, "a")
                    for link in links:
                        href = link.get_attribute("href")
                        if href and "indiamart.com" in href and not href.endswith(".pdf"):
                            seller_info["Company Profile URL"] = href
                            break
                except:
                    pass
            
            # Extract phone number - based on the image, there are "View Mobile Number" buttons
            try:
                # Look for "View Mobile Number" buttons
                phone_buttons = seller_element.find_elements(By.XPATH, ".//*[contains(text(), 'View Mobile Number') or contains(text(), 'Call') or contains(@class, 'phone') or contains(@class, 'mobile')]")
                for button in phone_buttons:
                    # If we find a button, we'll need to extract the number from the company profile page
                    # or we might find a directly displayed number
                    phone_text = button.text.strip()
                    if phone_text and ('Call' in phone_text or any(c.isdigit() for c in phone_text)):
                        # If the text contains digits, it might be a direct phone number
                        if any(c.isdigit() for c in phone_text):
                            seller_info["Phone Number"] = ''.join(c for c in phone_text if c.isdigit())
                            break
            except NoSuchElementException:
                pass
            
            # If we have a company profile URL, visit it to extract more details
            if seller_info["Company Profile URL"]:
                self.extract_detailed_info(seller_info)
            
            return seller_info
            
        except Exception as e:
            print(f"Error extracting seller info: {e}")
            return seller_info
    
    @retry(max_attempts=2, delay=1)
    def extract_detailed_info(self, seller_info):
        """Visit the company's profile page to extract more detailed information"""
        # Store the current window handle
        main_window = self.driver.current_window_handle
        
        try:
            # Open the company profile page in a new tab
            self.driver.execute_script(f"window.open('{seller_info['Company Profile URL']}', '_blank');")
            
            # Switch to the new tab
            self.driver.switch_to.window(self.driver.window_handles[-1])
            
            # Wait for the page to load
            time.sleep(random.uniform(3, 5))
            
            # Save the page source for debugging if needed
            # with open("company_profile_page.html", "w", encoding="utf-8") as f:
            #     f.write(self.driver.page_source)
            
            # Extract phone number - try multiple approaches
            if not seller_info["Phone Number"]:
                try:
                    # First try to find any visible phone numbers on the page
                    phone_elements = self.driver.find_elements(By.XPATH, "//*[contains(text(), '+91') or contains(text(), '91-') or contains(text(), 'Call ')]")
                    for element in phone_elements:
                        text = element.text.strip()
                        if text and any(c.isdigit() for c in text):
                            # Extract only the digits
                            digits = ''.join(c for c in text if c.isdigit())
                            if len(digits) >= 10:  # Valid Indian phone numbers have at least 10 digits
                                seller_info["Phone Number"] = validate_phone(digits)
                                break
                except Exception as e:
                    self.logger.warning(f"Error finding direct phone numbers: {e}")
                
                if not seller_info["Phone Number"]:
                    try:
                        # Try to find and click the "View Phone Number" button if it exists
                        view_phone_buttons = self.driver.find_elements(By.XPATH, 
                            "//button[contains(text(), 'View Phone') or contains(text(), 'Show Number') or contains(text(), 'View Mobile') or contains(text(), 'Call')]" + 
                            " | //span[contains(text(), 'View Mobile Number') or contains(text(), 'Call')] | //div[contains(text(), 'View Mobile Number') or contains(text(), 'Call')]")
                        
                        for button in view_phone_buttons:
                            if button.is_displayed():
                                try:
                                    button.click()
                                    time.sleep(1)  # Wait for the number to appear
                                    
                                    # Now try to extract the phone number
                                    phone_elements = self.driver.find_elements(By.XPATH, "//*[contains(@class, 'phone') or contains(@class, 'mobile') or contains(text(), '+91')]")
                                    for element in phone_elements:
                                        text = element.text.strip()
                                        if text and any(c.isdigit() for c in text):
                                            digits = ''.join(c for c in text if c.isdigit())
                                            if len(digits) >= 10:
                                                seller_info["Phone Number"] = validate_phone(digits)
                                                break
                                    
                                    if seller_info["Phone Number"]:
                                        break  # Exit the loop if we found a phone number
                                except Exception as e:
                                    self.logger.warning(f"Error clicking phone button: {e}")
                                    continue  # Try the next button
                    except Exception as e:
                        self.logger.warning(f"Error finding phone buttons: {e}")
            
            # Extract detailed address if not already available
            if not seller_info["Address"] or len(seller_info["Address"]) < 5:
                try:
                    # Try multiple approaches to find address
                    address_selectors = [
                        "//span[contains(text(), 'Address:')]/following-sibling::span",
                        "//div[contains(@class, 'address') or contains(@class, 'location')]",
                        "//span[contains(text(), 'Address')]/following::*[1]",
                        "//div[contains(text(), 'Address')]/following::*[1]",
                        "//div[contains(@class, 'FM_') and (contains(text(), 'Delhi') or contains(text(), 'Mumbai') or contains(text(), 'Bengaluru'))]",
                        "//span[contains(@class, 'FM_') and (contains(text(), 'Delhi') or contains(text(), 'Mumbai') or contains(text(), 'Bengaluru'))]"
                    ]
                    
                    for selector in address_selectors:
                        try:
                            elements = self.driver.find_elements(By.XPATH, selector)
                            for element in elements:
                                text = element.text.strip()
                                if text and len(text) > 5 and not text.startswith("View") and not text.startswith("Call"):
                                    seller_info["Address"] = text
                                    break
                            
                            if seller_info["Address"] and len(seller_info["Address"]) >= 5:
                                break  # Exit the loop if we found a good address
                        except NoSuchElementException:
                            continue  # Try the next selector
                except Exception as e:
                    self.logger.warning(f"Error finding address: {e}")
            
            # Close the tab and switch back to the main window
            self.driver.close()
            self.driver.switch_to.window(main_window)
            
        except Exception as e:
            self.logger.error(f"Error extracting detailed info: {e}")
            # Make sure we switch back to the main window even if there's an error
            try:
                self.driver.close()
                self.driver.switch_to.window(main_window)
            except:
                pass
    
    def calculate_relevancy_score(self, seller_info, keyword):
        """Calculate a relevancy score based on how well the seller info matches the keyword"""
        score = 0
        keyword = keyword.lower()
        
        # Check if keyword appears in product title/description
        product_desc = seller_info["Product Title/Description"].lower()
        if keyword in product_desc:
            # Direct match gets a high score
            score += 60
            # Add bonus points based on how many times the keyword appears
            score += min(10, product_desc.count(keyword) * 2)
        else:
            # Use fuzzy matching to check for similarity
            ratio = fuzz.partial_ratio(keyword, product_desc)
            score += int(ratio * 0.6)  # Max 60 points from fuzzy matching
            
        # Check if keyword appears in company name
        company_name = seller_info["Company Name"].lower()
        if keyword in company_name:
            # Direct match in company name is valuable
            score += 30
        else:
            # Use fuzzy matching for company name too
            ratio = fuzz.partial_ratio(keyword, company_name)
            score += int(ratio * 0.3)  # Max 30 points from company name matching
        
        # Small bonus if they have a phone number (indicates they're more contactable)
        if seller_info["Phone Number"]:
            score += 5
            
        # Small bonus if they have an address (indicates they're more established)
        if seller_info["Address"]:
            score += 5
        
        # Cap the score at 100
        return min(100, score)
    
    def scrape_search_results(self, keyword, min_leads=100):
        """Scrape search results to collect leads"""
        page_num = 1
        leads_count = 0
        
        while leads_count < min_leads:
            print(f"Scraping page {page_num}...")
            
            try:
                # Wait for the search results to load - based on the image, we need to look for various selectors
                # Try multiple selectors to find product listings
                try:
                    WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, ".product-listing, .FM_sldrB, .prd-block, [class*='FM_']"))
                    )
                except TimeoutException:
                    # If we can't find specific elements, wait for any content to load
                    WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.TAG_NAME, "body"))
                    )
                    time.sleep(5)  # Give extra time for dynamic content to load
                
                # Save the page source for debugging if needed
                with open("page_source.html", "w", encoding="utf-8") as f:
                    f.write(self.driver.page_source)
                
                # Try multiple selectors to find product listings based on the image structure
                seller_elements = []
                selectors = [
                    ".product-listing .listing",  # Original selector
                    ".prd-block",               # Alternative selector
                    ".FM_sldrB",               # From the image
                    "[class*='FM_'][class*='bs']",  # Generic FM class with box-shadow
                    ".product-card",           # Common product card class
                    "div[onclick*='product']",  # Elements with product in onclick
                    "div[class*='product']",    # Elements with product in class
                    "div[class*='card']",       # Elements with card in class
                    "div[class*='item']",       # Elements with item in class
                ]
                
                # Try each selector
                for selector in selectors:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        seller_elements.extend(elements)
                        print(f"Found {len(elements)} listings with selector: {selector}")
                
                # Remove duplicates by comparing element IDs
                unique_elements = []
                element_ids = set()
                for element in seller_elements:
                    element_id = element.id
                    if element_id not in element_ids:
                        element_ids.add(element_id)
                        unique_elements.append(element)
                
                seller_elements = unique_elements
                
                if not seller_elements:
                    # If still no elements found, try to find any div that might contain product info
                    seller_elements = self.driver.find_elements(By.XPATH, "//div[.//a and .//div[contains(text(), 'Contact') or contains(text(), 'Price')]]")
                
                if not seller_elements:
                    print("No product listings found. Taking screenshot for debugging...")
                    self.driver.save_screenshot(f"search_results_page_{page_num}.png")
                    print("No more results found.")
                    break
                
                print(f"Found {len(seller_elements)} listings on this page")
                
                # Process each seller listing
                for seller_element in seller_elements:
                    # Add random delay to mimic human behavior
                    time.sleep(random.uniform(1, 3))
                    
                    # Extract seller information
                    seller_info = self.extract_seller_info(seller_element)
                    
                    # Calculate relevancy score
                    seller_info["Relevancy Score (%)"] = self.calculate_relevancy_score(seller_info, keyword)
                    
                    # Add to leads list if we have at least the company name or product description
                    if seller_info["Company Name"] or seller_info["Product Title/Description"]:
                        self.leads.append(seller_info)
                        leads_count += 1
                        print(f"Collected lead {leads_count}: {seller_info['Company Name'] or seller_info['Product Title/Description']}")
                        
                        # If we've reached the minimum number of leads, break out of the loop
                        if leads_count >= min_leads:
                            break
                
                # If we haven't collected enough leads, go to the next page
                if leads_count < min_leads:
                    # Try to find and click the "Next" button
                    try:
                        next_button = WebDriverWait(self.driver, 5).until(
                            EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), 'Next') or contains(@class, 'next')]"))
                        )
                        next_button.click()
                        page_num += 1
                        # Wait for the next page to load
                        time.sleep(random.uniform(3, 5))
                    except (TimeoutException, NoSuchElementException):
                        print("No more pages available.")
                        break
                        
            except Exception as e:
                print(f"Error scraping search results: {e}")
                break
        
        print(f"Total leads collected: {len(self.leads)}")
        return self.leads
    
    def export_to_csv(self, filename="leads.csv"):
        """Export the collected leads to a CSV file"""
        if not self.leads:
            self.logger.warning("No leads to export.")
            return False
        
        try:
            # Clean and sanitize the data
            cleaned_leads = [sanitize_data(lead) for lead in self.leads]
            
            # Ensure we have the correct fields in the output
            fields = ["Company Name", "Company Profile URL", "Price", "Address", "Phone Number", "Product Title/Description", "Relevancy Score (%)"]
            
            # Sort leads by relevancy score (highest first)
            sorted_leads = sorted(cleaned_leads, key=lambda x: x["Relevancy Score (%)"], reverse=True)
            
            # Create a DataFrame from the leads
            df = pd.DataFrame(sorted_leads)
            
            # Ensure we have the correct fields in the output
            df = df[fields]
            
            # Export to CSV
            df.to_csv(filename, index=False, encoding='utf-8-sig')  # utf-8-sig for Excel compatibility
            
            self.logger.info(f"Successfully exported {len(sorted_leads)} leads to {filename}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error exporting to CSV: {e}")
            return False
    
    def close(self):
        """Close the browser and clean up"""
        if self.driver:
            self.driver.quit()
            print("Browser closed.")


def main():
    # Create logs directory if it doesn't exist
    if not os.path.exists('logs'):
        os.makedirs('logs')
    
    # Setup logger first
    logger = setup_logger()
    logger.info("Starting IndiaMART Lead Scraper")
    
    scraper = None
    
    try:
        print("Initializing browser...")
        # Try to create the scraper with different headless settings if needed
        try:
            scraper = IndiaMartScraper(headless=False)
        except Exception as e:
            logger.warning(f"Failed to initialize browser in normal mode: {e}")
            print("Failed to initialize browser in normal mode. Trying headless mode...")
            try:
                scraper = IndiaMartScraper(headless=True)
                print("Browser initialized in headless mode.")
            except Exception as e:
                logger.error(f"Failed to initialize browser in headless mode: {e}")
                print("\nERROR: Could not initialize the browser. Please check your Chrome installation.")
                print("Possible solutions:")
                print("1. Make sure Chrome is installed and up to date")
                print("2. Try running the script with administrator privileges")
                print("3. Check if your antivirus is blocking Chrome automation")
                return
        
        print("Browser initialized successfully.")
        logger.info("Browser initialized successfully")
        
        # Login to IndiaMART
        print("\nNavigating to IndiaMART...")
        login_success = scraper.login()
        
        if login_success:
            print("\nLogin successful!")
            
            # Get the search keyword from the user
            keyword = input("\nEnter the product keyword to search for: ")
            logger.info(f"User entered keyword: {keyword}")
            
            # Search for the product
            print(f"\nSearching for '{keyword}'...")
            search_success = scraper.search_product(keyword)
            
            if search_success:
                print("\nSearch successful! Starting to collect leads...")
                
                # Ask for minimum leads
                try:
                    min_leads = int(input("\nMinimum number of leads to collect (default: 100): ") or "100")
                except ValueError:
                    min_leads = 100
                    print("Invalid input. Using default value of 100 leads.")
                
                # Scrape the search results
                leads = scraper.scrape_search_results(keyword, min_leads=min_leads)
                
                if leads:
                    # Export the leads to a CSV file
                    filename = input("\nEnter filename for export (default: leads.csv): ") or "leads.csv"
                    export_success = scraper.export_to_csv(filename)
                    
                    if export_success:
                        logger.info(f"Scraping completed successfully. {len(leads)} leads exported to {filename}")
                        print(f"\nScraping completed! {len(leads)} leads have been exported to {filename}")
                    else:
                        logger.error("Failed to export leads to CSV.")
                        print("\nFailed to export leads to CSV. Check logs for details.")
                else:
                    logger.warning("No leads were collected.")
                    print("\nNo leads were collected. Try a different keyword or check if the website structure has changed.")
            else:
                logger.error("Search failed.")
                print("\nSearch failed. Please try again with a different keyword.")
        else:
            logger.error("Login failed.")
            print("\nLogin failed. Please check your credentials and try again.")
            
    except KeyboardInterrupt:
        logger.info("Operation cancelled by user.")
        print("\nOperation cancelled by user.")
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
        print(f"\nAn error occurred: {e}")
        print("Check the logs directory for more details.")
    finally:
        # Close the browser
        if scraper:
            logger.info("Closing browser and ending session")
            scraper.close()


if __name__ == "__main__":
    main()
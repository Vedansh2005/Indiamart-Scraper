import logging
import os
import time
from datetime import datetime

# Configure logging
def setup_logger():
    """Set up and configure the logger"""
    # Create logs directory if it doesn't exist
    if not os.path.exists('logs'):
        os.makedirs('logs')
    
    # Create a unique log file name with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = f"logs/scraper_{timestamp}.log"
    
    # Configure the logger
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    
    return logging.getLogger()

# Retry decorator for handling transient errors
def retry(max_attempts=3, delay=2):
    """Decorator to retry a function if it fails"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            attempts = 0
            while attempts < max_attempts:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    attempts += 1
                    if attempts == max_attempts:
                        raise
                    logging.warning(f"Attempt {attempts} failed with error: {e}. Retrying in {delay} seconds...")
                    time.sleep(delay)
        return wrapper
    return decorator

# Function to sanitize data for CSV
def sanitize_data(data):
    """Clean and sanitize data for CSV export"""
    if isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, str):
                # Remove any leading/trailing whitespace
                data[key] = value.strip()
                # Replace any newlines or tabs with spaces
                data[key] = data[key].replace('\n', ' ').replace('\t', ' ')
                # Remove any double spaces
                while '  ' in data[key]:
                    data[key] = data[key].replace('  ', ' ')
    return data

# Function to validate phone numbers
def validate_phone(phone):
    """Validate and format phone numbers"""
    if not phone:
        return ""
    
    # Remove any non-digit characters
    digits = ''.join(filter(str.isdigit, phone))
    
    # Check if it's a valid Indian phone number (10 digits, or 11-12 with country code)
    if len(digits) == 10:
        return digits
    elif len(digits) in [11, 12] and digits.startswith(('91', '0')):
        # Remove leading 0 or 91 (country code)
        return digits[-10:]
    else:
        return phone  # Return original if we can't validate

# Function to validate emails
def validate_email(email):
    """Validate email addresses"""
    if not email:
        return ""
    
    # Basic email validation
    if '@' in email and '.' in email.split('@')[1]:
        return email.strip().lower()
    else:
        return ""  # Return empty string for invalid emails
#!/usr/bin/env python
import argparse
import os
import sys
from indiamart_scraper import IndiaMartScraper
from utils import setup_logger

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="IndiaMART Lead Scraper - Extract leads from IndiaMART based on product keywords")
    
    parser.add_argument(
        "--keyword", "-k",
        type=str,
        help="Product keyword to search for"
    )
    
    parser.add_argument(
        "--output", "-o",
        type=str,
        default="leads.csv",
        help="Output CSV file name (default: leads.csv)"
    )
    
    parser.add_argument(
        "--min-leads", "-m",
        type=int,
        default=100,
        help="Minimum number of leads to collect (default: 100)"
    )
    
    parser.add_argument(
        "--headless", "-H",
        action="store_true",
        help="Run in headless mode (no browser UI)"
    )
    
    return parser.parse_args()

def main():
    """Main entry point for the CLI"""
    # Parse command line arguments
    args = parse_arguments()
    
    # Set up logger
    logger = setup_logger()
    
    # Create an instance of the scraper
    scraper = IndiaMartScraper(headless=args.headless)
    
    try:
        # Login to IndiaMART
        login_success = scraper.login()
        
        if login_success:
            # Get the search keyword from the user if not provided as an argument
            keyword = args.keyword
            if not keyword:
                keyword = input("Enter the product keyword to search for: ")
            
            logger.info(f"Using keyword: {keyword}")
            
            # Search for the product
            search_success = scraper.search_product(keyword)
            
            if search_success:
                # Scrape the search results
                leads = scraper.scrape_search_results(keyword, min_leads=args.min_leads)
                
                # Export the leads to a CSV file
                export_success = scraper.export_to_csv(filename=args.output)
                
                if export_success:
                    logger.info(f"Scraping completed successfully. {len(leads)} leads exported to {args.output}")
                    print(f"\nScraping completed! {len(leads)} leads have been exported to {args.output}")
            else:
                logger.error("Search failed.")
                print("Search failed. Please try again.")
        else:
            logger.error("Login failed.")
            print("Login failed. Please check your credentials and try again.")
            
    except KeyboardInterrupt:
        logger.info("Operation cancelled by user.")
        print("\nOperation cancelled by user.")
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
        print(f"An error occurred: {e}")
    finally:
        # Close the browser
        logger.info("Closing browser and ending session")
        scraper.close()

if __name__ == "__main__":
    main()
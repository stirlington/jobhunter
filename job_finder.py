import streamlit as st
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import pandas as pd
import time
import re
import os

# For Selenium Manager (works with newer Selenium versions)
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager

# Configure Streamlit page
st.set_page_config(page_title="Job Search Assistant", layout="wide")

def create_webdriver():
    """
    Create WebDriver with robust handling for different deployment environments
    """
    try:
        # Chrome options for headless and no-sandbox environments
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        
        # User agent to mimic browser
        chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        
        # Attempt to use WebDriver Manager for automatic driver management
        try:
            service = ChromeService(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=chrome_options)
            return driver
        
        except Exception as webdriver_manager_error:
            # Fallback to system ChromeDriver if WebDriver Manager fails
            st.warning(f"WebDriver Manager failed: {webdriver_manager_error}")
            
            try:
                # Try using system ChromeDriver
                driver = webdriver.Chrome(options=chrome_options)
                return driver
            
            except Exception as system_driver_error:
                st.error(f"Could not initialize WebDriver: {system_driver_error}")
                return None

    except Exception as e:
        st.error(f"Unexpected error in WebDriver creation: {e}")
        return None

def search_jobs(company, driver):
    jobs = []
    platforms = [
        {"name": "LinkedIn", "query": f"{company} jobs site:linkedin.com/jobs/view/"},
        {"name": "Indeed", "query": f"{company} jobs site:indeed.com"}
    ]
    
    for platform in platforms:
        try:
            # Use more targeted search query
            search_url = f"https://www.google.com/search?q={platform['query']}"
            driver.get(search_url)
            time.sleep(3)  # Increased wait time
            
            # Wait for search results to load
            try:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "div.g"))
                )
            except Exception as wait_error:
                st.warning(f"Timeout waiting for search results for {company}: {wait_error}")
                continue
            
            # Find all search result links with improved selector
            links = driver.find_elements(By.CSS_SELECTOR, "div.g a")
            
            for link in links:
                try:
                    url = link.get_attribute("href")
                    title = link.text
                    
                    # Advanced filtering
                    cleaned_title = clean_job_title(title)
                    if not cleaned_title:
                        continue
                    
                    # Default location
                    location = "Location not specified"
                    
                    # Validate job listing
                    if not url or not any(platform_keyword in url.lower() for platform_keyword in ['linkedin', 'indeed']):
                        continue
                    
                    jobs.append({
                        'Platform': platform['name'],
                        'Company': company,
                        'Job Title': cleaned_title,
                        'Location': location,
                        'URL': url
                    })
                except Exception as link_error:
                    st.warning(f"Error processing link for {company}: {link_error}")
        except Exception as platform_error:
            st.warning(f"Error searching on {platform['name']} for {company}: {platform_error}")
    
    return jobs

def clean_job_title(title):
    """Clean and filter job titles."""
    # Remove extra whitespace and irrelevant text
    title = re.sub(r'\s+', ' ', title).strip()
    
    # More aggressive filtering
    if not title or len(title) < 5:
        return None
    
    # Filter out non-job related links
    irrelevant_keywords = [
        'careers', 'company', 'about', 'contact', 'login', 
        'signup', 'home', 'jobs near me', 'all jobs'
    ]
    if any(keyword in title.lower() for keyword in irrelevant_keywords):
        return None
    
    return title

def main():
    st.title("Company Job Search Assistant")

    # File upload
    st.subheader("Upload Company List")
    uploaded_file = st.file_uploader("Choose an Excel file", type=['xlsx'])

    if uploaded_file is not None:
        try:
            df = pd.read_excel(uploaded_file)
            
            # Display column names and let user select the company column
            st.write("Available columns in your file:", df.columns.tolist())
            company_column = st.selectbox(
                "Select the column containing company names:",
                options=df.columns.tolist()
            )
            
            st.write("Preview of companies:", df[company_column])

            # Create a placeholder for the results table
            results_table = st.empty()
            results_df = pd.DataFrame(columns=['Platform', 'Company', 'Job Title', 'Location', 'URL'])
            results_table.dataframe(results_df)

            if st.button("Search Jobs"):
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                # Initialize driver
                driver = create_webdriver()
                if not driver:
                    st.error("Could not create WebDriver. Please check your Chrome/Chromium installation.")
                    return
                
                try:
                    total_companies = len(df[company_column].unique())
                    search_count = 0
                    
                    for idx, company in enumerate(df[company_column].unique()):
                        status_text.text(f"Searching jobs for {company}...")
                        
                        jobs = search_jobs(company, driver)
                        
                        # Remove duplicates before adding
                        jobs_df = pd.DataFrame(jobs)
                        if not jobs_df.empty:
                            jobs_df.drop_duplicates(subset=['URL'], inplace=True)
                            results_df = pd.concat([results_df, jobs_df], ignore_index=True)
                        
                        # Update the displayed table
                        results_table.dataframe(results_df)
                        
                        search_count += 1
                        progress_bar.progress(search_count / total_companies)
                        
                        time.sleep(2)  # Delay between searches
                            
                finally:
                    driver.quit()
                
                status_text.text("Search completed!")
                
                if not results_df.empty:
                    # Download buttons
                    col1, col2 = st.columns(2)
                    
                    # CSV Download
                    csv = results_df.to_csv(index=False).encode('utf-8')
                    col1.download_button(
                        label="Download CSV",
                        data=csv,
                        file_name="company_jobs.csv",
                        mime="text/csv"
                    )
                    
                    # Excel Download
                    buffer = pd.ExcelWriter('company_jobs.xlsx', engine='xlsxwriter')
                    results_df.to_excel(buffer, index=False)
                    buffer.save()
                    
                    with open('company_jobs.xlsx', 'rb') as f:
                        excel_data = f.read()
                    
                    col2.download_button(
                        label="Download Excel",
                        data=excel_data,
                        file_name="company_jobs.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )

        except Exception as e:
            st.error(f"An error occurred: {str(e)}")

    st.sidebar.markdown("""
    ### Instructions
    1. Upload an Excel file containing company names
    2. Select the column containing company names
    3. Click 'Search Jobs' to start
    4. Watch results populate in real-time
    5. Download results as CSV or Excel
    """)

if __name__ == "__main__":
    main()

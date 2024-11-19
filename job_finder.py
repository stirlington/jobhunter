import streamlit as st
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import pandas as pd
import time
import re

# For Selenium Manager (works with newer Selenium versions)
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager

# Configure Streamlit page
st.set_page_config(page_title="Job Search Assistant", layout="wide")

def create_webdriver():
    """ Create WebDriver with robust handling for different deployment environments """
    try:
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

        # Use WebDriver Manager for automatic driver management
        service = ChromeService(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        return driver

    except Exception as e:
        st.error(f"Could not initialize WebDriver: {e}")
        return None

def search_jobs(company, driver):
    jobs = []
    platforms = [
        {"name": "LinkedIn", "query": f"{company} jobs site:linkedin.com/jobs/view/"},
        {"name": "Indeed", "query": f"{company} jobs site:indeed.com"}
    ]
    
    for platform in platforms:
        try:
            search_url = f"https://www.google.com/search?q={platform['query']}"
            driver.get(search_url)
            
            # Use WebDriverWait instead of time.sleep()
            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.g")))
            
            links = driver.find_elements(By.CSS_SELECTOR, "div.g a")
            for link in links:
                url = link.get_attribute("href")
                title = link.text
                
                cleaned_title = clean_job_title(title)
                if not cleaned_title:
                    continue
                
                location = "Location not specified"
                if url and any(keyword in url.lower() for keyword in ['linkedin', 'indeed']):
                    jobs.append({
                        'Platform': platform['name'],
                        'Company': company,
                        'Job Title': cleaned_title,
                        'Location': location,
                        'URL': url
                    })
        
        except Exception as e:
            st.warning(f"Error searching on {platform['name']} for {company}: {e}")
    
    return jobs

def clean_job_title(title):
    title = re.sub(r'\s+', ' ', title).strip()
    
    irrelevant_keywords = ['careers', 'company', 'about', 'contact', 'login', 'signup', 'home', 'jobs near me', 'all jobs']
    if any(keyword in title.lower() for keyword in irrelevant_keywords):
        return None
    
    return title

def main():
    st.title("Company Job Search Assistant")
    
    uploaded_file = st.file_uploader("Choose an Excel file", type=['xlsx'])
    
    if uploaded_file is not None:
        try:
            df = pd.read_excel(uploaded_file)
            company_column = st.selectbox("Select the column containing company names:", options=df.columns.tolist())
            
            results_table = st.empty()
            results_df = pd.DataFrame(columns=['Platform', 'Company', 'Job Title', 'Location', 'URL'])
            
            if st.button("Search Jobs"):
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                driver = create_webdriver()
                if not driver:
                    return
                
                total_companies = len(df[company_column].unique())
                
                try:
                    for idx, company in enumerate(df[company_column].unique()):
                        status_text.text(f"Searching jobs for {company}...")
                        jobs = search_jobs(company, driver)
                        
                        jobs_df = pd.DataFrame(jobs)
                        if not jobs_df.empty:
                            jobs_df.drop_duplicates(subset=['URL'], inplace=True)
                            results_df = pd.concat([results_df, jobs_df], ignore_index=True)
                        
                        results_table.dataframe(results_df)
                        progress_bar.progress((idx + 1) / total_companies)
                
                finally:
                    driver.quit()
                
                # Download buttons
                csv_data = results_df.to_csv(index=False).encode('utf-8')
                st.download_button(label="Download CSV", data=csv_data, file_name="company_jobs.csv", mime="text/csv")
                
                with pd.ExcelWriter('company_jobs.xlsx', engine='xlsxwriter') as writer:
                    results_df.to_excel(writer, index=False)

                with open('company_jobs.xlsx', 'rb') as f:
                    excel_data = f.read()

                st.download_button(label="Download Excel", data=excel_data,
                                   file_name="company_jobs.xlsx",
                                   mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        
        except Exception as e:
            st.error(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    main()

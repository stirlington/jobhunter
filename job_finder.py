import streamlit as st
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
import pandas as pd
import time
import os

# Configure Streamlit page
st.set_page_config(page_title="LinkedIn Job Search Assistant", layout="wide")

@st.cache_resource
def get_webdriver_options():
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-notifications')
    options.add_argument('--disable-popup-blocking')
    options.add_argument('--blink-settings=imagesEnabled=false')
    return options

def search_linkedin_jobs(company, job_title, location, driver):
    jobs = []
    try:
        # Construct LinkedIn search URL
        search_url = f"https://www.linkedin.com/jobs/search/?keywords={job_title}&location={location}&company={company}"
        driver.get(search_url)
        time.sleep(3)  # Increased wait time
        
        # Find job listings
        job_cards = WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.CLASS_NAME, "job-card-container"))
        )
        
        for job in job_cards[:5]:  # Limit to first 5 results per company
            try:
                title = job.find_element(By.CLASS_NAME, "job-card-list__title").text
                job_location = job.find_element(By.CLASS_NAME, "job-card-container__metadata-item").text
                url = job.find_element(By.CLASS_NAME, "job-card-list__title").get_attribute("href")
                
                jobs.append({
                    'Company': company,
                    'Title': title,
                    'Location': job_location,
                    'URL': url
                })
            except Exception as e:
                continue
                
    except Exception as e:
        st.warning(f"No jobs found for {company}")
    
    return jobs

def main():
    st.title("LinkedIn Job Search Assistant")

    # File upload
    st.subheader("Upload Company List")
    uploaded_file = st.file_uploader("Choose an Excel file", type=['xlsx'])

    if uploaded_file is not None:
        try:
            df = pd.read_excel(uploaded_file)
            st.write("Uploaded companies:", df)

            # Search parameters
            st.subheader("Search Parameters")
            col1, col2 = st.columns(2)
            with col1:
                job_titles = st.multiselect(
                    "Job Titles",
                    ["Quality", "Regulatory", "Quality Assurance", "Quality Control", "Regulatory Affairs"],
                    default=["Quality", "Regulatory"]
                )
            with col2:
                location = st.text_input("Location", "United Kingdom")

            if st.button("Search Jobs"):
                results = []
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                try:
                    # Initialize driver once for all searches
                    driver = webdriver.Chrome(options=get_webdriver_options())
                    
                    total_searches = len(df['Company']) * len(job_titles)
                    search_count = 0
                    
                    for company in df['Company'].unique():
                        for job_title in job_titles:
                            status_text.text(f"Searching {job_title} jobs for {company}...")
                            jobs = search_linkedin_jobs(company, job_title, location, driver)
                            results.extend(jobs)
                            
                            search_count += 1
                            progress_bar.progress(search_count / total_searches)
                            
                finally:
                    driver.quit()
                
                # Create results DataFrame
                results_df = pd.DataFrame(results)
                
                if not results_df.empty:
                    st.subheader("Search Results")
                    st.dataframe(results_df)
                    
                    # Save to session state to prevent re-searching
                    st.session_state.results_df = results_df
                    
                    # Download buttons
                    col1, col2 = st.columns(2)
                    
                    # CSV Download
                    csv = results_df.to_csv(index=False).encode('utf-8')
                    col1.download_button(
                        label="Download CSV",
                        data=csv,
                        file_name="linkedin_job_results.csv",
                        mime="text/csv"
                    )
                    
                    # Excel Download
                    buffer = pd.ExcelWriter('linkedin_job_results.xlsx', engine='xlsxwriter')
                    results_df.to_excel(buffer, index=False)
                    buffer.save()
                    
                    with open('linkedin_job_results.xlsx', 'rb') as f:
                        excel_data = f.read()
                    
                    col2.download_button(
                        label="Download Excel",
                        data=excel_data,
                        file_name="linkedin_job_results.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                else:
                    st.warning("No jobs found matching your criteria.")

        except Exception as e:
            st.error(f"An error occurred: {str(e)}")

    st.sidebar.markdown("""
    ### Instructions
    1. Upload an Excel file containing company names (column should be named 'Company')
    2. Select job titles to search for
    3. Enter location (default: United Kingdom)
    4. Click 'Search Jobs' to start the search
    5. Results will show below
    6. Download results as CSV or Excel
    """)

if __name__ == "__main__":
    main()

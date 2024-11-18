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
st.set_page_config(page_title="Job Search Assistant", layout="wide")

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

def search_jobs(company, job_title, location, driver):
    jobs = []
    try:
        # Construct Google search URL for LinkedIn jobs
        search_query = f"{company} {job_title} {location} site:linkedin.com/jobs/view/"
        search_url = f"https://www.google.com/search?q={search_query}"
        
        driver.get(search_url)
        time.sleep(2)
        
        # Find all search result links
        links = driver.find_elements(By.CSS_SELECTOR, "div.g a")
        
        for link in links:
            try:
                url = link.get_attribute("href")
                # Only accept direct job listing URLs
                if "linkedin.com/jobs/view/" in url.lower() and "search?" not in url.lower():
                    # Get the parent element for more context
                    parent = link.find_element(By.XPATH, "./../../..")
                    title_element = parent.find_element(By.CSS_SELECTOR, "h3")
                    title = title_element.text
                    
                    # Get snippet text if available
                    try:
                        snippet = parent.find_element(By.CSS_SELECTOR, "div.VwiC3b").text
                    except:
                        snippet = ""
                    
                    # Check if the job title and company name are in the title or snippet
                    title_lower = title.lower()
                    snippet_lower = snippet.lower()
                    company_lower = company.lower()
                    job_title_lower = job_title.lower()
                    
                    if ((job_title_lower in title_lower or job_title_lower in snippet_lower) and 
                        (company_lower in title_lower or company_lower in snippet_lower)):
                        jobs.append({
                            'Company': company,
                            'Title': title,
                            'Location': location,
                            'URL': url
                        })
            except Exception as e:
                continue
                
    except Exception as e:
        st.warning(f"Error searching for {company}: {str(e)}")
    
    return jobs

def main():
    st.title("Job Search Assistant")

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

            # Search parameters
            st.subheader("Search Parameters")
            col1, col2, col3 = st.columns(3)
            with col1:
                job_titles = st.multiselect(
                    "Job Types",
                    ["Quality Assurance", "Quality Control", "Regulatory Affairs", 
                     "Quality Manager", "Regulatory Manager"],
                    default=["Quality Assurance", "Regulatory Affairs"]
                )
            with col2:
                location = st.text_input("Location", "United Kingdom")
            
            # Create a placeholder for the results table
            results_table = st.empty()
            
            if st.button("Search Jobs"):
                results = []
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                # Initialize results DataFrame with all companies
                results_df = pd.DataFrame({
                    'Company': df[company_column].unique(),
                    'Quality Jobs': ['Searching...' for _ in range(len(df[company_column].unique()))],
                    'Regulatory Jobs': ['Searching...' for _ in range(len(df[company_column].unique()))],
                })
                results_table.dataframe(results_df)
                
                try:
                    # Initialize driver once for all searches
                    driver = webdriver.Chrome(options=get_webdriver_options())
                    
                    total_searches = len(df[company_column]) * len(job_titles)
                    search_count = 0
                    
                    for idx, company in enumerate(df[company_column].unique()):
                        company_jobs = {'Quality': [], 'Regulatory': []}
                        
                        for job_title in job_titles:
                            status_text.text(f"Searching {job_title} jobs for {company}...")
                            jobs = search_jobs(company, job_title, location, driver)
                            
                            # Categorize jobs
                            for job in jobs:
                                if any(q in job_title.lower() for q in ['quality', 'qa', 'qc']):
                                    company_jobs['Quality'].append(job['URL'])
                                if 'regulatory' in job_title.lower():
                                    company_jobs['Regulatory'].append(job['URL'])
                            
                            search_count += 1
                            progress_bar.progress(search_count / total_searches)
                            time.sleep(2)  # Delay between searches
                        
                        # Update results for this company
                        results_df.at[idx, 'Quality Jobs'] = '\n'.join(company_jobs['Quality']) if company_jobs['Quality'] else 'No jobs found'
                        results_df.at[idx, 'Regulatory Jobs'] = '\n'.join(company_jobs['Regulatory']) if company_jobs['Regulatory'] else 'No jobs found'
                        
                        # Update the displayed table
                        results_table.dataframe(results_df)
                            
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
                        file_name="job_search_results.csv",
                        mime="text/csv"
                    )
                    
                    # Excel Download
                    buffer = pd.ExcelWriter('job_search_results.xlsx', engine='xlsxwriter')
                    results_df.to_excel(buffer, index=False)
                    buffer.save()
                    
                    with open('job_search_results.xlsx', 'rb') as f:
                        excel_data = f.read()
                    
                    col2.download_button(
                        label="Download Excel",
                        data=excel_data,
                        file_name="job_search_results.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                else:
                    st.warning("No jobs found matching your criteria.")

        except Exception as e:
            st.error(f"An error occurred: {str(e)}")

    st.sidebar.markdown("""
    ### Instructions
    1. Upload an Excel file containing company names
    2. Select the column containing company names
    3. Select job types to search for
    4. Enter location (default: United Kingdom)
    5. Click 'Search Jobs' to start the search
    6. Watch results populate in real-time
    7. Download final results as CSV or Excel
    """)

if __name__ == "__main__":
    main()

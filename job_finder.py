import streamlit as st
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
import pandas as pd
import time

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

def search_jobs(company, location, driver):
    jobs = []
    platforms = [
        {"name": "Google", "query": f"{company} jobs {location}"},
        {"name": "LinkedIn", "query": f"{company} jobs {location} site:linkedin.com/jobs/view/"},
        {"name": "Indeed UK", "query": f"{company} jobs {location} site:indeed.co.uk"},
        {"name": "Indeed US", "query": f"{company} jobs {location} site:indeed.com"},
        {"name": "PharmiWeb", "query": f"{company} jobs {location} site:pharmiweb.com"},
        {"name": "Company Careers", "query": f"{company} careers"}
    ]
    
    for platform in platforms:
        try:
            search_url = f"https://www.google.com/search?q={platform['query']}"
            driver.get(search_url)
            time.sleep(2)
            
            # Find all search result links
            links = driver.find_elements(By.CSS_SELECTOR, "div.g a")
            
            for link in links:
                try:
                    url = link.get_attribute("href")
                    title = link.text
                    
                    # Filter out generic pages
                    if "search?" not in url.lower() and "linkedin.com/jobs" in url.lower():
                        jobs.append({
                            'Platform': platform['name'],
                            'Company': company,
                            'Job Title': title,
                            'URL': url
                        })
                except Exception as e:
                    continue
        except Exception as e:
            st.warning(f"Error searching on {platform['name']} for {company}: {str(e)}")
    
    return jobs

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

            # Location input
            location = st.text_input("Location", "United Kingdom")
            st.info("💡 For multiple locations, separate with OR (e.g., 'United Kingdom OR Ireland')")
            
            # Create a placeholder for the results table
            results_table = st.empty()
            
            if st.button("Search Jobs"):
                # Initialize results DataFrame
                results_df = pd.DataFrame(columns=['Platform', 'Company', 'Job Title', 'URL'])
                results_table.dataframe(results_df)
                
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                try:
                    # Initialize driver once for all searches
                    driver = webdriver.Chrome(options=get_webdriver_options())
                    
                    total_companies = len(df[company_column].unique())
                    search_count = 0
                    
                    for idx, company in enumerate(df[company_column].unique()):
                        status_text.text(f"Searching jobs for {company}...")
                        
                        jobs = search_jobs(company, location, driver)
                        results_df = pd.concat([results_df, pd.DataFrame(jobs)], ignore_index=True)
                        
                        search_count += 1
                        progress_bar.progress(search_count / total_companies)
                        
                        # Update the displayed table
                        results_table.dataframe(results_df)
                        
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
    3. Enter location (default: United Kingdom)
    4. Click 'Search Jobs' to start
    5. Watch results populate in real-time
    6. Download results as CSV or Excel
    """)

if __name__ == "__main__":
    main()

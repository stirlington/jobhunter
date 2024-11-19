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

def search_jobs(company, driver):
    jobs = []
    platforms = [
        {"name": "Google", "query": f"{company} jobs"},
        {"name": "LinkedIn", "query": f"{company} jobs site:linkedin.com/jobs/view/"},
        {"name": "Indeed UK", "query": f"{company} jobs site:indeed.co.uk"},
        {"name": "Indeed US", "query": f"{company} jobs site:indeed.com"},
        {"name": "PharmiWeb", "query": f"{company} jobs site:pharmiweb.com"},
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
                    if "search?" not in url.lower():
                        location = "Location not specified"  # Default location
                        
                        # Extract location for specific platforms
                        if platform['name'] == "LinkedIn":
                            try:
                                location_element = link.find_element(By.XPATH, "./../../..//span[contains(@class, 'job-card-container__metadata-item')]")
                                location = location_element.text if location_element else location
                            except:
                                pass
                        elif platform['name'] in ["Indeed UK", "Indeed US"]:
                            try:
                                location_element = link.find_element(By.XPATH, "./../../..//div[contains(@class, 'companyLocation')]")
                                location = location_element.text if location_element else location
                            except:
                                pass
                        
                        jobs.append({
                            'Platform': platform['name'],
                            'Company': company,
                            'Job Title': title,
                            'Location': location,
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

            # Create a placeholder for the results table
            results_table = st.empty()
            results_df = pd.DataFrame(columns=['Platform', 'Company', 'Job Title', 'Location', 'URL'])
            results_table.dataframe(results_df)

            if st.button("Search Jobs"):
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                try:
                    # Initialize driver once for all searches
                    driver = webdriver.Chrome(options=get_webdriver_options())
                    
                    total_companies = len(df[company_column].unique())
                    search_count = 0
                    
                    for idx, company in enumerate(df[company_column].unique()):
                        status_text.text(f"Searching jobs for {company}...")
                        
                        jobs = search_jobs(company, driver)
                        results_df = pd.concat([results_df, pd.DataFrame(jobs)], ignore_index=True)
                        
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

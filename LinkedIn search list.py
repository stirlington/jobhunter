import streamlit as st
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import pandas as pd
import time

# Configure Streamlit page
st.set_page_config(page_title="LinkedIn Job Search Assistant", layout="wide")

@st.cache_resource
def get_webdriver_options():
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-notifications')
    options.add_argument('--disable-popup-blocking')
    options.add_argument('--blink-settings=imagesEnabled=false')
    return options

# Rest of your code remains the same, but replace the driver initialization with:
driver = webdriver.Chrome(
    service=Service(ChromeDriverManager().install()),
    options=get_webdriver_options()
)

st.title("LinkedIn Job Search Assistant")

# File upload
st.subheader("Upload Company List")
uploaded_file = st.file_uploader("Choose an Excel file", type=['xlsx'])

if uploaded_file is not None:
    df = pd.read_excel(uploaded_file)
    st.write("Uploaded companies:", df)

    # Search parameters
    st.subheader("Search Parameters")
    job_title = st.text_input("Job Title")
    location = st.text_input("Location")

    if st.button("Search Jobs"):
        # Initialize results DataFrame
        results_df = pd.DataFrame(columns=['Company', 'Title', 'Location', 'URL'])
        
        try:
            for company in df['Company'].unique():  # Assuming company column is named 'Company'
                # Construct LinkedIn search URL
                search_url = f"https://www.linkedin.com/jobs/search/?keywords={job_title}&location={location}&company={company}"
                driver.get(search_url)
                time.sleep(2)  # Wait for page to load
                
                try:
                    # Find job listings
                    job_cards = WebDriverWait(driver, 10).until(
                        EC.presence_of_all_elements_located((By.CLASS_NAME, "job-card-container"))
                    )
                    
                    for job in job_cards[:5]:  # Limit to first 5 results per company
                        try:
                            title = job.find_element(By.CLASS_NAME, "job-card-list__title").text
                            job_location = job.find_element(By.CLASS_NAME, "job-card-container__metadata-item").text
                            url = job.find_element(By.CLASS_NAME, "job-card-list__title").get_attribute("href")
                            
                            # Add to results DataFrame
                            new_row = {
                                'Company': company,
                                'Title': title,
                                'Location': job_location,
                                'URL': url
                            }
                            results_df = pd.concat([results_df, pd.DataFrame([new_row])], ignore_index=True)
                        except:
                            continue
                            
                except:
                    st.write(f"No jobs found for {company}")
                    continue
                
        finally:
            driver.quit()
            
        # Display results
        st.subheader("Search Results")
        st.write(results_df)
        
        # Download button for results
        if not results_df.empty:
            csv = results_df.to_csv(index=False)
            st.download_button(
                label="Download Results",
                data=csv,
                file_name="linkedin_job_results.csv",
                mime="text/csv"
            )

st.sidebar.markdown("""
### Instructions
1. Upload an Excel file containing company names
2. Enter job title and location
3. Click 'Search Jobs' to start the search
4. Results will appear below
5. Download results as CSV
""")

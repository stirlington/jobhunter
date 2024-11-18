import pandas as pd
import streamlit as st
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
import time

def setup_chrome_options():
    options = uc.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--disable-software-rasterizer')
    return options

def search_job_vacancies(company_name):
    quality_jobs = []
    regulatory_jobs = []
    
    try:
        driver = uc.Chrome(options=setup_chrome_options())
        
        search_terms = {
            "quality": f"{company_name} quality jobs",
            "regulatory": f"{company_name} regulatory jobs"
        }
        
        job_sites = ["linkedin.com/jobs", "indeed.com", "careers", "workday.com", "jobs"]
        
        for job_type, search_term in search_terms.items():
            try:
                driver.get(f"https://www.google.com/search?q={search_term}")
                time.sleep(3)  # Increased wait time
                
                links = driver.find_elements(By.TAG_NAME, "a")
                found_jobs = False
                
                for link in links:
                    try:
                        href = link.get_attribute("href")
                        if href and any(site in href.lower() for site in job_sites):
                            link_text = link.text.lower()
                            if any(keyword in link_text for keyword in ["job", "career", "position", "vacancy", "opportunities"]):
                                job_info = {
                                    "url": href,
                                    "title": link.text.strip() or "Job Posting"
                                }
                                if job_type == "quality":
                                    quality_jobs.append(job_info)
                                else:
                                    regulatory_jobs.append(job_info)
                                found_jobs = True
                    except:
                        continue
                
                if not found_jobs:
                    job_info = {"url": "No jobs found", "title": "No jobs found"}
                    if job_type == "quality":
                        quality_jobs.append(job_info)
                    else:
                        regulatory_jobs.append(job_info)
                    
            except Exception as e:
                st.warning(f"Search error for {job_type} jobs: {str(e)}")
                job_info = {"url": "Error searching", "title": "Error occurred"}
                if job_type == "quality":
                    quality_jobs.append(job_info)
                else:
                    regulatory_jobs.append(job_info)
        
        driver.quit()
    except Exception as e:
        st.error(f"Browser error: {str(e)}")
        return [{"url": "Browser error", "title": "Error"}], [{"url": "Browser error", "title": "Error"}]
    
    return quality_jobs, regulatory_jobs

def main():
    st.set_page_config(page_title="Job Vacancy Finder", layout="wide")
    
    st.title("Job Vacancy Finder")
    st.write("Upload a spreadsheet with company names to find quality and regulatory job vacancies")
    
    uploaded_file = st.file_uploader("Choose an Excel file", type="xlsx")
    
    if uploaded_file is not None:
        try:
            df = pd.read_excel(uploaded_file)
            
            if 'Company Name' not in df.columns:
                st.error("Please ensure your spreadsheet has a 'Company Name' column")
                return
            
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            # Create new columns
            df['Quality Jobs'] = None
            df['Quality Job Titles'] = None
            df['Regulatory Jobs'] = None
            df['Regulatory Job Titles'] = None
            
            for index, row in df.iterrows():
                company_name = row['Company Name']
                status_text.text(f"Searching jobs for {company_name}...")
                
                quality_jobs, regulatory_jobs = search_job_vacancies(company_name)
                
                # Format quality jobs
                quality_urls = []
                quality_titles = []
                for job in quality_jobs:
                    quality_urls.append(job['url'])
                    quality_titles.append(job['title'])
                
                # Format regulatory jobs
                regulatory_urls = []
                regulatory_titles = []
                for job in regulatory_jobs:
                    regulatory_urls.append(job['url'])
                    regulatory_titles.append(job['title'])
                
                df.at[index, 'Quality Jobs'] = '\n'.join(quality_urls)
                df.at[index, 'Quality Job Titles'] = '\n'.join(quality_titles)
                df.at[index, 'Regulatory Jobs'] = '\n'.join(regulatory_urls)
                df.at[index, 'Regulatory Job Titles'] = '\n'.join(regulatory_titles)
                
                progress_bar.progress((index + 1) / len(df))
            
            status_text.text("Search completed!")
            
            # Preview the results
            st.write("Preview of results:")
            st.dataframe(df)
            
            # Download buttons
            col1, col2 = st.columns(2)
            
            # CSV Download
            csv = df.to_csv(index=False).encode('utf-8')
            col1.download_button(
                label="Download CSV",
                data=csv,
                file_name="job_vacancies_results.csv",
                mime="text/csv"
            )
            
            # Excel Download
            buffer = pd.ExcelWriter('job_vacancies_results.xlsx', engine='xlsxwriter')
            df.to_excel(buffer, index=False)
            buffer.save()
            
            with open('job_vacancies_results.xlsx', 'rb') as f:
                excel_data = f.read()
            
            col2.download_button(
                label="Download Excel",
                data=excel_data,
                file_name="job_vacancies_results.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            
        except Exception as e:
            st.error(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    main()

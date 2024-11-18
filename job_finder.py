import pandas as pd
import streamlit as st
from playwright.sync_api import sync_playwright
import time
import os
import re

# Install Playwright browsers on startup
os.system('playwright install')
os.system('playwright install-deps')

@st.cache_data
def search_job_vacancies(company_name):
    quality_jobs = []
    regulatory_jobs = []
    
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            # More specific search terms
            search_terms = {
                "quality": [
                    f"{company_name} quality assurance jobs",
                    f"{company_name} quality control jobs",
                    f"{company_name} QA jobs"
                ],
                "regulatory": [
                    f"{company_name} regulatory affairs jobs",
                    f"{company_name} regulatory compliance jobs"
                ]
            }
            
            job_sites = [
                "linkedin.com/jobs",
                "indeed.com/jobs",
                "glassdoor.com/job",
                "careers",
                "/jobs/",
                "workday.com",
                "lever.co",
                "greenhouse.io"
            ]
            
            job_keywords = [
                "quality",
                "qa ",
                "regulatory",
                "compliance",
                "assurance",
                "affairs"
            ]
            
            for job_type, searches in search_terms.items():
                for search_term in searches:
                    try:
                        page.goto(f"https://www.google.com/search?q={search_term}")
                        time.sleep(2)
                        
                        # Get all links and their parent elements
                        links = page.query_selector_all("a")
                        found_jobs = False
                        
                        for link in links:
                            try:
                                href = link.get_attribute("href")
                                if not href:
                                    continue
                                    
                                # Get the full text context around the link
                                link_text = link.inner_text().lower()
                                parent_text = link.evaluate('(element) => element.parentElement.textContent').lower()
                                
                                # Check if it's a job listing
                                is_job_site = any(site in href.lower() for site in job_sites)
                                has_job_keyword = any(keyword in link_text for keyword in job_keywords) or \
                                                any(keyword in parent_text for keyword in job_keywords)
                                is_job_posting = any(word in link_text or word in parent_text 
                                                   for word in ["job", "career", "position", "vacancy", "opening"])
                                
                                if is_job_site and has_job_keyword and is_job_posting:
                                    # Clean up the title
                                    title = link_text.strip()
                                    if not title:
                                        title = parent_text.strip()
                                    
                                    # Remove common unwanted text
                                    title = re.sub(r'(apply now|view job|posted|ago|days?|hours?|minutes?)', '', title, flags=re.IGNORECASE)
                                    title = ' '.join(title.split())  # Clean up whitespace
                                    
                                    job_info = {
                                        "url": href,
                                        "title": title or "Job Posting"
                                    }
                                    
                                    # Avoid duplicates
                                    if job_type == "quality":
                                        if job_info not in quality_jobs:
                                            quality_jobs.append(job_info)
                                            found_jobs = True
                                    else:
                                        if job_info not in regulatory_jobs:
                                            regulatory_jobs.append(job_info)
                                            found_jobs = True
                                            
                            except Exception as e:
                                continue
                        
                    except Exception as e:
                        st.warning(f"Search error for {search_term}: {str(e)}")
                
                # Add "No jobs found" only if no jobs were found across all searches for this type
                if job_type == "quality" and not quality_jobs:
                    quality_jobs.append({"url": "No jobs found", "title": "No jobs found"})
                elif job_type == "regulatory" and not regulatory_jobs:
                    regulatory_jobs.append({"url": "No jobs found", "title": "No jobs found"})
            
            browser.close()
            
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
            
            if 'search_completed' not in st.session_state:
                st.session_state.search_completed = False
                st.session_state.results_df = None
            
            if not st.session_state.search_completed:
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
                st.session_state.search_completed = True
                st.session_state.results_df = df
            
            # Use cached results for display and download
            df = st.session_state.results_df
            
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

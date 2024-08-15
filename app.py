import streamlit as st
import requests
from bs4 import BeautifulSoup
import re
import csv
from urllib.parse import urlparse

# List of domains to exclude from email scraping
EXCLUDE_DOMAINS = {
    "www.classcentral.com",
    "www.youtube.com",
    "www.simplilearn.com",
    "www.udemy.com",
    "www.coursera.org",
    "www.linkedin.com",
    "www.geeksforgeeks.org",
    "www.shiksha.com",
    "google.com",
    "pwskills.com",
    "www.indeed.com",
    "www.scaler.com",
    "www.datacamp.com"
}

# Function to check if a URL should be excluded
def should_exclude(url):
    parsed_url = urlparse(url)
    domain = parsed_url.netloc
    return any(excluded_domain in domain for excluded_domain in EXCLUDE_DOMAINS) or "google" in domain

# Function to find emails in a webpage
def find_emails(url):
    emails = set()
    try:
        response = requests.get(url, timeout=5)
        soup = BeautifulSoup(response.text, 'html.parser')

        # Search for emails in the rendered HTML content
        for mail in re.findall(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,4}", soup.prettify()):
            emails.add(mail)

        # Check footer for emails
        footer = soup.find('footer')
        if footer:
            for mail in re.findall(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,4}", footer.prettify()):
                emails.add(mail)

        # Search for "Contact", "Connect", "About" links and check those pages for emails
        for link in soup.find_all('a', href=True):
            if any(keyword in link.text.lower() for keyword in ['contact', 'connect', 'about']):
                linked_url = requests.compat.urljoin(url, link['href'])
                try:
                    linked_response = requests.get(linked_url, timeout=5)
                    linked_soup = BeautifulSoup(linked_response.text, 'html.parser')
                    for mail in re.findall(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,4}", linked_soup.prettify()):
                        emails.add(mail)
                except:
                    pass

    except Exception as e:
        st.write(f"Error fetching {url}: {e}")

    return list(emails)

# Function to perform a direct Google search and scrape URLs
def direct_google_search(query, num_results, country):
    google_domains = {
        "global": "www.google.com",
        "us": "www.google.com",
        "uk": "www.google.co.uk",
        "ca": "www.google.ca",
        "au": "www.google.com.au",
        "in": "www.google.co.in",
        "de": "www.google.de",
        "fr": "www.google.fr",
        "jp": "www.google.co.jp",
        "br": "www.google.com.br",
        "za": "www.google.co.za"
    }

    domain = google_domains.get(country, "www.google.com")
    search_url = f"https://{domain}/search?q={query}&num={num_results}"
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(search_url, headers=headers)
    soup = BeautifulSoup(response.text, 'html.parser')
    urls = []

    for link in soup.find_all('a', href=True):
        href = link['href']
        if "url?q=" in href and "webcache" not in href:
            url = href.split("?q=")[1].split("&sa=U")[0]
            if not should_exclude(url):
                urls.append(url)

    return urls[:num_results]

# Main function to handle search and email scraping
def main():
    st.title("Google Search Email Scraper")
    st.write("Enter a keyword to search for, and the app will scrape Google for the top URLs and extract emails from those websites.")

    keyword = st.text_input("Enter a keyword to search:")
    num_results = st.slider("Number of results to scrape (max 200):", 1, 200, 50)
    country = st.selectbox("Select Country:", ["global", "us", "uk", "ca", "au", "in", "de", "fr", "jp", "br", "za"])

    if st.button("Start Scraping"):
        if keyword:
            with st.spinner("Scraping Google search results..."):
                urls = direct_google_search(keyword, num_results, country)
                st.write(f"Found {len(urls)} URLs.")

                results = []
                for url in urls:
                    st.write(f"Scraping emails from {url}...")
                    emails = find_emails(url)
                    if emails:
                        results.append([url] + emails)
                    else:
                        results.append([url, "No emails found"])

                # Display results in a table
                st.write("Scraping completed! Results:")
                st.table(results)

                # Download results as CSV
                csv_data = convert_to_csv(results)
                st.download_button(
                    label="Download results as CSV",
                    data=csv_data,
                    file_name='scraped_emails.csv',
                    mime='text/csv',
                )
        else:
            st.warning("Please enter a keyword to search.")

# Helper function to convert results to CSV format
def convert_to_csv(data):
    output = []
    header = ["URL", "Email 1", "Email 2", "Email 3", "..."]
    output.append(",".join(header) + "\n")
    for row in data:
        output.append(",".join(row) + "\n")
    return "".join(output)

if __name__ == "__main__":
    main()

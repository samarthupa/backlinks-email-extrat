import streamlit as st
import requests
from bs4 import BeautifulSoup
import re
from urllib.parse import urlparse, urljoin

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

# List of domains where specific email filtering is required
SPECIFIC_DOMAINS = ["medium.com", "reddit.com", "quora.com"]

# Function to check if a URL should be excluded
def should_exclude(url):
    parsed_url = urlparse(url)
    domain = parsed_url.netloc
    path = parsed_url.path
    return any(excluded_domain in domain for excluded_domain in EXCLUDE_DOMAINS) or "google" in domain or path.startswith("/search")

# Function to validate emails with additional domain-specific filtering
def is_valid_email(email, url):
    # Basic email validation regex
    valid_email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    # Exclude emails that look like image filenames or have non-standard patterns
    invalid_patterns = [r'\.png$', r'\.jpg$', r'\.jpeg$', r'\.gif$', r'\.webp$', r'^jhsuysyuuwnoi@jksbhs\.js$', r'\.svg$']

    if re.match(valid_email_pattern, email):
        for pattern in invalid_patterns:
            if re.search(pattern, email):
                return False
        
        # Specific domain filtering logic
        parsed_url = urlparse(url)
        for specific_domain in SPECIFIC_DOMAINS:
            if specific_domain in parsed_url.netloc:
                if email.endswith(f"@{specific_domain}"):
                    return False
        return True
    return False

# Function to find emails in a webpage
def find_emails(url):
    emails = set()
    try:
        response = requests.get(url, timeout=5)
        soup = BeautifulSoup(response.text, 'html.parser')

        # Search for emails in `mailto:` links
        for mailto in soup.find_all('a', href=True):
            if 'mailto:' in mailto['href']:
                email = mailto['href'].split('mailto:')[1]
                if is_valid_email(email, url):
                    emails.add(email)

        # Search for emails in the rendered HTML content
        for mail in re.findall(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,4}", soup.prettify()):
            if is_valid_email(mail, url):
                emails.add(mail)

        # Check "Contact", "Connect", "About" links and check those pages for emails
        for link in soup.find_all('a', href=True):
            if any(keyword in link.text.lower() for keyword in ['contact', 'connect', 'about']):
                linked_url = urljoin(url, link['href'])
                if not should_exclude(linked_url):  # Prevent circular references and scraping excluded domains
                    try:
                        linked_response = requests.get(linked_url, timeout=5)
                        linked_soup = BeautifulSoup(linked_response.text, 'html.parser')
                        for mail in re.findall(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,4}", linked_soup.prettify()):
                            if is_valid_email(mail, linked_url):
                                emails.add(mail)
                    except:
                        pass

    except requests.RequestException:
        # Attempt to fetch the page from Google Cache if the URL fails to connect
        cache_url = f"https://webcache.googleusercontent.com/search?q=cache:{url}"
        try:
            cache_response = requests.get(cache_url, timeout=5)
            cache_soup = BeautifulSoup(cache_response.text, 'html.parser')

            # Search for emails in the cached page
            for mail in re.findall(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,4}", cache_soup.prettify()):
                if is_valid_email(mail, url):
                    emails.add(mail)
        except:
            pass

    return list(emails)

# Function to perform a direct Google search and scrape URLs
def direct_google_search(query, num_results):
    search_url = f"https://www.google.com/search?q={query}&num={num_results}"
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
    st.write("Enter a keyword to search for, or provide a list of URLs. The app will scrape Google for the top URLs or use the provided URLs and extract emails from those websites.")

    # Reordering the input fields
    keyword = st.text_input("Enter a keyword to search (optional if URLs are provided):")
    num_results = st.slider("Number of results to scrape (max 200):", 1, 200, 50)
    urls_input = st.text_area("Enter URLs (one per line, optional):")

    urls_provided = [url.strip() for url in urls_input.split("\n") if url.strip()]

    if st.button("Start Scraping"):
        if urls_provided or keyword:
            urls = urls_provided if urls_provided else direct_google_search(keyword, num_results)
            st.write(f"Found {len(urls)} URLs.")

            results = []
            for url in urls:
                if not should_exclude(url):
                    st.write(f"Scraping emails from {url}...")
                    emails = find_emails(url)
                    if emails:  # Only add URLs with found emails to the results
                        results.append([url] + emails)

            # Display results in a table
            st.write("Scraping completed! Results:")
            st.table(results)

            # Download results as CSV
            if results:  # Only enable download if there are results with emails
                csv_data = convert_to_csv(results)
                st.download_button(
                    label="Download results as CSV",
                    data=csv_data,
                    file_name='scraped_emails.csv',
                    mime='text/csv',
                )
            else:
                st.write("No valid emails found in the search results or provided URLs.")
        else:
            st.warning("Please enter a keyword or provide URLs to scrape.")

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

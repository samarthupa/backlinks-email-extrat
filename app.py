import streamlit as st
import requests
from bs4 import BeautifulSoup
from googlesearch import search
import csv
import re

# Function to find emails in a webpage
def find_emails(url):
    emails = set()
    try:
        response = requests.get(url, timeout=5)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Search for emails in the page content
        for mail in re.findall(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,4}", soup.text):
            emails.add(mail)
        
        # Check footer for emails
        footer = soup.find('footer')
        if footer:
            for mail in re.findall(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,4}", footer.text):
                emails.add(mail)
        
        # Search for "Contact", "Connect", "About" links and check those pages for emails
        for link in soup.find_all('a', href=True):
            if any(keyword in link.text.lower() for keyword in ['contact', 'connect', 'about']):
                linked_url = requests.compat.urljoin(url, link['href'])
                try:
                    linked_response = requests.get(linked_url, timeout=5)
                    linked_soup = BeautifulSoup(linked_response.text, 'html.parser')
                    for mail in re.findall(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,4}", linked_soup.text):
                        emails.add(mail)
                except:
                    pass

    except Exception as e:
        st.write(f"Error fetching {url}: {e}")
    
    return list(emails)

# Streamlit UI
st.title("Email Scraper Tool")

keyword = st.text_input("Enter a keyword to search:")
num_results = st.slider("Number of results to scrape (max 200):", 1, 200, 50)

if st.button("Search and Scrape Emails"):
    if keyword:
        st.write(f"Searching Google for '{keyword}'...")
        urls = []
        for url in search(keyword, num=num_results, stop=num_results, pause=2):
            urls.append(url)
        
        st.write(f"Found {len(urls)} URLs.")
        
        results = []
        for url in urls:
            st.write(f"Scraping emails from {url}...")
            emails = find_emails(url)
            if emails:
                results.append([url] + emails)
            else:
                results.append([url, "No emails found"])
        
        # Output results to CSV
        st.write("Scraping completed. Preparing CSV file...")
        with open('scraped_emails.csv', 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(["URL", "Email 1", "Email 2", "Email 3", "..."])
            writer.writerows(results)
        
        st.success("Scraping completed! Download the results:")
        st.download_button(label="Download CSV", data=open('scraped_emails.csv', 'rb').read(), file_name="scraped_emails.csv", mime="text/csv")

    else:
        st.warning("Please enter a keyword to search.")

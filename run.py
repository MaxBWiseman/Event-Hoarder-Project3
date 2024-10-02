import gspread
import requests
from bs4 import BeautifulSoup

gc = gspread.service_account(filename="creds.json")

sheet = gc.open('Project3Python').sheet1

# Get job title from user
job_title = input('Enter job title: ').replace(' ', '%20')
country = input('Enter country: ').replace(' ', '%20')
# We must replace spaces with %20 to make the URL valid, this is visible in a normal search URL on LinkedIn

# Construct the URL with the user-specified job title
URL = f'https://www.linkedin.com/jobs/search?keywords={job_title}&location={country}&geoId=103644278&trk=public_jobs_jobs-search-bar_search-submit&position=1&pageNum=0'

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
}
# We need to specify a user agent to avoid being blocked by LinkedIn

page = requests.get(URL, headers=headers)
# Send a GET request to the URL with the headers

if page.status_code != 200:
    print(f"Failed to retrieve search results: {page.status_code}")
else:
    soup = BeautifulSoup(page.content, 'html.parser')
# If the status code is not 200, print an error message. Otherwise, parse the HTML content with BeautifulSoup
# html.parser is the default parser for BeautifulSoup and must be specified, we use content instead of text because we want the raw HTML content
    results = soup.find_all('a', class_='base-card__full-link')
# After looking on dev tools on linkedIn I found the element and class I want to collect
    if not results:
        print("No job links found. Please check the class name or ensure the page structure hasn't changed.")
    else:
        for result in results:
            print(result)
            
# I have decided I will scrape linkedin for job postings and then manipulate the data in some way usefull to me.
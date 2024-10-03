import gspread
import requests
from bs4 import BeautifulSoup
from collections import Counter
import threading
import time
import sys
import itertools

# threading is used to call the Spinner class in a separate thread
# itertools is used to cycle through the spinner characters


class Spinner:
    def __init__(self, message='Loading...'):
        self.message = message
        self.spinner = itertools.cycle(['|', '/', '-', '\\'])
# Creates an infinite iterator that cycles through the characters in the list
        self.stop_running = threading.Event()
# Object used to stop the thread
        
    def start(self):
        threading.Thread(target=self._spin).start()
# The threading.Thread class is used to create a new thread, the target is the _spin method,
# this allows spinner to run in the background while the main program continues to run
    
    def _spin(self):
        while not self.stop_running.is_set():
# Continue loop until self.stop_running is set
            sys.stdout.write(f'\r{self.message} {next(self.spinner)}')
# sys.stdout.write is used to write to the standard output, \r is used to return to the start of the line,
# allowing the spinner to overwrite the previous character
            sys.stdout.flush()
# Forces the output to be displayed immediately
            time.sleep(0.1)
            sys.stdout.write('\b')
# \b is used to move the cursor back one character to prepare the next spinning character
    
    def stop(self):
        self.stop_running.set()
        sys.stdout.write('\r' + ' ' * (len(self.message) + 2) + '\r')
# The stop_running event is set, the line is cleared by writing spaces and returning to the start of the line
        sys.stdout.flush()
# Write to console immediately


gc = gspread.service_account(filename="creds.json")
# This is the file that contains the credentials for the Google Sheets API
sheet = gc.open('Project3Python').sheet1
# Opens the Google Sheet called Project3Python and selects the first sheet

product = input('Enter event type or name: ').replace(' ', '%20')
location = input('Enter location: ').replace(' ', '%20')
# The replace method replaces spaces with %20, which is the URL encoding for a space

url = f'https://www.eventbrite.com/d/united-kingdom--{location}/{product}/?page=1'
url2 = f'https://www.eventbrite.com/d/united-kingdom--{location}/{product}/?page=2'
# product and location are inserted into the URL with f-strings, 2 pages are used to get more events

spinner = Spinner('Loading events...')
spinner.start()
# The spinner is started

page = requests.get(url)
page2 = requests.get(url2)
# The requests.get method is used to get the HTML content of the URL

spinner.stop()
# The spinner is stopped

soup = BeautifulSoup(page.content, 'html.parser')
soup2 = BeautifulSoup(page2.content, 'html.parser')
# You must specify the parser to use, in this case 'html.parser' for beautifulsoup to work

events = soup.find_all('a', class_='event-card-link')
events2 = soup2.find_all('a', class_='event-card-link')
# Fine all the elements with the tag 'a' and the class 'event-card-link' in the returned HTML

event_data = []
# Create an empty list to store the event data, to manipulate it later

for event in events + events2:
# Combines the two lists of events
    event_info = {
        'name': event.get('aria-label', '').replace('View', '').strip(),
# Without this the word "View" will be included in the name of the event
        'location': event['data-event-location'],
        'url': event['href']
    }
# The event name, location and URL are stored in a dictionary
    event_data.append(event_info)
# event_info is appended to the event_data list
    
unique_events = []
# Create an empty list to store the unique events, checked by seen_urls
seen_urls = set()
# A set is a collection of unique elements, which makes removing duplicates easier when passed through.

for data in event_data:
    if data['url'] not in seen_urls:
        unique_events.append(data)
        seen_urls.add(data['url'])
# If the iterated URL is not in seen_urls which is a unique set, it is appended to unique_events and added to seen_urls.
# seen_urls acts as a filter to remove duplicates

def display_events(events, start_index, end_index):
    for data in events[start_index:end_index]:
        event_url = data['url']
        page_detail = requests.get(event_url)
        page_detail_soup = BeautifulSoup(page_detail.content, 'html.parser')
    
        price_div = page_detail_soup.find('div', class_="conversion-bar__panel-info")
        event_price = price_div.get_text(strip=True) if price_div else 'Free'

        summary = page_detail_soup.find('p', class_='summary')
        event_summary = summary.get_text(strip=True) if summary else 'No summary available'

        date_time = page_detail_soup.find('span', class_='date-info__full-datetime')
        event_date_time = date_time.get_text(strip=True) if date_time else 'No date and time available'
    
        print(f'-------------------------------------\n{data["name"]},\n{data["location"]}\nDate & Time: {event_date_time}\nSummary: {event_summary}\nPrice: {event_price}')

page_size = 5
# The number of events to display per page
total_events = len(unique_events)
# The total number of unique events
current_page = 0
seen_tags_counter = Counter()
# A counter is a dictionary subclass for counting hashable objects
# This stores the number of occurrences of each tag
seen_events_counter = 0
# The number of unique events seen

while current_page * page_size < total_events:
# While the current page multiplied by the page size is less than the total number of events
    start_index = current_page * page_size
# The start index is the current page multiplied by the page size ex. 0 * 5 = 0
    end_index = start_index + page_size
# The end index is the start index plus the page size ex. 0 + 5 = 5
    display_events(unique_events, start_index, end_index)
# The display_events function is called with the unique events, start index and end index as arguments
# This will display the calculated number of events per press of 'Y'
    
    spinner = Spinner('Counting tags...')
    spinner.start()
    
    # Count tags for the displayed events
    for data in unique_events[start_index:end_index]:
# : is used to access the key-value pairs in the dictionary
        event_url = data['url']
        page_detail = requests.get(event_url)
# The requests.get method is used to get the HTML content of the URL
        page_detail_soup = BeautifulSoup(page_detail.content, 'html.parser')
        tags = page_detail_soup.find_all('a', class_='tags-link')
        for tag in tags:
            seen_tags_counter[tag.get_text(strip=True)] += 1
# The tags are found in the HTML and added to the seen_tags_counter.

    spinner.stop()
    

    seen_events_counter += len(unique_events[start_index:end_index])
# seen_tags_counter is incremented by the number of unique events displayed

    most_common_tags = seen_tags_counter.most_common(5)
#
    print(f'\n-------------------------------------\nThe most common tags for the last {seen_tags_counter} events are:')
    for tag, count in most_common_tags:
        print(f'{tag}: {count}')
    
    if end_index >= total_events:
        break
# If the end index is greater than or equal to the total number of events, the loop will break
    
    user_input = input("\nPress 'Y' to see more events, or any other key to exit: ").strip().lower()
    if user_input != 'y':
        break
# The user is prompted to press 'Y' to see more events, if any other key is pressed the loop will break
    
    current_page += 1
import requests
from bs4 import BeautifulSoup
import pandas as pd
import time

def get_celebrity_links(url):
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')
    links = []

    # Find all links within the main content area that point to celebrity profiles
    # These links typically contain the celebrity's name and a unique ID
    # Example: /simon-cowell-horoscope-natal-chart
    for a_tag in soup.find_all('a', href=True):
        # The links on the main page are relative paths like /simon-cowell-horoscope-natal-chart
        # The actual individual page is on www.astro-seek.com/birth-chart/...
        if '-horoscope-natal-chart' in a_tag['href']:
            # Construct the full URL using the correct base domain for individual charts
            full_link = "https://www.astro-seek.com/birth-chart" + a_tag['href'].replace('-horoscope-natal-chart', '-horoscope')
            links.append(full_link)
    return list(set(links)) # Return unique links

def scrape_celebrity_details(url):
    print(f"Scraping details from: {url}")
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')
    
    details = {
        'Name': '',
        'Birth Date': '',
        'Birth Time': '',
        'Birth Place': '',
        'Profession': ''
    }

    # Extract Name
    name_tag = soup.find('h1')
    if name_tag:
        details['Name'] = name_tag.text.strip().split('-')[0].strip()

    # Extract Birth Date, Time, Place, Profession
    # The structure seems to be in a div with class 'w50p fl' and 'w50p fr'
    # Let's try to find the specific <p> tags within these divs
    
    # Birth data (Date, Place, Profession)
    birth_info_div = soup.find('div', class_='w50p fl')
    if birth_info_div:
        p_tags = birth_info_div.find_all('p')
        for p in p_tags:
            text = p.get_text(separator=' ', strip=True)
            if 'Date of Birth:' in text:
                details['Birth Date'] = text.replace('Date of Birth:', '').strip()
            elif 'Birth place:' in text:
                details['Birth Place'] = text.replace('Birth place:', '').strip()
            elif 'Occupation:' in text:
                details['Profession'] = text.replace('Occupation:', '').strip()

    # Birth Time (often in a separate div or with specific formatting)
    # The example page for Simon Cowell shows "unknown time" in a <p> tag within a div.w50p fr
    time_info_div = soup.find('div', class_='w50p fr')
    if time_info_div:
        time_p = time_info_div.find('p')
        if time_p:
            time_text = time_p.get_text(strip=True)
            if 'unknown time' in time_text:
                details['Birth Time'] = 'unknown'
            else:
                # This part needs careful inspection of actual pages
                # For now, let's assume if it's not 'unknown', it's the time
                # This might need further refinement based on actual data patterns
                details['Birth Time'] = time_text.strip()

    return details

main_url = "https://famouspeople.astro-seek.com/"

print(f"Getting celebrity links from {main_url}")
celebrity_links = get_celebrity_links(main_url)
print(f"Found {len(celebrity_links)} celebrity links.")

all_celebrity_data = []

# Limit to a smaller number of links for testing to avoid long execution times and potential blocking
# For full data collection, this limit would be removed or handled with pagination
for link in celebrity_links[:10]: # Scrape only the first 10 links for now
    data = scrape_celebrity_details(link)
    all_celebrity_data.append(data)
    time.sleep(1) # Be polite and avoid overwhelming the server

df = pd.DataFrame(all_celebrity_data)
df.to_csv('famous_people_detailed_astro_seek.csv', index=False)
print("Detailed celebrity data scraped and saved to famous_people_detailed_astro_seek.csv")

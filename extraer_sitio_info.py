import os
import re
import time
import requests
import pandas as pd
from bs4 import BeautifulSoup

# --- CONFIGURATION ---
# WARNING: This API Key has been shared publicly. 
# It is highly recommended to delete it and generate a new one.
API_KEY = "" 

# --- FILENAMES FOR SAVING ---
CSV_FILENAME = 'dental_clinics_madrid_places.csv'
EXCEL_FILENAME = 'dental_clinics_madrid_places.xlsx'

def find_dental_clinics(query, api_key):
    """
    Uses the Places API 'Text Search' to find a list of clinics.
    Returns a list of place_ids.
    """
    search_url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
    all_place_ids = []
    
    params = {'query': query, 'key': api_key, 'type': 'dental_clinic', 'language': 'es'}
    
    try:
        # Added a timeout to prevent the script from hanging on this request.
        res = requests.get(search_url, params=params, timeout=15) # <-- IMPROVEMENT
        results = res.json()

        if results['status'] == 'OK':
            for place in results['results']:
                all_place_ids.append(place['place_id'])
        elif results['status'] != 'ZERO_RESULTS':
            print(f"  -> API Error finding places: {results.get('status')} - {results.get('error_message', '')}")

    except requests.exceptions.Timeout:
        print("  -> The search request timed out. Moving to the next postcode.")
    except Exception as e:
        print(f"  -> An exception occurred during place search: {e}")

    return all_place_ids

def get_clinic_details(place_id, api_key):
    """
    Uses the Places API 'Place Details' to get specific info for one clinic.
    """
    details_url = "https://maps.googleapis.com/maps/api/place/details/json"
    fields = "name,formatted_address,international_phone_number,website,rating"
    params = {'place_id': place_id, 'fields': fields, 'key': api_key, 'language': 'es'}

    try:
        # Added a timeout to prevent the script from hanging here. THIS IS THE KEY FIX.
        res = requests.get(details_url, params=params, timeout=15) # <-- IMPROVEMENT
        results = res.json()
        
        if results['status'] == 'OK':
            return results['result']
        else:
            print(f"  -> API Error getting details for {place_id}: {results.get('status')} - {results.get('error_message', '')}")
            return None
            
    except requests.exceptions.Timeout:
        print(f"  -> Timed out getting details for {place_id}. Skipping.")
        return None
    except Exception as e:
        print(f"  -> An exception occurred during detail lookup for {place_id}: {e}")
        return None

def scrape_email_from_website(url):
    """
    Scrapes a single website to find email addresses.
    """
    if not url: return set()
    emails = set()
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        # This request already had a timeout, which is good.
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.content, 'html5lib')
        email_regex = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        found_emails = re.findall(email_regex, soup.get_text())
        for email in found_emails:
            if not email.endswith(('.png', '.jpg', '.gif', '.svg', '.webp')):
                emails.add(email.lower())
    except requests.exceptions.RequestException:
        pass
    except Exception:
        pass
    return emails

if __name__ == "__main__":
    # Check which postcodes have already been processed to avoid re-doing work
    processed_postcodes = set()
    if os.path.exists(CSV_FILENAME):
        try:
            df_existing = pd.read_csv(CSV_FILENAME)
            if 'Searched Postcode' in df_existing.columns:
                processed_postcodes = set(df_existing['Searched Postcode'].unique())
                print(f"Already processed {len(processed_postcodes)} postcodes. Resuming...")
        except pd.errors.EmptyDataError:
            print("CSV file is empty. Starting from the beginning.")
        except Exception as e:
            print(f"Could not read existing CSV file due to error: {e}. Starting from scratch.")

    for postcode in range(28001, 28081):
        if postcode in processed_postcodes:
            print(f"\nSkipping postcode {postcode} as it is already in the CSV file.")
            continue

        query = f"clínica dental Madrid {postcode}"
        print(f"\nSearching for: {query}")
        
        place_ids = find_dental_clinics(query, API_KEY)
        
        if not place_ids:
            print("  No clinics found for this postcode via API.")
            time.sleep(1)
            continue

        postcode_results = []
        for place_id in place_ids:
            details = get_clinic_details(place_id, API_KEY)
            
            if details:
                name = details.get('name', 'Not found')
                address = details.get('formatted_address', 'Not found')
                phone = details.get('international_phone_number', 'Not found')
                website = details.get('website', '')
                rating = details.get('rating', 'N/A')

                found_emails = scrape_email_from_website(website)
                emails_str = ", ".join(found_emails) if found_emails else "Not found"
                
                print(f"    - Name: {name} | Phone: {phone} | Email: {emails_str}")

                postcode_results.append({
                    'Name': name, 'Address': address, 'Phone Number': phone,
                    'Website': website if website else 'Not found', 'Rating': rating,
                    'Email': emails_str, 'Searched Postcode': postcode
                })
            time.sleep(0.1)

        if postcode_results:
            write_header = not os.path.exists(CSV_FILENAME) or os.path.getsize(CSV_FILENAME) == 0
            df = pd.DataFrame(postcode_results)
            df.to_csv(CSV_FILENAME, mode='a', index=False, header=write_header, encoding='utf-8-sig')
            print(f"  -> Saved {len(postcode_results)} results for postcode {postcode} to {CSV_FILENAME}")
        
        time.sleep(1)

    if os.path.exists(CSV_FILENAME):
        print(f"\nAll scraping finished. Creating final Excel file...")
        final_df = pd.read_csv(CSV_FILENAME)
        final_df.to_excel(EXCEL_FILENAME, index=False, engine='openpyxl')
        print(f"Data successfully saved to {EXCEL_FILENAME}")
    else:
        print("\nNo data was collected to save.")
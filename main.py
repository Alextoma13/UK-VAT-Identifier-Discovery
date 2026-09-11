import pandas as pd
import requests
import re
from bs4 import BeautifulSoup
from duckduckgo_search import DDGS
from thefuzz import fuzz
import time

# Regex flexibil pentru formatul UK VAT
VAT_REGEX = re.compile(r'\b(?:GB)?\s*(\d{3}\s*\d{4}\s*\d{2})\b')

def find_company_website(company_name):
    """Caută primul rezultat relevant pe motorul de căutare."""
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(f"{company_name} UK official website", max_results=1))
            if results:
                return results[0]['href']
    except Exception:
        pass
    return None

def scrape_for_vat(url):
    """Scanează paginile unde companiile sunt obligate legal să pună TVA-ul."""
    paths_to_check = ['', '/terms', '/contact', '/privacy', '/legal']
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    found_vats = set()
    
    for path in paths_to_check:
        try:
            target_url = url.rstrip('/') + path
            response = requests.get(target_url, headers=headers, timeout=5)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                text = soup.get_text(separator=' ')
                matches = VAT_REGEX.findall(text)
                for match in matches:
                    clean_vat = match.replace(" ", "")
                    found_vats.add(clean_vat)
        except Exception:
            continue
    return list(found_vats)

def verify_with_hmrc(vat_number, original_company_name):
    """Oracolul de verificare + logica de prevenire a coruperii datelor (False Positives)."""
    url = f"https://api.service.hmrc.gov.uk/organisations/vat/check-vat-number/lookup/{vat_number}"
    headers = {"Accept": "application/vnd.hmrc.1.0+json"}
    
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        hmrc_data = response.json()
        hmrc_name = hmrc_data.get('target', {}).get('name', '')
        
        # Scor de similaritate între numele oficial din Companies House și cel de la HMRC
        similarity = fuzz.token_set_ratio(original_company_name.lower(), hmrc_name.lower())
        
        # Pragul de 65 filtrează discrepanțele majore (ex: "J Smith Ltd" vs "Squarespace Inc")
        is_true_positive = similarity >= 65
        return {"valid": True, "hmrc_name": hmrc_name, "similarity": similarity, "is_tp": is_true_positive}
    return {"valid": False}

if __name__ == "__main__":
    print("Pipeline-ul de extracție și validare UK VAT este configurat.")
    # Pentru a rula efectiv pipeline-ul, utilizați un fișier CSV generat din Companies House.
    # Exemplu de apel: 
    # df = pd.read_csv('uk_companies_sample.csv')
    # pipeline_logic(df)

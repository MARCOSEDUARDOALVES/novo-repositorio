import requests
import json
import csv

API_ENDPOINT = "http://wishiy.com/page/api/today"

def collect_data(limit=100):
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    data = {'response': 'JSON', 'limit': limit}
    
    try:
        response = requests.post(API_ENDPOINT, headers=headers, data=data)
        response.raise_for_status()  # Raise an exception for HTTP errors
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Erro ao conectar à API: {e}")
        return None

def save_to_csv(data, filename="celebrity_data.csv"):
    if not data:
        print("Nenhum dado para salvar.")
        return

    # Extract headers from the first item, assuming all items have the same structure
    headers = list(data[0].keys())

    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=headers)
        writer.writeheader()
        writer.writerows(data)
    print(f"Dados salvos em {filename}")

if __name__ == "__main__":
    celebrity_data = collect_data(limit=100) # Collect up to 100 celebrities
    if celebrity_data:
        save_to_csv(celebrity_data)


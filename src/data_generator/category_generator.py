"""
Generating a CSV file with categories and their weights.
"""
from pathlib import Path
import random
import csv

def get_raw_categories() -> list:
    """
    Reads the raw categories from a text file and returns them as a list.
    """
    raw_category_path = Path(__file__).resolve().parent.parent.parent / 'raw' / 'categories_raw.txt'
    
    with open(raw_category_path, 'r', encoding='utf-8') as f:
        return [line.strip() for line in f]
    
def generate_category_weights(categories: list) -> list:
    """
    Generates normalized weights rounded to 4 decimals
    """
    random.seed(42)  # Fixed seed value for reproducibility
    weights = [random.expovariate(1) for _ in categories]
    total = sum(weights)
    normalized = [w/total for w in weights]
    
    # Round and adjust last element to ensure sum=1
    rounded = [round(w, 4) for w in normalized]
    rounded[-1] = round(1 - sum(rounded[:-1]), 4)
    return rounded

def generate_category_csv(categories: list, weights: list) -> None:
    """
    Generates a CSV file containing the category weights.
    """
    category_path = Path(__file__).resolve().parent.parent.parent / 'data' / 'categories.csv'
    
    with open(category_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['category', 'weight'])
        for category, weight in zip(categories, weights):
            writer.writerow([category, weight])



def main():
    categories = get_raw_categories()
    weights = generate_category_weights(categories)
    generate_category_csv(categories, weights)
    

if __name__ == '__main__':
    main()

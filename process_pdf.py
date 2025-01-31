import os
import re

from PyPDF2 import PdfReader
from dotenv import load_dotenv
from openai import OpenAI
#import openai


# Determine if the pdf is a financial report
def is_fiscal_year(pdf_path):
    try:
        reader = PdfReader(pdf_path)
        keywords = ['fy2', 'fiscal year']
        for page in reader.pages:
            page_text = page.extract_text()
            if any(keyword in page_text.lower() for keyword in keywords):
                return True
        return False
    except Exception as e:
        print(f"Error checking if the pdf is a financial report: {e}")
        return None


# Extract text from pdf
def extract_text_from_pdf(pdf_path):
    try:
        reader = PdfReader(pdf_path)
        text = ""
        for page in reader.pages:
            page_text = page.extract_text()
            # Only extract text if it contains 'scope 1' or 'scope 2' and '2024' or '2023'
            if ('scope 1' in page_text.lower() or 'scope 2' in page_text.lower()) and \
                  ('2024' in page_text.lower() or '2023' in page_text.lower()):
                text += page_text
        return text
    
    except Exception as e:
        print(f"Error processing PDF: {pdf_path}")
        print(f"Error message: {str(e)}")
        return None
'''
# Find the specific emissions data in text using ChatGPT
def find_data_in_text_chatgpt(company_name, pdf_text):
    # Input: emission related text
    # Output: emission data in natural language

    load_dotenv()
    openai.api_key = os.getenv('OPENAI_API')

    prompt = f"According to the given text, find the latest scope 1 and scope 2 emissions data of \"{company_name}\",  \
                and then give me the data in the one of following patterns: \n \
                ##Pattern 1: \n \
                Scope 1 (direct): 1,234 unit. \n \
                Scope 2 (location-based): 2,345 unit. \n \
                Scope 2 (martket-based): 3,456 unit. \n \
                ##Pattern 2: \n \
                Scope 1 and 2 (total): 1,234 unit. \n \
                ##Requirements: \n \
                1. Pay attention to the notes and comments about the accurately calculation method of Scope 2.\n \
                2. Pattern2 is used only the scope1 and scope2 are counted together. \n \
                3. Pay attention and try hard to find the unit of the data.\n \
                4. If the data is missing, or you not sure about the data, leave the part as \"N/A\". \n \
                5. No explanation need. \n \
                ---------------------------------- \n \
                {pdf_text}."

    # Call the OpenAI ChatGPT API to analyze the content and find emission data
    response = openai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system","content": "You are a professional analyst who can find scope 1 and scope 2 emissions data from a company's sustainability report."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.7
    )

    # Extract the answer text from the response
    answer = response.choices[0].message.content.strip()
    return answer
'''

# Find the specific emissions data in text using DeepSeek
def find_data_in_text_deepseek(company_name, pdf_text):
    try:
        load_dotenv()
        client = OpenAI(
            api_key=os.getenv('DEEPSEEK_API'), 
            base_url="https://api.deepseek.com"
        )

        prompt = f"According to the given text, find the latest scope 1 and scope 2 emissions data of \"{company_name}\",  \
                    and then give me the data in the one of following patterns.\n \
                    ##Pattern 1: \n \
                    Scope 1 (direct): 1,234 unit. \n \
                    Scope 2 (location-based): 2,345 unit. \n \
                    Scope 2 (martket-based): 3,456 unit. \n \
                    ##Pattern 2 (only used when scope1 and scope2 are counted together): \n \
                    Scope 1 and 2 (total): 1,234 unit. \n \
                    ##Requirements: \n \
                    1. Pay attention and try hard to find the unit of the data.\n \
                    2. Pay more attention in the latter part of the content, as they often contain more accurate and detailed data. \n \
                    3. Pay attention to the calculation method of Scope 2.\n \
                    4. If the data is missing or not sure, leave the part as \"N/A\". \n \
                    ---------------------------------- \n \
                    {pdf_text}."
        
        # Call the DeepSeek API with timeout
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "You are a professional analyst who can find scope 1 and scope 2 emissions data from a company's sustainability report."},
                {"role": "user", "content": prompt},
            ],
            stream=False
        )

        # Extract the answer text from the response
        answer = response.choices[0].message.content.strip()
        return answer

    except Exception as e:
        print(f"Error calling DeepSeek API for {company_name}: {e}")
        return "N/A"


# Convert data from sentence to number, including unit conversion
def data_formatting(text):

    # Sample input: "49,860.25 tons CO2e."   
    try:  
        split_text = text.replace(",", "").strip().split(" ", 1) # ['49860.25', 'tons CO2e.']
        value = float(split_text[0]) # 49860.25
        unit = split_text[1].lower().strip() # tons co2e.
        unit_capital = split_text[1].strip() # tons CO2e
    except:
        return "-"

    ### Default unit is metric ton / t / tonne ###
    # Short ton / ton
    if "short ton" in unit or ("ton" in unit and "metric" not in unit and "tonnes" not in unit): 
        value = round(value * 0.90718, 2) 
    # Long ton
    elif "long ton" in unit: 
        value = round(value * 1.01605, 2) 
    # Kilogram / kg
    elif "kilogram" in unit or "kg" in unit:
        value = value / 1000
        if abs(value) < 1: # If it is a small number, keep three significant digits
            # Find the position of the first non-zero digit
            str_num = f"{value:.10f}"
            first_nonzero = next(i for i, c in enumerate(str_num.replace("-", "").replace("0.", "")) if c != '0')
            value = round(value, first_nonzero + 3)
        else:
            value = round(value, 2) 

    # Thousand tonne / kt
    if "thousand" in unit or "kilo tonne" in unit or "kt" in unit:
        value = round(value * 1000, 2)
    # Million tonne / mmt (separate from Metric Tonne (MT))
    elif "million" in unit or "mmt" in unit:
        value = round(value * 1000000, 2)
    elif "billion" in unit or "gt" in unit:
        value = round(value * 1000000000, 2)
    

    # If it is an integer, remove the .0 after the decimal point
    if value.is_integer():
        return str(int(value))
    return str(value)


# Process one company's emissions data
def find_emissions_data(company_name, file_path, log_file_path):

    with open(log_file_path, 'a', encoding='utf-8') as log_file:
        log_file.write(f"\n=========={company_name}==========\n")

    pdf_text =extract_text_from_pdf(file_path)
    if pdf_text == None:
        return None

    data_in_text = find_data_in_text_deepseek(company_name, pdf_text)
    if data_in_text == None:
        return None
    with open(log_file_path, 'a', encoding='utf-8') as log_file:
        log_file.write(f"【data in sentance】\n{data_in_text}\n")

    # If the calculation method is "Scope 1 and 2 (total)"
    if "Scope 1 and 2 (total)" in data_in_text:
        scope_1_and_2 = re.search(r"Scope 1 and 2 \(total\):\s*([^\n]+)", data_in_text) # 49,860.25 tons CO2e.  
        scope_1_and_2_value = data_formatting(scope_1_and_2)
        with open(log_file_path, 'a', encoding='utf-8') as log_file:
            log_file.write(f"【data only】\n{scope_1_and_2_value}\n")
        return ("-", "-", "-", scope_1_and_2_value)
    
    # If the calculation method is "Scope 1" and "Scope 2"
    scope1 = re.search(r"Scope 1 \(direct\):\s*([^\n]+)", data_in_text)
    scope1_value = data_formatting(scope1)
    scope2_location = re.search(r"Scope 2 \(location-based\):\s*([^\n]+)", data_in_text)
    scope2_location_value = data_formatting(scope2_location)
    scope2_market = re.search(r"Scope 2 \(market-based\):\s*([^\n]+)", data_in_text)
    scope2_market_value = data_formatting(scope2_market)
    with open(log_file_path, 'a', encoding='utf-8') as log_file:
        log_file.write(f"【data only】\n{scope1_value}-{scope2_location_value}-{scope2_market_value}\n")
    return (scope1_value, scope2_location_value, scope2_market_value, "-")
    

if __name__ == "__main__":

    log_file_path = 'log_deepseek.txt'
    '''
    # Test single company
    company_name = "HEINEKEN HOLDING NV"
    file_path = f"./reports2/{company_name}.pdf"
    emissions_data = find_emissions_data(company_name, file_path, log_file_path)
    '''
    # Batch processing
    reports_dir = "./reports/test"
    pdf_files = [f for f in os.listdir(reports_dir) if f.endswith('.pdf')]
    for pdf_file in pdf_files:
        company_name = os.path.splitext(pdf_file)[0]
        file_path = os.path.join(reports_dir, pdf_file)
        emissions_data = find_emissions_data(company_name, file_path, log_file_path)
            
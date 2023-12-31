import streamlit as st
import pandas as pd
from playwright.sync_api import sync_playwright
import concurrent.futures
import time

CR = "https://cernyrytir.cz/index.php3?akce=3"
NG = "https://www.najada.games/mtg/singles/bulk-purchase"
BL = "https://www.blacklotus.cz/magic-kusove-karty/"

COLS = ("Name", "Set", "Type", "Rarity", "Language", "Condition", "Stock", "Price")
TITLE = "MTG Card Availability & Price Comparison"

def process_input_data(inputstring:str) -> list:
    return inputstring.strip().split('\n')

def process_dataframe_height(dataframe:pd.DataFrame) -> int:
    return int((len(dataframe) + 1) * 35 + 3)

def get_black_lotus_data(url:str, search_query:str) -> list:
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(url)
        page.type('input[name="string"]', search_query)
        page.press('input[name="string"]', 'Enter')
        page.wait_for_load_state('domcontentloaded')

        div_elements = page.query_selector_all('.products.products-block div')
        text_values = []
        for div_element in div_elements:
            text_values.append(div_element.inner_text())
        
        browser.close()

        filtered_data = [item.split('\n') for item in text_values if search_query.lower() in item.lower() and len(item.split('\n')) >= 4]

        unique_sublists = set()
        for sublist in filtered_data:
            unique_sublists.add(tuple(sublist))
        unique_sublists = [list(sublist) for sublist in unique_sublists]

        filtered_list = []
        for sublist in unique_sublists:
            filtered_sublist = [item for item in sublist if item and "DETAIL" not in item]
            while len(filtered_sublist) < 4:
                filtered_sublist.append('')
            
            edition_element = filtered_sublist[3]
            if " z edice " in edition_element:
                index = edition_element.find(' z edice ')
                if index != -1:
                    extracted_part = edition_element[index + len(' z edice '):]
                if extracted_part.endswith('.'):
                    extracted_part = extracted_part[:-1]
                filtered_sublist[3] = extracted_part
            
            qty_element = filtered_sublist[1]
            numeric_qty = ""
            if any(char.isdigit() for char in qty_element):
                for char in qty_element:
                    if char.isdigit():
                        numeric_qty += char
            if numeric_qty:
                filtered_sublist[1] = numeric_qty + " ks"
            else:
                filtered_sublist[1] = "0 ks"
            
            filtered_list.append(filtered_sublist)

        data = []

        for item in filtered_list:
            category_data = {
                COLS[0]: item[0],
                COLS[1]: item[3],
                COLS[2]: "",
                COLS[3]: "",
                COLS[4]: "",
                COLS[5]: "",
                COLS[6]: item[1],
                COLS[7]: item[2]}
            data.append(category_data)

        return data

def get_cerny_rytir_data(url:str, search_query:str) -> list:
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(url)
        page.type('input[name="jmenokarty"]', search_query)
        page.press('input[name="jmenokarty"]', 'Enter')
        page.wait_for_load_state('domcontentloaded')

        tbody_elements = page.locator('tbody').all()

        if len(tbody_elements) >= 7:
            tbody = tbody_elements[6]

            td_elements = tbody.locator('td').all()

            data = []
            current_lines = []

            for td in td_elements:
                line = td.inner_text().strip()
                line = line.replace('\xa0', ' ')
                if len(line) > 0:
                    current_lines.append(line)
                    if len(current_lines) == 6:
                        category_data = {
                            COLS[0]: current_lines[0],
                            COLS[1]: current_lines[1],
                            COLS[2]: current_lines[2],
                            COLS[3]: current_lines[3],
                            COLS[4]: "",
                            COLS[5]: "",
                            COLS[6]: current_lines[4],
                            COLS[7]: current_lines[5]}

                        data.append(category_data)
                        current_lines = []

        browser.close()
        return data

def get_najada_games_data(url: str, searchstring: str) -> list:
    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context()
        page = context.new_page()
        page.goto(url)

        page.wait_for_selector('textarea#cardData')
        page.fill('textarea#cardData', searchstring)
        page.click('div.my-5.Button.font-encodeCond.f-15.p-7-44.green')
        page.wait_for_selector('.BulkPurchaseResult', state='visible')

        loose_card_elements = page.query_selector_all('.BulkPurchaseResult .LooseCard')

        result_list = []
        headers = [COLS[5], COLS[6], COLS[7]]
        for element in loose_card_elements:
            card_info = {}
            card_info[COLS[0]] = element.evaluate('(element) => element.querySelector(".title.font-encodeCond").textContent')
            card_info[COLS[1]] = element.evaluate('(element) => element.querySelector(".expansionTitle.font-hind").textContent')
            card_info[COLS[3]] = element.evaluate('(element) => element.querySelector(".rarity.font-hind.text-right").textContent')
            card_info[COLS[4]] = (element.evaluate('(element) => element.querySelector(".name").textContent')).strip()

            details_text = (element.evaluate('(element) => element.querySelector(".TabSwitchVertical").textContent')).strip()
            details_list = [item.strip() for item in details_text.split('\n') if item.strip()]
            details_list = [item[-2:] if "Wantlist " in item else item for item in details_list]
            details_list = [item for item in details_list if '+' not in item and '-' not in item and "r." not in item]
            if len(details_list) >= 2:
                details_list = details_list[1:]

            sublists = [details_list[i:i + 3] for i in range(0, len(details_list), 3)]

            for sublist in sublists:
                for i, col_header in enumerate(headers):
                    card_info[col_header] = sublist[i]
                result_list.append(card_info.copy())

        browser.close()

        return result_list


st.set_page_config(page_title=TITLE, layout="wide", initial_sidebar_state="expanded")

with st.sidebar:
    st.subheader(TITLE)
    inpustring = st.text_area("Enter card names (one line per card)", height=600)
    checkstock = st.checkbox("Exclude 'Not In Stock'", value=True)
    searchbutton = st.button("Search")
    

col1, col2, col3 = st.columns(3)
col1.subheader("Najada Games")
col2.subheader("Černý rytíř")
col3.subheader("Blacklotus")

if searchbutton:
    bar = st.sidebar.progress(0, text="Obtaining Data...")
    start_time = time.time()
    inputlist = process_input_data(inpustring)

    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures_parallel = [executor.submit(get_cerny_rytir_data, CR, item) for item in inputlist]
        concurrent.futures.wait(futures_parallel)
        results_parallel = [future.result() for future in futures_parallel]

        futures_parallel2 = [executor.submit(get_black_lotus_data, BL, item) for item in inputlist]
        concurrent.futures.wait(futures_parallel2)
        results_parallel2 = [future.result() for future in futures_parallel2]

        future_once = executor.submit(get_najada_games_data, NG, inpustring)
        result_once = future_once.result()

    bar.progress(75, text="Processing Data...")
    elapsed_time = time.time() - start_time

    
    try:
        ng_df = pd.DataFrame(result_once)
        ng_df = ng_df.drop(columns=[COLS[4], COLS[5]])
        ng_df.insert(2, COLS[2], None)
        ng_df[COLS[7]] = ng_df[COLS[7]].astype(str).str.replace(r'CZK', 'Kč', regex=True)
        ng_df[COLS[7]] = ng_df[COLS[7]].replace("CZK", "Kč")
        ng_df[COLS[6]] = ng_df[COLS[6]].str.strip().replace("not in stock", "0")
        ng_df[COLS[6]] = ng_df[COLS[6]].astype(str).str.replace(r'\D', '', regex=True)
    except:
        ng_df = pd.DataFrame()

    try:
        cr_data = [item for sublist in results_parallel if sublist for item in sublist]
        cr_df = pd.DataFrame(cr_data)
        cr_df = cr_df.drop(columns=[COLS[4], COLS[5]])
        cr_df[COLS[6]] = cr_df[COLS[6]].astype(str).str.replace(r' ks', '', regex=True)
    except:
        cr_df = pd.DataFrame()
    
    try:
        bl_data = [item for sublist in results_parallel2 if sublist for item in sublist]
        bl_df = pd.DataFrame(bl_data)
        bl_df = bl_df.drop(columns=[COLS[4], COLS[5]])
        bl_df[COLS[6]] = bl_df[COLS[6]].astype(str).str.replace(r' ks', '', regex=True)
        bl_df[COLS[7]] = bl_df[COLS[7]].astype(str).str.replace(r'od ', '', regex=True)
    except:
        bl_df = pd.DataFrame()
    
    
    if checkstock:
        ng_df = ng_df[ng_df[COLS[6]] != "0"]
        cr_df = cr_df[cr_df[COLS[6]] != "0"]
        bl_df = bl_df[bl_df[COLS[6]] != "0"]
        
    col1.data_editor(ng_df, hide_index=True, disabled=True, use_container_width=True, height=process_dataframe_height(ng_df))
    col2.data_editor(cr_df, hide_index=True, disabled=True, use_container_width=True, height=process_dataframe_height(cr_df))
    col3.data_editor(bl_df, hide_index=True, disabled=True, use_container_width=True, height=process_dataframe_height(bl_df))


    st.sidebar.success("Processed in {:.1f} seconds".format(elapsed_time))
    bar.progress(100, text="Done!")
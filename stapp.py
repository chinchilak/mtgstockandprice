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

def process_input_data(inputstring: str) -> list:
    lines = inputstring.strip().split('\n')
    processed_lines = []
    for line in lines:
        index = next((i for i, char in enumerate(line) if not char.isdigit() and not char.isspace()), None)
        if index is not None:
            processed_lines.append(line[index:].strip())
        else:
            processed_lines.append(line.strip())
    return processed_lines

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
        page.wait_for_load_state("domcontentloaded")

        table_xpath = "/html/body/table/tbody/tr[2]/td[2]/table/tbody/tr/td/table/tbody"
        page.wait_for_selector(f"xpath={table_xpath}")

        table = page.locator(f"xpath={table_xpath}")
        rows = table.locator("tr").all()
        table_data = [
        [
            td.text_content().replace("\xa0", " ").strip()
            for td in row.locator("td").all()
            if td.text_content().replace("\xa0", " ").strip()
        ]
        for row in rows]

        merged_list = []
        for i in range(0, len(table_data), 3):
            sublist = table_data[i:i+3]
            merged_list.append([item for sublist in sublist for item in sublist])
        
        data = []
        for row_data in merged_list:
            if len(row_data) == 6:
                category_data = {
                    COLS[0]: row_data[0],
                    COLS[1]: row_data[1],
                    COLS[2]: row_data[2],
                    COLS[3]: row_data[3],
                    COLS[4]: "",
                    COLS[5]: "",
                    COLS[6]: row_data[4],
                    COLS[7]: row_data[5]}
                data.append(category_data)

        browser.close()
        return data

def get_najada_games_data(url: str, searchstring: str) -> list:
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            context = browser.new_context()
            page = context.new_page()
            page.goto(url)

            page.wait_for_selector('textarea#cardData')
            page.fill('textarea#cardData', searchstring)
            page.click('div.my-5.Button.font-encodeCond.f-15.p-7-44.green')
            page.wait_for_selector('.BulkPurchaseResult', state='visible')

            arrow_down_elements = page.query_selector_all('.icon.icon_arrow-down')
            for arrow_down_element in arrow_down_elements:
                arrow_down_element.click()

            loose_card_elements = page.query_selector_all('.BulkPurchaseResult .LooseCard')

            result_list = []
            result2_list = []
            for element in loose_card_elements:
                card_info = {}
                card_info[COLS[0]] = element.evaluate('(element) => element.querySelector(".title.font-encodeCond").textContent')
                card_info[COLS[1]] = element.evaluate('(element) => element.querySelector(".expansionTitle.font-hind").textContent')
                card_info[COLS[3]] = element.evaluate('(element) => element.querySelector(".rarity.font-hind.text-right").textContent')
                card_info[COLS[4]] = (element.evaluate('(element) => element.querySelector(".name").textContent')).strip()

                result_list.append(card_info)

                condition_elements = element.query_selector_all('.state')
                group_condition = [{COLS[5]: item.inner_text()} for item in condition_elements]

                stock_elements = element.query_selector_all('.col-3 .Status span.font-hind span')
                group_stock = [{COLS[6]: item.inner_text()} for item in stock_elements]
            
                price_elements = element.query_selector_all('.col-2 .NumberFormat.font-encodeCond.green')
                group_price = [{COLS[7]: item.inner_text().strip()} for item in price_elements]

                list_group = []

                for condition, stock, price in zip(group_condition, group_stock, group_price):
                    combined_dict = {}
                    combined_dict.update(condition)
                    combined_dict.update(stock)
                    combined_dict.update(price)
                    list_group.append(combined_dict)
                
                result2_list.append(list_group)

            browser.close()

            combined_list = []

            for dict1, sublist2 in zip(result_list, result2_list):
                combined_sublist = []
                for dict2 in sublist2:
                    combined_dict = dict1.copy()
                    combined_dict.update(dict2)
                    combined_sublist.append(combined_dict)

                combined_list.append(combined_sublist)
            
            flattened_list = [combined_dict for sublist in combined_list for combined_dict in sublist]
            print(flattened_list)

            return flattened_list
    except:
        return ["N/A"]


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
        ng_df = pd.DataFrame(columns=COLS)

    try:
        cr_data = [item for sublist in results_parallel if sublist for item in sublist]
        cr_df = pd.DataFrame(cr_data)
        cr_df = cr_df.drop(columns=[COLS[4], COLS[5]])
        cr_df[COLS[6]] = cr_df[COLS[6]].astype(str).str.replace(r' ks', '', regex=True)
    except:
        cr_df = pd.DataFrame(columns=COLS)
    
    try:
        bl_data = [item for sublist in results_parallel2 if sublist for item in sublist]
        bl_df = pd.DataFrame(bl_data)
        bl_df = bl_df.drop(columns=[COLS[4], COLS[5]])
        bl_df[COLS[6]] = bl_df[COLS[6]].astype(str).str.replace(r' ks', '', regex=True)
        bl_df[COLS[7]] = bl_df[COLS[7]].astype(str).str.replace(r'od ', '', regex=True)
    except:
        bl_df = pd.DataFrame(columns=COLS)
    
    
    if checkstock:
        ng_df = ng_df[ng_df[COLS[6]] != "0"]
        cr_df = cr_df[cr_df[COLS[6]] != "0"]
        bl_df = bl_df[bl_df[COLS[6]] != "0"]
        
    col1.data_editor(ng_df, hide_index=True, disabled=True, use_container_width=True, height=process_dataframe_height(ng_df), key="ngdata")
    col2.data_editor(cr_df, hide_index=True, disabled=True, use_container_width=True, height=process_dataframe_height(cr_df), key="crdata")
    col3.data_editor(bl_df, hide_index=True, disabled=True, use_container_width=True, height=process_dataframe_height(bl_df), key="bldata")


    st.sidebar.success("Processed in {:.1f} seconds".format(elapsed_time))
    bar.progress(100, text="Done!")
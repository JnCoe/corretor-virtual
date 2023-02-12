import logging
import pickle
import random
import re
import time
from datetime import datetime
from io import BytesIO

import pandas as pd
import pygsheets
import requests
import yaml
from PIL import Image
from selenium import webdriver
from tqdm.auto import tqdm

import credentials


class LogRecordListHandler(logging.Handler):
    def __init__(self, log_records):
        """This class will append all the logs (default set to INFO) into a list to later store it at another spreadsheet"""
        super().__init__()
        self.log_records = log_records

    def emit(self, record):
        self.log_records.append(record)


# Load config file
with open("config.yaml") as f:
    config = yaml.safe_load(f)

# create a list to store the logging records
log_records = []

# create a logger and set the log level to INFO
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# create a custom formatter and add it to the logger
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

# create a StreamHandler and set the log level to INFO
handler_stream = logging.StreamHandler()
handler = LogRecordListHandler(log_records)
handler.setLevel(logging.INFO)

# add the formatter to the handler
handler.setFormatter(formatter)

# add the handler to the logger
logger.addHandler(handler)
logger.addHandler(handler_stream)

logger.info("------------------------------------------------")
logger.info("New execution")

# Opening Selenium
option = webdriver.ChromeOptions()
option.add_argument(
    "--disable-blink-features=AutomationControlled"
)  # Hiding flag for identifying automation
option.add_argument(
    "--disable-notifications"
)  # Automatically deny notification requests
browser = webdriver.Chrome(options=option)

browser.get("https://www.google.com")  # Open any page just to load the cookies

time.sleep(1)

# Loading cookies to reduce risks of detection
cookies = pickle.load(open("cookies.pkl", "rb"))
for cookie in cookies:
    browser.add_cookie(cookie)

# Expanding window to avoid missing elements
browser.maximize_window()


# -- Functions to be used

# Extract numeric value from element
def extract_number(element, xpath) -> str:
    """This function will get a Selenium object and return just the number within it.

    Args:
        element (obj): Selenium object of the desired number (e.g.: footage)
        xpath (str): String containing the xpath of the element with the desired number

    Returns:
        str: number inside of the element as a string"""
    try:
        number = element.find_element_by_xpath(xpath).text
        number = re.sub("\D", "", number)

    except:
        number = ""

    return number


# Extract images
# Temporarily returning just first image
def extract_images_zap(srcs, id) -> str:
    """This function returns the first image of the gallery of images

    Args:
        srcs (list): List of strings containing the urls of the images
        id (str): String containing the id of the property [deprecated]

    Returns:
        str: String containing the url of the first image"""
    if srcs == []:
        return ""

    else:
        #! Collecting pictures is time-consuming and may lead to automation detection
        #! it also adds little value to the data. Hence, it was deactivated
        # headers = {
        #     "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.102 Safari/537.36"
        # }

        # images = [
        #     Image.open(BytesIO(requests.get(src, headers=headers).content))
        #     for src in srcs
        # ]
        # widths, heights = zip(*(i.size for i in images))

        # total_width = sum(widths)
        # max_height = max(heights)

        # new_im = Image.new("RGB", (total_width, max_height))

        # x_offset = 0
        # for im in images:
        #     new_im.paste(im, (x_offset, 0))
        #     x_offset += im.size[0]

        # new_im.save(f'data/images/{id}.jpg')

        # return new_im
        return f'=IMAGE("{srcs[0]}")'


def dados_card_zap(card) -> list:
    """ "This function returns all the information about the property

    Args:
        card (obj): Selenium object of the card containing the property

    Returns:
        list: List containing all the information about the property"""

    # Obtaining the ID of the property
    id = card.find_element_by_xpath("./ancestor::div[3]").get_attribute("data-id")
    # Storing URL using the ID
    url = f"https://www.zapimoveis.com.br/imovel/{id}"

    # Getting variables for the property
    metragem = extract_number(card, ".//span[@itemprop='floorSize']")
    quartos = extract_number(card, ".//span[@itemprop='numberOfRooms']")
    banheiros = extract_number(card, ".//span[@itemprop='numberOfBathroomsTotal']")
    vaga = extract_number(
        card, ".//li[@class='feature__item text-small js-parking-spaces']"
    )

    # Obtaining the address
    end = card.find_element_by_xpath(
        ".//h2[@class='simple-card__address color-dark text-regular']"
    ).text

    # Obtaining financial variables
    cond = extract_number(
        card, ".//li[@class='card-price__item condominium text-regular']"
    )
    iptu = extract_number(card, ".//li[@class='card-price__item iptu text-regular']")
    aluguel = extract_number(
        card,
        ".//p[@class='simple-card__price js-price color-darker heading-regular heading-regular__bolder align-left']",
    )

    # Some properties have a different layout for the rental price
    if aluguel == "":
        aluguel = extract_number(
            card,
            ".//p[@class='simple-card__price js-price color-primary heading-regular heading-regular__bolder align-left']",
        )

    # Obtaining list of images
    srcs = [
        img.get_attribute("src")
        for img in card.find_elements_by_xpath(
            "./ancestor::div[2]//div[@class='carousel oz-card-image__carousel']//img"
        )
    ]

    # Extracting images
    img = extract_images_zap(srcs, id)

    # Returning all the information
    return [id, url, end, metragem, quartos, banheiros, vaga, cond, iptu, aluguel, img]


# Actual scrapping
# Change the URL to the desired one
url = config["parameters"]["url"]
browser.get(url)
time.sleep(7)

# Obtaining total number of properties
total = extract_number(
    browser,
    "//h1[@class='summary__title js-summary-title heading-regular heading-regular__bold align-left text-margin-zero results__title']",
)

logger.info(f"Total de imóveis: {total}")

# Extracting all the results from the page
resultados = browser.find_elements_by_xpath("//div[@class='simple-card__box']")

# Start counting
loop = 1
novos_imoveis = 0

next_page = None

# Loop through pages
while next_page != "":

    logger.info(f"Obtendo informações sobre a página {loop}")

    time.sleep(random.randint(6, 12))
    resultados = browser.find_elements_by_xpath("//div[@class='simple-card__box']")

    dados = []

    # Run dados_card_zap for each element in resultados and append the result to dados
    for card in tqdm(resultados, desc=f"Obtendo dados dos imóveis - Página {loop}"):
        dados.append(dados_card_zap(card))

    # convert dados into a DataFrame
    df = pd.DataFrame(
        dados,
        columns=[
            "id",
            "url",
            "end",
            "metragem",
            "quartos",
            "banheiros",
            "vaga",
            "cond",
            "iptu",
            "aluguel",
            "img",
        ],
    )

    # Convert all columns except id, url, end, img to numeric
    for col in df.columns[3:-1]:
        df[col] = pd.to_numeric(df[col])

    df["end_completo"] = ""

    # Add column 'preco_metro_quadrado' to df
    df["preco_metro_quadrado"] = round(df["aluguel"] / df["metragem"], 2)

    # Add column 'total' to df
    df["total"] = df["aluguel"] + df["cond"] + df["iptu"]

    # Add column 'id_geral' after column 'id' that is just id+'zap'
    df.insert(1, "id_geral", "zap_" + df["id"])

    # Add column 'site' at the end that is just 'zap'
    df["site"] = "zap"

    # Add column 'status' that is empty
    df["status"] = ""

    df["comentarios"] = ""

    # Open Gsheet to get records
    gs = pygsheets.authorize(service_file="gsheet_credential.json")
    gsheets_main_key = config["credentials"]["gsheets_main_key"]
    wb_main = gs.open_by_key(gsheets_main_key)
    main = pd.DataFrame(wb_main[0].get_all_records())
    # wb_main[0].clear()
    # wb_main[0].set_dataframe(df, (1, 1))

    # Drop all rows that already are on the Gsheet (redundancy)
    df = df[~df["id_geral"].isin(main["id_geral"])]

    # round all numbers to 0 decimal places
    df = (
        df.round(0)
        .astype(str)
        .replace("\.0", "", regex=True)
        .replace("nan", "", regex=True)
    )

    # Add column data_adicionado with current timestamp
    df["data_adicionado"] = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

    # Append df to wb_main[0], ignoring the header
    if len(df) != 0:
        wb_main[0].set_dataframe(df, (len(main) + 2, 1), copy_head=False, fit=True)
    try:
        # Roll to the end of page
        browser.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(1)
        next_page = browser.find_element_by_xpath(
            "//button[@aria-label='Próxima Página']"
        )
        next_page.click()

    # If next page button is not found, break the loop
    except:
        logger.info("Próxima página não encontrada")
        next_page = ""

    novos_imoveis += len(df)

    # Save df id column into list
    ids = df["id"].tolist()

    logger.info(f"Página {loop} varrida - {len(df)} novos imóveis encontrados: {ids}")
    loop += 1

logger.info(f"Execução completa com {loop} páginas")
logger.info(f">>>>> Total de novos imóveis: {novos_imoveis}")

data_log = [
    {
        "asctime": datetime.fromtimestamp(record.created).strftime("%Y-%m-%d %H:%M:%S"),
        "name": record.name,
        "levelname": record.levelname,
        "message": record.msg,
    }
    for record in log_records
]

# Saving results to Gsheet
df_log = df = pd.DataFrame.from_records(data_log)
main_log = pd.DataFrame(wb_main[1].get_all_records())
wb_main[1].set_dataframe(df_log, (len(main_log) + 2, 1), copy_head=False, fit=True)

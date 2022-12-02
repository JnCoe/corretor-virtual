import logging
import pickle
import re
import time
from datetime import datetime
from io import BytesIO

import pandas as pd
import pygsheets
import requests
from PIL import Image
from selenium import webdriver
from tqdm.auto import tqdm

import credentials

option = webdriver.ChromeOptions()
option.add_argument("--disable-blink-features=AutomationControlled")
option.add_argument("--disable-notifications")
browser = webdriver.Chrome(options=option)

browser.get("https://www.google.com")

time.sleep(1)
cookies = pickle.load(open("cookies.pkl", "rb"))
for cookie in cookies:
    browser.add_cookie(cookie)

browser.maximize_window()


def extract_number(element, xpath) -> str:
    try:
        number = element.find_element_by_xpath(xpath).text
        number = re.sub("\D", "", number)

    except:
        number = ""

    return number


def extract_images_zap(srcs, id) -> str:
    if srcs == []:
        return ""
    else:
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.102 Safari/537.36"
        }

        images = [
            Image.open(BytesIO(requests.get(src, headers=headers).content))
            for src in srcs
        ]
        widths, heights = zip(*(i.size for i in images))

        total_width = sum(widths)
        max_height = max(heights)

        new_im = Image.new("RGB", (total_width, max_height))

        x_offset = 0
        for im in images:
            new_im.paste(im, (x_offset, 0))
            x_offset += im.size[0]

        # new_im.save(f'data/images/{id}.jpg')

        # return new_im  ##### ENQUANTO NAO RESOLVO
        return f'=IMAGE("{srcs[0]}")'


def dados_card_zap(card):
    id = card.find_element_by_xpath("./ancestor::div[3]").get_attribute("data-id")
    url = f"https://www.zapimoveis.com.br/imovel/{id}"

    metragem = extract_number(card, ".//span[@itemprop='floorSize']")
    quartos = extract_number(card, ".//span[@itemprop='numberOfRooms']")
    banheiros = extract_number(card, ".//span[@itemprop='numberOfBathroomsTotal']")
    vaga = extract_number(
        card, ".//li[@class='feature__item text-small js-parking-spaces']"
    )

    end = card.find_element_by_xpath(
        ".//h2[@class='simple-card__address color-dark text-regular']"
    ).text

    cond = extract_number(
        card, ".//li[@class='card-price__item condominium text-regular']"
    )
    iptu = extract_number(card, ".//li[@class='card-price__item iptu text-regular']")
    aluguel = extract_number(
        card,
        ".//p[@class='simple-card__price js-price color-darker heading-regular heading-regular__bolder align-left']",
    )
    if aluguel == "":
        aluguel = extract_number(
            card,
            ".//p[@class='simple-card__price js-price color-primary heading-regular heading-regular__bolder align-left']",
        )

    srcs = [
        img.get_attribute("src")
        for img in card.find_elements_by_xpath(
            "./ancestor::div[2]//div[@class='carousel oz-card-image__carousel']//img"
        )
    ]

    img = extract_images_zap(srcs, id)

    return [id, url, end, metragem, quartos, banheiros, vaga, cond, iptu, aluguel, img]


url = "https://www.zapimoveis.com.br/aluguel/apartamentos/rj+rio-de-janeiro+zona-sul+flamengo/?onde=,Rio%20de%20Janeiro,Rio%20de%20Janeiro,Zona%20Sul,Flamengo,,,neighborhood,BR%3ERio%20de%20Janeiro%3ENULL%3ERio%20de%20Janeiro%3EZona%20Sul%3EFlamengo,-22.936822,-43.175702,%3B,Rio%20de%20Janeiro,Rio%20de%20Janeiro,Zona%20Sul,Botafogo,,,neighborhood,BR%3ERio%20de%20Janeiro%3ENULL%3ERio%20de%20Janeiro%3EZona%20Sul%3EBotafogo,-22.951193,-43.180784,&transacao=Aluguel&tipo=Im%C3%B3vel%20usado&tipoUnidade=Residencial,Apartamento&precoTotalMaximo=4000&precoTotalMinimo=2000&pagina=1&ordem=Mais%20recente"
browser.get(url)
time.sleep(7)

total = extract_number(
    browser,
    "//h1[@class='summary__title js-summary-title heading-regular heading-regular__bold align-left text-margin-zero results__title']",
)

resultados = browser.find_elements_by_xpath("//div[@class='simple-card__box']")

dados = []

loop = 1

next_page = None

while next_page != "":

    if loop > 1:
        browser.find_element_by_xpath("//button[@aria-label='Próxima Página']").click()

    time.sleep(6)
    resultados = browser.find_elements_by_xpath("//div[@class='simple-card__box']")

    dados = []

    # Run dados_card_zap for each element in resultados and append the result to dados
    for card in tqdm(resultados):
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

    logging.warning("Obtaining current table from gsheets")
    gs = pygsheets.authorize(service_file="gsheet_credential.json")
    wb_main = gs.open_by_key(credentials.gsheets_main_key)
    main = pd.DataFrame(wb_main[0].get_all_records())
    # wb_main[0].clear()
    # wb_main[0].set_dataframe(df, (1, 1))

    # Drop all rows where 'id_geral' is in main['id_geral']
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

    logging.info(f"Sending {len(df)} new rows to gsheets")
    # Append df to wb_main[0], ignoring the header
    if len(df) != 0:
        wb_main[0].set_dataframe(df, (len(main) + 1, 1), copy_head=False, fit=True)
    try:
        # Roll to the end of page
        browser.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        next_page = browser.find_element_by_xpath(
            "//button[@aria-label='Próxima Página']"
        )
    except:
        next_page = ""

    loop += 1

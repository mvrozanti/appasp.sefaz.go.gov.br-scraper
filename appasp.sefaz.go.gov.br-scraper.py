#!/usr/bin/env python
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
import argparse
import atexit
import code
import psutil
import re
import signal
import sys

BASE_URL = 'http://appasp.sefaz.go.gov.br/'

def exit_gracefully(driver):
    # DB.close()
    driver.close()
    try: 
        for proc in psutil.process_iter():
            if proc.name() == 'firefox': proc.kill()
    except Exception as e: print(e)
    finally: sys.exit(0)

class CNPJScraper:

    def __init__(self, relative_url, headful):
        opts = Options()
        opts.headless = not headful
        self.driver = webdriver.Firefox(options=opts)
        self.url = BASE_URL + relative_url
        # atexit.register(exit_gracefully, driver)
        # signal.signal(signal.SIGINT, lambda x,y: exit_gracefully(driver))
        # self.driver.set_window_size(1024, 768)

    def get_single(self, cnpj_alvo):
        d = self.driver
        d.get(self.url)
        d.find_element_by_id('rTipoDocCNPJ').click()
        cnpj_field = d.find_element_by_id('tCNPJ')
        cnpj_field.send_keys(cnpj_alvo)
        cnpj_field.send_keys(Keys.RETURN)
        d.switch_to.window(d.window_handles[1])
        WebDriverWait(d, 10).until(EC.text_to_be_present_in_element((By.TAG_NAME, 'tbody'), 'CADASTRO ATUALIZADO EM'))
        relevant_elements = d.find_elements_by_class_name('label_text')
        cnpj_extraido = relevant_elements[0].text
        inscricao_estadual_cce = relevant_elements[1].text
        nome_empresarial = relevant_elements[2].text
        indicador_contribuinte = relevant_elements[3].text
        atividade_principal = relevant_elements[15].text
        situacao_cadastral_vigente = relevant_elements[19].text
        data_desta_situacao_cadastral = relevant_elements[20].text[::-1].replace('/', '-')
        data_de_cadastramento = relevant_elements[21].text[::-1].replace('/', '-')
        if cnpj_alvo != re.sub(r'[^\d+]', '', cnpj_extraido):
            print('deu ruim')
            sys.exit(1)
        return [cnpj_extraido, inscricao_estadual_cce, nome_empresarial, indicador_contribuinte, atividade_principal, situacao_cadastral_vigente, data_desta_situacao_cadastral, data_de_cadastramento]

def is_valid_cnpj(cnpj):
    return re.match(r'\d{14}', cnpj)

def get_cnpj(cnpj):
    if not is_valid_cnpj(cnpj):
        print(f'CNPJ "{cnpj}" é inválido.', file=sys.stderr)
        sys.exit(1)

def main(args):
    cnpj_alvo = '53654877000162'
    scraper = CNPJScraper(args.url, args.headful)
    cnpjs_alvo = open(args.input).readlines()
    kek = scraper.get_single(cnpj_alvo)
    code.interact(local=globals().update(locals()) or globals())

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='scraper de informações de CNPJ via appasp.sefaz.go.gov.br')
    parser.add_argument('-H', '--headful', action='store_true', default=False, 
            help='Torna o browser visível (desligado por default)')
    parser.add_argument('-U', '--url', default='Sintegra/Consulta/default.asp?', 
            help='Especifica a URL relativa para a consulta do site') # caso o site atualize e seja necessário alterá-la "por fora" do script
    parser.add_argument('-i', '--input', default='cnpj.csv', 
            help='Especifica o caminho do arquivo que contém os CNPJs (1 por linha) a serem consultados')
    main(parser.parse_args())

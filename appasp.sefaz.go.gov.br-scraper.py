#!/usr/bin/env python
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from datetime import datetime
import argparse
import atexit
import code
import csv
import psutil
import re
import signal
import sys
import os.path as op

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

    def get_single(self, cnpj_alvo, timeout):
        if not re.match(r'\d{14}', cnpj_alvo):
            print(f'CNPJ "{cnpj_alvo}" é inválido.', file=sys.stderr)
            sys.exit(1)
        d = self.driver
        d.switch_to.window(d.window_handles[0])
        d.get(self.url)

        d.find_element_by_xpath('/html/body/form/div/div[2]/input[2]').click()
        d.find_element_by_id('rTipoDocCNPJ').click()
        cnpj_field = d.find_element_by_id('tCNPJ')
        cnpj_field.clear()
        cnpj_field.send_keys(cnpj_alvo)
        cnpj_field.send_keys(Keys.RETURN)
        d.switch_to.window(d.window_handles[1])
        try:
            WebDriverWait(d, 5).until(EC.presence_of_element_located((By.TAG_NAME, 'tbody')))
        except Exception as e: 
            print(e)
            print('nao achou tbody')
            code.interact(local=globals().update(locals()) or globals())
        tbody_element = d.find_element_by_tag_name('tbody')
        WebDriverWait(d, 5).until(lambda d: 
                EC.text_to_be_present_in_element((By.TAG_NAME, 'tbody'), 'CADASTRO ATUALIZADO EM')
                or
                EC.text_to_be_present_in_element((By.TAG_NAME, 'tbody'), 'foi encontrado nenhum')
                )
        if 'foi encontrado nenhum' in d.find_element_by_tag_name('tbody').text:
            d.close()
            return ['NULL']*8
        regex_fluxo_principal = re.compile(r'CNPJ:\n(\d{2}\.\d{3}\.\d{3}\/\d{4}-\d{2}).*INSCRIÇÃO ESTADUAL - CCE :\n(.*)\n.*NOME EMPRESARIAL:\n(.*)\n.*CONTRIBUINTE\?\n*(.*)\n(?:\n|.)*\n(?:\n|.)+ATIVIDADE PRINCIPAL\n(.*)(?:\n|.)+SITUAÇÃO CADASTRAL VIGENTE:\n(.*)\n.*DATA DESTA SITUAÇÃO CADASTRAL:\n([^\s]+).*DATA DE CADASTRAMENTO:\n(.*)', re.MULTILINE)
        try:
            body_element = d.find_element_by_tag_name('body')
            m = next(filter(lambda match: match, regex_fluxo_principal.finditer(body_element.text)))
            normalize_date = lambda date_str: datetime.strptime(date_str, '%d/%m/%Y').strftime('%Y-%m-%d')
            info = [i.strip() for i in m.groups()]
            info[-1] = normalize_date(info[-1])
            info[-2] = normalize_date(info[-2])
            if cnpj_alvo != re.sub(r'[^\d+]', '', info[0]):
                print('Formato do site foi alterado. Favor reportar este incidente.')
                sys.exit(1)
            d.close()
            return info
        except Exception as e: 
            if 'existe mais de uma Inscrição Estadual para o par' in body_element.text:
                regex_fluxo_multiplas_inscricoes_estaduais = re.compile(r'abaixo relacionadas\.\n\n((?:\d+\n)+)')
                m = next(regex_fluxo_multiplas_inscricoes_estaduais.finditer(body_element.text))
                cnpjs_raiz_alvo = [cnpj for cnpj in m.group(1).split('\n') if cnpj]
                code.interact(local=globals().update(locals()) or globals())
                return [self.get_single(cra + cnpj_alvo[-5:], timeout) for cra in cnpjs_raiz_alvo]
            else:
                print(e)
                code.interact(local=globals().update(locals()) or globals())
            return ['NULL']*8

def main(args):
    if op.exists(args.output) and not args.force:
        print(f'Arquivo "{args.output}" já existe. Use a opção --force para sobrescrevê-lo.', file=sys.stderr)
        sys.exit(2) 
    scraper = CNPJScraper(args.url, args.headful)
    if not op.exists(args.input):
        print(f'Arquivo de input "{args.input}" não existe.', file=sys.stderr)
        sys.exit(3)
    cnpjs_alvo = [ca.rstrip() for ca in open(args.input).readlines()]
    with open(args.output, 'w') as of:
        output_writer = csv.writer(of, delimiter=',', dialect='excel', quoting=csv.QUOTE_MINIMAL)
        for cnpj_alvo in cnpjs_alvo:
            if args.verbose:
                print(f'Tentando {cnpj_alvo}:')
            cnpj_info = scraper.get_single(cnpj_alvo, args.timeout)
            if args.verbose:
                print(cnpj_info)
            if cnpj_info:
                if type(cnpj_info[0]) == list:
                    output_writer.writerows(cnpj_info)
                else:
                    output_writer.writerow(cnpj_info)
                of.flush()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='scraper de informações de CNPJ via appasp.sefaz.go.gov.br')
    parser.add_argument('-H', '--headful', action='store_true', default=False, 
            help='Torna o browser visível (desligado por default)')
    parser.add_argument('-U', '--url', default='Sintegra/Consulta/default.asp?', 
            help='Especifica a URL relativa para a consulta do site.\n' +
            'Caso não seja especificada, será "Sintegra/Consulta/default.asp?"') # caso o site atualize e seja necessário alterá-la "por fora" do script
    parser.add_argument('-i', '--input', default='cnpj.csv', 
            help='Especifica o caminho do arquivo que contém os CNPJs (1 por linha, apenas dígitos) a serem consultados')
    parser.add_argument('-o', '--output', default='sefaz_go.csv', 
            help='Especifica o caminho do arquivo csv de output')
    parser.add_argument('-f', '--force', action='store_true', default=False, 
            help='Sobrescrever um arquivo de output pré-existente')
    parser.add_argument('-t', '--timeout', metavar='TIMEOUT', type=int,
            help='Especifica o timeout do bot em milissegundos')
    parser.add_argument('-v', '--verbose', action='store_true', 
            help='Mostrar mensagens de debug')
    main(parser.parse_args())

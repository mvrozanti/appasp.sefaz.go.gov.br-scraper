#!/usr/bin/env python
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
import argparse
import csv
import os.path as op
import re
import sys

BASE_URL = 'http://appasp.sefaz.go.gov.br/'
DEFAULT_RELATIVE_URL = 'Sintegra/Consulta/default.asp?'

def site_format_error(reason):
    print(f'Formato do site foi alterado, em função do campo "{reason}". Favor reportar este incidente.', file=sys.stderr)
    sys.exit(1)

def format_cnpj(cnpj):
    return f'{cnpj[:2]}.{cnpj[2:5]}.{cnpj[5:8]}/{cnpj[8:12]}-{cnpj[12:]}'

class CNPJScraper:

    def __init__(self, relative_url, headful):
        opts = Options()
        opts.headless = not headful
        self.driver = webdriver.Firefox(options=opts)
        self.url = BASE_URL + relative_url

    def reset(self):
        """
        volta à página de pesquisa e fecha todas as outras abas
        """
        d = self.driver
        d.switch_to.window(d.window_handles[0])
        d.get(self.url)
        for wh in d.window_handles[1:]:
            d.switch_to.window(wh)
            d.close()
        d.switch_to.window(d.window_handles[0])

    def get_single(self, cnpj_alvo, timeout):
        """
        Extrai o cnpj_alvo da página aberta após consultá-lo, caso seja especificado.
        Caso não seja especificado, procura inscrições-raiz na página atual e as extrai coletivamente.
        """

        # inicializar variáveis de auxílio
        d = self.driver
        normalize_cnpj = lambda cnpj: re.sub(r'[^\d+]', '', cnpj)
        normalize_date = lambda date_str: datetime.strptime(date_str, '%d/%m/%Y').strftime('%Y-%m-%d')

        if cnpj_alvo:
            if not re.match(r'\d{14}', cnpj_alvo):
                print(f'CNPJ "{cnpj_alvo}" é inválido.', file=sys.stderr)
                sys.exit(1)
            d.find_element_by_xpath('/html/body/form/div/div[2]/input[2]').click()
            d.find_element_by_id('rTipoDocCNPJ').click()
            cnpj_field = d.find_element_by_id('tCNPJ')
            cnpj_field.clear()
            cnpj_field.send_keys(cnpj_alvo)
            cnpj_field.send_keys(Keys.RETURN)
        d.switch_to.window(d.window_handles[-1])
        try:
            WebDriverWait(d, timeout).until(EC.presence_of_element_located((By.TAG_NAME, 'tbody')))
        except Exception as e: 
            print(e, file=sys.stderr)
            site_format_error('tbody não ter sido encontrado')
        tbody_element = d.find_element_by_tag_name('tbody')
        WebDriverWait(d, timeout).until(lambda d: 
                EC.text_to_be_present_in_element(tbody_element, 'CADASTRO ATUALIZADO EM')
                or
                EC.text_to_be_present_in_element(tbody_element, 'foi encontrado nenhum')
                )
        if 'foi encontrado nenhum' in tbody_element.text:
            return [format_cnpj(cnpj_alvo)]+['NULL']*7
        regex_fluxo_principal = re.compile(r'CNPJ:\n(\d{2}\.\d{3}\.\d{3}\/\d{4}-\d{2}).*' +
                r'INSCRIÇÃO ESTADUAL - CCE :\n(.*)\n.*' +
                r'NOME EMPRESARIAL:\n(.*)\n.*' +
                r'CONTRIBUINTE\?\n*(.*)\n(?:\n|.)*\n(?:\n|.)+' +
                r'ATIVIDADE PRINCIPAL\n(.*)(?:\n|.)+' +
                r'SITUAÇÃO CADASTRAL VIGENTE:\n(.*)\n.*' +
                r'DATA DESTA SITUAÇÃO CADASTRAL:\n([^\s]+).*' +
                r'DATA DE CADASTRAMENTO:\n(.*)', re.MULTILINE)
        try:
            body_element = d.find_element_by_tag_name('body')
            m = next(filter(lambda match: match, regex_fluxo_principal.finditer(body_element.text)))
            info = [i.strip() for i in m.groups()]
            try:
                info[-1] = normalize_date(info[-1])
            except Exception as e: 
                site_format_error(f'DATA DESTA SITUAÇÃO CADASTRAL para o cnpj={cnpj_alvo}')
            try:
                info[-2] = normalize_date(info[-2])
            except Exception as e: 
                site_format_error(f'DATA DE CADASTRAMENTO para o cnpj={cnpj_alvo}')
            if not cnpj_alvo:
                d.close()
            elif cnpj_alvo != normalize_cnpj(info[0]):
                site_format_error(f'CNPJ para o cnpj={cnpj_alvo}')
            return info
        except StopIteration as e: 
            if 'existe mais de uma Inscrição Estadual para o par' in body_element.text:
                regex_fluxo_multiplas_inscricoes_estaduais = re.compile(r'abaixo relacionadas\.\n\n((?:\d+\n)+)')
                m = next(regex_fluxo_multiplas_inscricoes_estaduais.finditer(body_element.text))
                cnpjs_raiz_alvo = [cnpj for cnpj in m.group(1).split('\n') if cnpj]
                mult = []
                wh = self.driver.current_window_handle
                for cnpj_raiz_alvo in cnpjs_raiz_alvo:
                    d.switch_to.window(wh)
                    d.execute_script(f"fSend('{cnpj_raiz_alvo}')")
                    mult += [self.get_single(None, timeout)]
                return mult
            else:
                print(e)
                site_format_error('regex errado')
            return [format_cnpj(cnpj_alvo)]+['NULL']*7

def main(args):
    if op.exists(args.output) and not args.force:
        print(f'Arquivo "{args.output}" já existe. Use a opção --force para sobrescrevê-lo.', file=sys.stderr)
        sys.exit(2) 
    if not op.exists(args.input):
        print(f'Arquivo de input "{args.input}" não existe.', file=sys.stderr)
        sys.exit(3)
    scraper = CNPJScraper(args.url, args.headful)
    cnpjs_alvo = [ca.rstrip() for ca in open(args.input).readlines()]
    with open(args.output, 'w') as of:
        output_writer = csv.writer(of, delimiter=',', dialect='excel', quoting=csv.QUOTE_MINIMAL)
        for cnpj_alvo in cnpjs_alvo:
            scraper.reset()
            if args.verbose:
                print(f'Tentando {cnpj_alvo}:')
            cnpj_info = scraper.get_single(cnpj_alvo, args.timeout)
            if args.verbose:
                print(cnpj_info)
            if cnpj_info:
                if type(cnpj_info[0]) == list: # caso das múltiplas inscrições
                    output_writer.writerows(cnpj_info)
                else:
                    output_writer.writerow(cnpj_info)
                of.flush()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='scraper de informações de CNPJ via appasp.sefaz.go.gov.br')
    parser.add_argument('-H', '--headful', action='store_true', default=False, 
            help='Torna o browser visível (desligado por default)')
    parser.add_argument('-U', '--url', default=DEFAULT_RELATIVE_URL, 
            help='Especifica a URL relativa para a consulta do site.\n' +
            f'Caso não seja especificada, será "{DEFAULT_RELATIVE_URL}"') # caso o site atualize e seja necessário alterá-la "por fora" do script
    parser.add_argument('-i', '--input', default='cnpj.csv', 
            help='Especifica o caminho do arquivo que contém os CNPJs (1 por linha, apenas dígitos) a serem consultados')
    parser.add_argument('-o', '--output', default='sefaz_go.csv', 
            help='Especifica o caminho do arquivo csv de output')
    parser.add_argument('-f', '--force', action='store_true', default=False, 
            help='Sobrescrever um arquivo de output pré-existente')
    parser.add_argument('-t', '--timeout', metavar='TIMEOUT', type=int, default=5,
            help='Especifica o timeout do bot em segundos')
    parser.add_argument('-v', '--verbose', action='store_true', 
            help='Mostrar mensagens de debug')
    main(parser.parse_args())
#

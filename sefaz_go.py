#!/usr/bin/env python
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
import signal
import atexit
import code
import sys
import psutil

URL = 'http://appasp.sefaz.go.gov.br/Sintegra/Consulta/default.asp?'

def exit_gracefully(driver):
    # DB.close()
    driver.close()
    try: 
        for proc in psutil.process_iter():
            if proc.name() == 'firefox': proc.kill()
    except Exception as e: print(e)
    finally: sys.exit(0)

def load_csv():
    return open('cnpj.csv').readlines()

def main(args):
    opts = Options()
    opts.headless = False

    dcap = dict(DesiredCapabilities.PHANTOMJS)
    dcap["phantomjs.page.settings.userAgent"] = ('Mozilla/5.0 (X11; CrOS armv7l 9592.96.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.114 Safari/537.36') 
    dcap["pageLoadStrategy"] = "normal"  # complete

    # fp = webdriver.FirefoxProfile()

    driver = webdriver.Firefox(options=opts)
    # atexit.register(exit_gracefully, driver)
    # signal.signal(signal.SIGINT, lambda x,y: exit_gracefully(driver))
    driver.set_window_size(1024, 768)

    driver.get(URL)
    driver.find_element_by_id('rTipoDocCNPJ').click()
    cnpj_field = driver.find_element_by_id('tCNPJ')
    cnpj_field.send_keys('53654877000162')
    cnpj_field.send_keys(Keys.RETURN)
    driver.switch_to.window(driver.window_handles[1])
    WebDriverWait(driver, 10).until(EC.text_to_be_present_in_element((By.TAG_NAME, "tbody"), "CADASTRO ATUALIZADO EM"))
    code.interact(local=globals().update(locals()) or globals())
    # results = browser.find_elements_by_class_name('')
    driver.quit()

if __name__ == '__main__':
    main(None)

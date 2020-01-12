#!/usr/bin/env python 
from time import time
import subprocess
import pickle
import os
import os.path as op
import sys
import code
import argparse
import atexit

def main(args):
    record_file = 'record.txt'
    try:
        record = float(open(record_file).read()) if op.exists(record_file) else -1
    except ValueError as e: 
        print(f'Arquivo {record_file} inválido, desconsiderando', file=sys.stderr)
        record = -1
    atexit.register(lambda: os.remove(args.test_output_file))
    s = time()
    result = subprocess.Popen(f'./appasp.sefaz.go.gov.br-scraper.py -o {args.test_output_file}'.split())
    result.communicate()[0]
    exit_code = result.returncode
    if exit_code != 0:
        print('Erro de execução', file=sys.stderr)
        sys.exit(exit_code)
    e = time()
    t = e - s
    if record != -1:
        if record < t:
            print(f'Há uma piora de {t - record}ms de performance', file=sys.stderr)
            sys.exit(1)
        else:
            print(f'Há uma melhora de {record - t}ms de performance')
    else:
        print(f'Primeira execução durou {t}ms')
    open(record_file, 'w').write(str(t))

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='backtester de performance para script appasp.sefaz.go.gov.br-scraper.py')
    parser.add_argument('-r', '--record-file', default='record.txt',
            help='caminho do arquivo de record (default: .test.csv)')
    parser.add_argument('-t', '--test-output-file', default='.test.vsv', 
            help='arquivo de output do teste')
    main(parser.parse_args())

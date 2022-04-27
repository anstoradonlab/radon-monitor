from pycampbellcr1000 import CR1000

cr1000 = CR1000.from_url('serial://dev/ttyUSB0:115200', timeout=2)

logger_info = cr1000.getprogstat()

print(logger_info)

fname = str(logger_info['ProgName'], 'utf-8')

print(fname)
print('='*len(fname))
print()

print(str(cr1000.getfile(fname), 'utf8'))
import sys, io, urllib.request, re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

codes = 'sh600722,sz001267,sz000533,sz301396,sz001309'
url = 'https://qt.gtimg.cn/q=' + codes
data = urllib.request.urlopen(url).read()
text = data.decode('gbk')

for line in text.split(';'):
    line = line.strip()
    m = re.match(r'v_(\w+)="\d+~(.+?)~(\d+)~([\d.]+)~([\d.]+)', line)
    if m:
        code = m.group(3)
        name = m.group(2)
        price = m.group(4)
        prev_close = m.group(5)
        print(code + ': ' + name + ' | ' + price)

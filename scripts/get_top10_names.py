import urllib.request, re, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

codes = 'sh600722,sz001267,sz000533,sz301396,sz001309,sz002636,sh688411,sz300085,sh600821,sz000617'
url = f'https://qt.gtimg.cn/q={codes}'
data = urllib.request.urlopen(url).read()
text = data.decode('gbk')

for line in text.split(';'):
    line = line.strip()
    m = re.match(r'v_(\w+)="\d+~(.+?)~(\d+)~([\d.]+)', line)
    if m:
        print(f'{m.group(1)}|{m.group(2)}|{m.group(3)}|{m.group(4)}')

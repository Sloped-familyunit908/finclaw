import sys, io, urllib.request
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

codes = 'sh600722,sz001267,sz000533,sz301396,sz001309,sh601919,sz002151,sz000617,sz002636,sz002015,sh603799,sh601899,sh603993,sh600143,sh603179,sz300274,sh000001'
url = 'https://qt.gtimg.cn/q=' + codes
data = urllib.request.urlopen(url, timeout=10).read().decode('gbk')

for line in data.split(';'):
    line = line.strip()
    if not line:
        continue
    start = line.find('"')
    if start < 0:
        continue
    val = line[start+1:].rstrip('"')
    parts = val.split('~')
    if len(parts) < 10:
        continue
    name = parts[1]
    code = parts[2]
    cur = parts[3]
    prev = parts[4]
    try:
        cur_f = float(cur)
        prev_f = float(prev)
        if prev_f > 0 and cur_f > 0:
            chg = (cur_f - prev_f) / prev_f * 100
            print(code + ' ' + name + ': ' + cur + ' ({:+.2f}%)'.format(chg))
    except:
        pass

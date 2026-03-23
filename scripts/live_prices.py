import sys, io, urllib.request, re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

codes = [
    'sh600722', 'sz001267', 'sz000533', 'sz301396', 'sz001309',
    'sh601919', 'sz002151', 'sz000617', 'sz002636', 'sz002015',
    'sh603799', 'sh601899', 'sh603993', 'sh600143', 'sh603179',
    'sz002342', 'sz300803', 'sz300655', 'sh688361', 'sz301171',
    'sz300274', 'sh000001',
]

sina_codes = ','.join(codes)
url = 'https://hq.sinajs.cn/list=' + sina_codes
req = urllib.request.Request(url, headers={'Referer': 'https://finance.sina.com.cn'})
data = urllib.request.urlopen(req, timeout=10).read().decode('gbk')

for line in data.strip().split('\n'):
    line = line.strip()
    if not line or '=""' in line:
        continue
    eq = line.find('="')
    if eq < 0:
        continue
    var_part = line[:eq]
    val_part = line[eq+2:].rstrip('";')
    code = var_part.split('_')[-1]
    parts = val_part.split(',')
    if len(parts) < 9:
        continue
    name = parts[0]
    open_p = parts[1]
    prev = parts[2]
    cur = parts[3]
    high = parts[4]
    low = parts[5]
    
    try:
        prev_f = float(prev)
        cur_f = float(cur) if float(cur) > 0 else float(open_p)
        if prev_f > 0 and cur_f > 0:
            chg = (cur_f - prev_f) / prev_f * 100
            status = ''
            if float(cur) == 0 and float(open_p) > 0:
                status = ' [pre-open]'
                cur_f = float(open_p)
                chg = (cur_f - prev_f) / prev_f * 100
            print(code + ' ' + name + ': ' + str(cur_f) + ' (' + '{:+.2f}'.format(chg) + '%)' + status + '  prev=' + prev)
        else:
            print(code + ' ' + name + ': prev=' + prev + ' [waiting]')
    except:
        print(code + ' ' + name + ': parse error')

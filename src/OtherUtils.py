import os
import time
import datetime

import requests

'''计算时间相差小时数'''
def time_delta(begin_time, end_time):
    delta = end_time - begin_time
    print(delta.total_seconds())
    return delta.total_seconds() // 3600


'''识别图片验证码'''
def get_code_new(base64):
    im = base64.replace("data:image/png;base64,", "")
    headers = {
        'Connection': 'Keep-Alive',
        'User-Agent': 'Mozilla/4.0 (compatible; MSIE 8.0; Windows NT 5.1; Trident/4.0)',
    }
    params = {
        'user': 'QIngshang77',
        'pass': 'QIngshang77.',
        'softid': '961760',
        'codetype': 1006,
        'file_base64': im
    }
    r = requests.post('http://upload.chaojiying.net/Upload/Processing.php', data=params, headers=headers)
    recognized_text = r.json()['pic_str']
    return recognized_text

def build_timeslot(arrival):
    arrivalDatePlan = arrival['arrivalDatePlan']
    intervalIndex = arrival['intervalIndex']
    # 解析为日期对象
    date_obj = datetime.datetime.strptime(arrivalDatePlan, "%Y-%m-%d")
    # 转换为需要的格式
    formatted_date = date_obj.strftime("%d.%m.%Y")

    if intervalIndex == 23:
        return f'{formatted_date}, {"{:02}".format(intervalIndex)}:00 - {"{:02}".format(intervalIndex)}:59'
    else:
        return f'{formatted_date}, {"{:02}".format(intervalIndex)}:00 - {"{:02}".format(intervalIndex + 1)}:00'



if __name__ == '__main__':
    print(time.time())

    # mtime = os.path.getmtime('../cookies_test.pkl')
    mtime = os.path.getmtime('../chromedriver.exe')
    dtime = datetime.datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")
    dtime_obj = datetime.datetime.strptime(dtime, "%Y-%m-%d %H:%M:%S")
    begin = datetime.timedelta(seconds=dtime_obj.timestamp())
    print(time_delta(begin, datetime.timedelta(seconds=time.time())))




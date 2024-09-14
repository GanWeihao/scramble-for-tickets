import os
import time
import datetime

import requests

'''计算时间相差小时数'''
def time_delta(begin_time, end_time):
    delta = end_time - begin_time
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


def multipart_form_data(data, boundary='----WebKitFormBoundaryfbF0VMHoxcqE96jC', hearder={}):
    if 'content-type' in hearder:
        fd_val = str(hearder['content-type'])
        if 'boundary' in fd_val:
            fd_val = fd_val.split(';')[1].strip()
            boundary = fd_val.split('=')[1].strip()
        else:
            raise 'multipart/form-data content-type key boundary'

    # form-data
    jion_str = '--{}\r\nContent-Disposition: form-data; name="{}"\r\n\r\n{}\r\n'
    end_str = "--{}--".format(boundary)
    args_str = ""
    args_str = format_from_data(data, args_str, jion_str, boundary)
    args_str = args_str + end_str.format(boundary)
    args_str = args_str.replace("\'", "\"")
    return args_str


def format_from_data(data, args_str='', jion_str='', boundary='', filedname='', filedindex=0):
    if not isinstance(data, dict):
        raise "multipart/form-data data dict"
    for key, value in data.items():
        if type(value) == list:
            for idx in range(len(value)):
                if filedname == '':
                    args_str = format_from_data(value[idx], args_str, jion_str, boundary, filedname=key, filedindex=idx)
                else:
                    new_key = f'{filedname}[{filedindex}].{key}'
                    args_str = format_from_data(value[idx], args_str, jion_str, boundary, filedname=new_key,
                                                filedindex=idx)
        else:
            if filedname == '':
                args_str = args_str + jion_str.format(boundary, key, value)
            else:
                new_key = f'{filedname}[{filedindex}].{key}'
                args_str = args_str + jion_str.format(boundary, new_key, value)
    return args_str


if __name__ == '__main__':
    print(multipart_form_data({
        "typeOfTransportation": '1',
        "reservationId": '48429722-9821-443e-b09e-36c40b4942c3',
        "vehicles": [{
            "id": 'cb762c05-a95f-4265-b933-5f5c8aac204b',
            "regNumber": 'AU9766',
            "vehicleType": '3',
            "subType": '1',
            "status": '1',
            "scanDoc": [{
                "name": '16fb321b-af24-43d0-a881-22e8574b0fe6.png',
                "path": '16fb321b-af24-43d0-a881-22e8574b0fe6.png',
                "size": '697462',
                "createdAt": '0001-01-01T00:00:00'
            }]
        }]
    }))

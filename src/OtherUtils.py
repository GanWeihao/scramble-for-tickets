import datetime
import time
import ddddocr

from src.Logging import Logging

logger = Logging(__name__).get_logger()

ocr = ddddocr.DdddOcr(beta=True)

'''计算时间相差小时数'''
def time_delta(begin_time, end_time):
    delta = end_time - begin_time
    return delta.total_seconds() // 3600

'''计算两个日期之间相差天数'''
def date_delta(begin_date, end_date):
    # 将字符串转换为日期对象
    date_1 = datetime.datetime.strptime(begin_date, "%Y-%m-%d")
    date_2 = datetime.datetime.strptime(end_date, "%Y-%m-%d")

    # 计算两个日期之间的天数差
    delta = date_2 - date_1
    return delta.days + 1


'''识别图片验证码'''
def get_code_new(base64):
    result = ocr.classification(base64, png_fix=True)
    logger.info("------验证码识别为：%s------" % result)
    return result


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
    flag = True
    while flag:
        btime = time.time()
        while flag:
            etime = time.time()
            if etime - btime >= 5:
                flag = False
                break
            print("没到5秒")
    print("结束")

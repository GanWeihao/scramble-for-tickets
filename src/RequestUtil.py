import json
import pickle

import requests
import random, string

from src.Logging import Logging
from src.OtherUtils import multipart_form_data

logger = Logging(__name__).get_logger()


class RequestUtil:
    def __int__(self):
        pass

    def load_cookie(self, user_type):
        try:
            if user_type == '0':
                cookies = pickle.load(open("../cookies_test.pkl", "rb"))  # 载入cookie
            else:
                cookies = pickle.load(open("../cookies.pkl", "rb"))
            logger.info('------载入Cookie------')
            return cookies
        except Exception as e:
            logger.exception("------Cookie 加载失败，原因：%s------" % e)

    def request(self, url, method, headers=None, param=None, content_type=None, user_type='0'):
        """
        请求工具类传递的参数
        :param url:
        :param method:
        :param headers:
        :param param:
        :param content_type:
        :return:
        """
        try:
            cookies = self.load_cookie(user_type)
            cookieArr = []
            for cookie in cookies:
                cookieArr.append(f"{cookie.get('name')}={cookie.get('value')}")
            # 拼接cookies
            joined_cookies = "; ".join(cookieArr)
            headers['Cookie'] = joined_cookies
            headers['Content-Type'] = content_type
            logger.info("------请求URL：%s------" % url)
            logger.info("------请求参数：%s------" % param)
            if method == 'get':
                # .json() 返回的是json的数据
                result = requests.get(url=url, params=param, headers=headers)
                return result
            elif method == 'post':
                # 判断content_type，是表单还是json的请求
                if content_type == 'application/json':
                    result = requests.post(url=url, json=param, headers=headers)
                    return result
                elif content_type == 'application/x-www-form-urlencoded':
                    result = requests.post(url=url, json=param, headers=headers)
                    return result
                elif content_type == 'multipart/form-data':
                    boundary = '----WebKitFormBoundary' \
                               + ''.join(random.sample(string.ascii_letters + string.digits, 16))
                    headers['Content-Type'] = f'multipart/form-data; boundary={boundary}'
                    args_str = multipart_form_data(param, boundary, headers)
                    result = requests.post(url=url, data=args_str, headers=headers)
                    return result
                else:
                    print("请输入正确的content_type")
            else:
                print("目前只支持get/post")
        except Exception as e:
            print("http请求报错:{0}".format(e))


if __name__ == '__main__':
    param = {
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
    }
    UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36'
    Sec_Ch_Ua = '"Chromium";v="128", "Not;A=Brand";v="24", "Google Chrome";v="128"'
    headers = {
        'Ajax-method': 'AjaxMethodFactory',  # 这个很重要
        'User-Agent': UA,
        'Accept': 'application/json, text/plain, */*',
        'Accept-Encoding': 'gzip, deflate, br, zstd',
        'accept-language': 'zh-CN,zh;q=0.9',
        'Facilitymode': 'false',
        'Priority': 'u=1, i',
        'Sec-Ch-Ua': Sec_Ch_Ua,
        'Sec-Ch-Ua-Mobile': '?0',
        'Sec-Ch-Ua-Platform': '"Windows"',
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'same-origin',
    }
    boundary = '----WebKitFormBoundary' \
               + ''.join(random.sample(string.ascii_letters + string.digits, 16))

    requestUtil = RequestUtil()
    cookies = requestUtil.load_cookie('1')
    cookieArr = []
    for cookie in cookies:
        cookieArr.append(f"{cookie.get('name')}={cookie.get('value')}")
    # 拼接cookies
    joined_cookies = "; ".join(cookieArr)
    headers['Cookie'] = joined_cookies
    headers['Content-Type'] = f'multipart/form-data; boundary={boundary}'
    args_str = multipart_form_data(param, boundary, headers)
    res = requests.post(url='https://eopp.epd-portal.ru/reservations-api/v1/UpdateDraftStepTwo', data=args_str,
                        headers=headers)
    logger.info("------响应报文：%s------" % res)

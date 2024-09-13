import pickle

import requests
import random, string
from requests_toolbelt import MultipartEncoder

from src.Logging import Logging

logger = Logging(__name__).get_logger()


class RequestUtil:
    def __int__(self):
        pass

    def load_cookie(self, user_type):
        try:
            if user_type == '0':
                cookies = pickle.load(open("cookies_test.pkl", "rb"))  # 载入cookie
            else:
                cookies = pickle.load(open("cookies.pkl", "rb"))
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
            print(joined_cookies)
            headers['Cookie'] = joined_cookies
            headers['Content-Type'] = content_type

            if method == 'get':
                # .json() 返回的是json的数据
                res = requests.get(url=url, params=param, headers=headers).json()
                return res
            elif method == 'post':
                # 判断content_type，是表单还是json的请求
                if content_type == 'application/json':
                    res = requests.post(url=url, json=param, headers=headers).json()
                    return res
                elif content_type == 'application/x-www-form-urlencoded':
                    res = requests.post(url=url, json=param, headers=headers).json()
                    return res
                elif content_type == 'multipart/form-data':
                    boundary = '----WebKitFormBoundary' \
                               + ''.join(random.sample(string.ascii_letters + string.digits, 16))
                    m = MultipartEncoder(fields=param, boundary=boundary)
                    headers['Content-Type'] = m.content_type
                    res = requests.post(url=url, data=m, headers=headers).json()
                    return res
                else:
                    print("请输入正确的content_type")
            else:
                print("目前只支持get/post")
        except Exception as e:
            print("http请求报错:{0}".format(e))

import configparser
import datetime
import json
import os
import pickle
import random
import string
import time

from requests_toolbelt import MultipartEncoder
from selenium import webdriver
from selenium.webdriver import DesiredCapabilities
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

from src.Logging import Logging
from src.OtherUtils import time_delta, get_code_new, build_timeslot
from src.RequestUtil import RequestUtil

cfg = configparser.RawConfigParser()
conf_path = "config.conf"
cfg.read([conf_path], encoding='utf-8')

logger = Logging(__name__).get_logger()

requestUtil = RequestUtil()

WIDTH = 720
HEIGHT = 1280
PIXEL_RATIO = 3.0
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36'
Sec_Ch_Ua = '"Chromium";v="128", "Not;A=Brand";v="24", "Google Chrome";v="128"'

headers = {
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


class Task(object):
    def __init__(self):
        self.driver = None
        self.chrome_options = None
        # 测试账号信息，用于监控余票
        self.test_account = {'account': cfg.get("user_info_test", "account").strip(),
                             'password': cfg.get("user_info_test", "password").strip()}
        # 真实账号信息，用于抢票或改票
        self.account = {'account': cfg.get("user_info", "account").strip(),
                        'password': cfg.get("user_info", "password").strip()}
        # 网站登录URL
        self.login_url = cfg.get("web_info", "login_url").strip()
        # 浏览器驱动信息
        self.driver_path = cfg.get("other", "driver_path").strip()
        self.driver_path_chromedriver_v128 = cfg.get("other", "driver_path_chromedriver_v128").strip()
        # 调用方法, 初始化浏览器信息
        self.init_browser()

    def init_browser(self):
        # 设置无头浏览器 无界面浏览器
        self.chrome_options = webdriver.ChromeOptions()
        # 设置默认编码为utf-8，也就是中文
        self.chrome_options.add_argument('lang=zh_CN.UTF-8')
        # 禁止硬件加速
        self.chrome_options.add_argument('--disable-gpu')
        # 取消沙盒模式
        self.chrome_options.add_argument('--no-sandbox')
        # 禁止弹窗广告
        self.chrome_options.add_argument('--disable-popup-blocking')
        # 去掉反扒标志
        self.chrome_options.add_experimental_option('excludeSwitches', ['enable-automation'])
        # 此方法针对V78版本及以上有效，同时可以解决部分网站白屏的问题。
        self.chrome_options.add_experimental_option('useAutomationExtension', False)
        # ##大量渲染时候写入/tmp而非/dev/shm
        self.chrome_options.add_argument("-–disable-dev-shm-usage")
        # 打开开发者控制台
        self.chrome_options.add_argument("--auto-open-devtools-for-tabs")
        desired_capabilities = DesiredCapabilities.CHROME
        desired_capabilities["pageLoadStrategy"] = "none"

        mobileEmulation = {"deviceMetrics": {"width": WIDTH, "height": HEIGHT, "pixelRatio": PIXEL_RATIO},
                           "userAgent": UA}
        self.chrome_options.add_experimental_option("mobileEmulation", mobileEmulation)

    '''user_type: 0测试账号，1真实账号'''

    def get_cookie(self, user_type="0"):
        try:
            self.driver = webdriver.Chrome(executable_path=self.driver_path_chromedriver_v128,
                                           options=self.chrome_options,
                                           keep_alive=True)  # 此项稳定版打开
            with open('../stealth.min.js') as f:
                js = f.read()
            self.driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
                "source": js
            })
            # 将window.navigator.webdriver属性变为undefined 防止检测
            # 修改get方法
            script = 'Object.defineProperty(navigator, "webdriver", {get:()=>undefined,});'
            # execute_cdp_cmd用来执行chrome开发这个工具命令
            self.driver.execute_script(script)

            # 先进入登录页面进行登录
            logger.info("------开始登录------")
            self.driver.get(self.login_url)

            logger.info("------填入账号信息------")
            user_input = WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.XPATH, '//*[@id="mat-input-0"]')))
            pwd_input = WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.XPATH, '//*[@id="mat-input-1"]')))
            login_btn = WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.XPATH,
                                                '/html/body/app-root/layout-with-nav/app-flex-container/div/app-flex-item/div/app-signin/div/div[2]/div/div[3]/app-specialists-signin/div[2]/form/button')))

            if user_type == "0":
                user_input.send_keys(self.test_account['account'])  # 换为实际用户名
                time.sleep(1)
                pwd_input.send_keys(self.test_account['password'])  # 换为实际密码
            else:
                user_input.send_keys(self.account['account'])
                time.sleep(1)
                pwd_input.send_keys(self.account['password'])
            time.sleep(1)
            login_btn.click()
            logger.info("------登陆成功,等待页面加载------")

            # 等待页面加载完成
            WebDriverWait(self.driver, 20).until(EC.presence_of_element_located((By.XPATH,
                                                                                 '/html/body/app-root/layout-with-nav/app-flex-item/div/mat-sidenav-container/mat-sidenav-content/app-reservations-list-page/form/mat-sidenav-container/mat-sidenav-content')))
            # 保存Cookie，输出到文件
            if user_type == "0":
                self.begin_time = datetime.timedelta
                pickle.dump(self.driver.get_cookies(), open("../cookies_test.pkl", "wb"))
            else:
                pickle.dump(self.driver.get_cookies(), open("../cookies.pkl", "wb"))

            # 关闭浏览器
            self.driver.quit()
            logger.info("------Cookie保存成功------")
        except Exception as e:
            logger.exception(e)
            raise e

    '''余票监测'''

    def timeslot_check(self, date=None, time_str=None, stime='00:00', etime='23:59'):
        self.ckeck_cookie()

        request_url = cfg.get("web_info", "timeslot_registry_url").strip()
        params = {
            'facilityIdFilter': '1dae5b1c-e2b3-44a4-848f-df8ce2ddde42',
            'startDate': date,
            'endDate': date,
            'startTime': stime,
            'endTime': etime,
            'pageIndex': 1,
            'pageSize': 100
        }
        headers_temp = headers
        headers_temp['referer'] = 'https://eopp.epd-portal.ru/en/reservations/new/reservation'
        res = requestUtil.request(url=request_url,
                                  method='get',
                                  headers=headers_temp,
                                  param=params,
                                  content_type='application/json',
                                  user_type='0')
        result = {
            'arrivalDatePlan': date
        }
        for idx in range(len(res['capacities'])):
            slot = res['capacities'][idx]
            if time_str is not None:
                slotTime = slot['slotTime'].replace(" ", "")
                if slotTime[0:4] == time_str and int(slot['capacityPortal']['free']):
                    result['intervalIndex'] = idx
                    return result
            else:
                if int(slot['capacityPortal']['free']) > 0:
                    result['intervalIndex'] = idx
                    return result
        # 延迟1秒执行，防止被墙
        time.sleep(1)
        # 如果没有符合条件的，则迭代调用，直到刷出余票
        return self.timeslot_check(date, time)

    '''获取用户信息'''

    def get_user_info(self):
        self.ckeck_cookie()
            
        request_url = cfg.get("web_info", "get_user_info_url").strip()
        param = {
            'isTso': 'false'
        }
        headers_temp = headers
        headers_temp['referer'] = 'https://eopp.epd-portal.ru/en/reservations/new/reservation'
        res = requestUtil.request(url=request_url,
                                  method='get',
                                  headers=headers_temp,
                                  param=param,
                                  content_type='application/json',
                                  user_type='1')
        self.user_info = res

    '''获取图片验证码'''
    def create_captcha(self):
        self.ckeck_cookie()

        request_url = cfg.get("web_info", "create_captcha_url").strip()
        param = {}
        headers_temp = headers
        headers_temp['referer'] = 'https://eopp.epd-portal.ru/en/reservations/new/reservation'
        res = requestUtil.request(url=request_url,
                                  method='get',
                                  headers=headers_temp,
                                  param=param,
                                  content_type='application/json',
                                  user_type='1')
        self.captcha = {
            'captachaHash': res['fileDownloadName'],
            'captachaInputText': get_code_new(res['fileContents'])
        }

    '''生成草稿订单'''
    def create_draft(self, arrival, regNumber=None):
        self.ckeck_cookie()

        if regNumber is None:
            logger.exception('请填写车牌号')
            return

        self.create_captcha()

        request_url = cfg.get("web_info", "create_draft_url").strip()
        param = {
            "fio": self.user_info['fullName'],
            "organizationName": "",
            "inn": str(self.user_info['inn']),
            "orgInn": self.user_info['orgInn'],
            "requesterType": "Foreign organization",
            "organizationForm": "",
            "ogrnip": "",
            "phone": self.user_info['phone'],
            "email": self.user_info['email'],
            "acceptContacts": 'true',
            "source": 0
        }
        headers_temp = headers
        headers_temp['referer'] = 'https://eopp.epd-portal.ru/en/reservations/new/reservation'
        res = requestUtil.request(url=request_url,
                                  method='post',
                                  headers=headers_temp,
                                  param=param,
                                  content_type='application/json',
                                  user_type='1')
        if res['isSuccess']:
            logger.info("订单创建成功")
            self.search_vehicles(regNumber)
            reservationRequestId = res['entity']['reservationRequestId']
            # 更新车辆信息
            self.update_draft(reservationRequestId)
            # 提交订单
            isSuccess = self.submit_draft_url(arrival, reservationRequestId)
            if isSuccess:
                return

            # 上述暂无余票，重新检查余票情况
            arrival_new = self.available_slots(arrival)
            if arrival_new is not None:
                isSuccess = self.submit_draft_url(arrival_new, reservationRequestId)
        else:
            # 请求失败，2秒后重试
            time.sleep(2)
            self.create_draft()

    '''查询车辆信息，regNumber-车牌号'''
    def search_vehicles(self, regNumber=None):
        self.ckeck_cookie()

        request_url = cfg.get("web_info", "search_vehicles_url").strip()
        param = {
            "substring": regNumber,
            "subtype": "1"
        }
        headers_temp = headers
        headers_temp['referer'] = 'https://eopp.epd-portal.ru/en/reservations/new/reservation'
        res = requestUtil.request(url=request_url,
                                  method='get',
                                  headers=headers_temp,
                                  param=param,
                                  content_type='application/json',
                                  user_type='1')
        if len(res) <= 0:
            raise ValueError('车牌号不存在，请检查')
        for vehicle in res:
            if vehicle['regNumber'] == regNumber and vehicle['status'] == 1:
                self.vehicle = vehicle
                logger.info("车辆信息获取成功")
                return

        raise ValueError('车辆不存在或车辆状态不可用')

    '''更新车辆信息'''
    def update_draft(self, reservationId=None):
        self.ckeck_cookie()

        if reservationId is None:
            logger.exception("请传入订单ID")
            return

        request_url = cfg.get("web_info", "update_draft_url").strip()
        param = MultipartEncoder(
            fields={
                "typeOfTransportation": '1',
                "reservationId": str(reservationId),
                "vehicles": json.dumps([{
                    "id": self.vehicle['id'],
                    "regNumber": self.vehicle['regNumber'],
                    "vehicleType": str(self.vehicle['vehicleType']),
                    "subType": str(self.vehicle['subType']),
                    "status": str(self.vehicle['status']),
                    "scanDoc": json.dumps([{
                        "name": self.vehicle['scanDoc'][0]['name'],
                        "path": self.vehicle['scanDoc'][0]['path'],
                        "size": str(self.vehicle['scanDoc'][0]['size']),
                        "createdAt": self.vehicle['scanDoc'][0]['createdAt']
                    }])
                }])
            }
        )
        boundary = '----WebKitFormBoundary' \
                   + ''.join(random.sample(string.ascii_letters + string.digits, 16))
        m = MultipartEncoder(fields=param, boundary=boundary)

        headers_temp = headers
        headers_temp['referer'] = 'https://eopp.epd-portal.ru/en/reservations/new/reservation'
        res = requestUtil.request(url=request_url,
                                  method='post',
                                  headers=headers_temp,
                                  param=param,
                                  content_type='multipart/form-data',
                                  user_type='1')
        if res['isSuccess']:
            logger.info("更新车辆信息成功")
        else:
            raise RuntimeError(f"更新车辆信息失败【{res['errorMessage']}】")

    '''提交订单'''
    def submit_draft_url(self, arrival, reservationId):
        self.ckeck_cookie()

        request_url = cfg.get("web_info", "submit_draft_url").strip()
        param = {
            "reservationId": reservationId,
            "countryId": "156",
            "facilityId": "1dae5b1c-e2b3-44a4-848f-df8ce2ddde42",
            "arrivalDatePlan": arrival['arrivalDatePlan'],
            "timeslot": build_timeslot(arrival),
            "captachaInputText": self.captcha['captachaInputText'],
            "captachaHash": self.captcha['captachaHash'],
            "intervalIndex": arrival['intervalIndex'],
            "transportType": 1,
            "modeType": 1,
            "isTso": False
        }
        headers_temp = headers
        headers_temp['referer'] = 'https://eopp.epd-portal.ru/en/reservations/new/reservation'
        res = requestUtil.request(url=request_url,
                                  method='post',
                                  headers=headers_temp,
                                  param=param,
                                  content_type='application/json',
                                  user_type='1')
        if res['isSuccess']:
            logger.info("订单提交成功")
            return True
        else:
            logger.info("订单提交失败")
            return False


    '''查询余票情况'''
    def available_slots(self, arrival):
        self.ckeck_cookie()

        request_url = cfg.get("web_info", "available_slots_url").strip()
        param = {
            "facilityId": '1dae5b1c-e2b3-44a4-848f-df8ce2ddde42',
            "vehicleId": self.vehicle['id'],
            "date": arrival['arrivalDatePlan'],
            "transportType": 1,
            "isCreateReservation": 'true'
        }
        headers_temp = headers
        headers_temp['referer'] = 'https://eopp.epd-portal.ru/en/reservations/new/reservation'
        res = requestUtil.request(url=request_url,
                                  method='get',
                                  headers=headers_temp,
                                  param=param,
                                  content_type='application/json',
                                  user_type='1')

        if len(res['slots']) > 0:
            for slot in res['slots']:
                if int(slot['count']) > 0:
                    arrival['intervalIndex'] = int(slot['intervalIndex'])
                    return arrival
        logger.error("暂无余票，重新监测")
        return None

    def ckeck_cookie(self):
        if not os.path.exists("../cookies_test.pkl"):
            logger.info('Cookie文件不存在，重新登录生成')
            self.get_cookie('0')
            time.sleep(2)
            self.get_cookie('1')
        else:
            # 获取文件创建时间
            mtime = os.path.getmtime("../cookies_test.pkl")
            dtime = datetime.datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")
            dtime_obj = datetime.datetime.strptime(dtime, "%Y-%m-%d %H:%M:%S")
            if time_delta(begin_time=datetime.timedelta(seconds=dtime_obj.timestamp()), end_time=datetime.timedelta(seconds=time.time())) > 7:
                logger.info('Cookie过期，重新获取')
                self.get_cookie('0')
                time.sleep(2)
                self.get_cookie('1')

        logger.info('Cookie有效...')


if __name__ == '__main__':
    task = Task()
    task.ckeck_cookie()
    task.get_user_info()
    # 返回有余票的 日期 和 时间index
    arrival = task.timeslot_check('2024-09-28')
    task.create_draft(arrival, 'AU9766')

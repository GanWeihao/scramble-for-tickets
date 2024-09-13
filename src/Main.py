import configparser
import datetime
import os
import pickle
import time

from selenium import webdriver
from selenium.webdriver import DesiredCapabilities
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

from src.Logging import Logging
from src.OtherUtils import time_delta
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
                self.begin_time = datetime.time
                pickle.dump(self.driver.get_cookies(), open("cookies_test.pkl", "wb"))
            else:
                pickle.dump(self.driver.get_cookies(), open("cookies.pkl", "wb"))

            # 关闭浏览器
            self.driver.quit()
            logger.info("------Cookie保存成功------")
        except Exception as e:
            logger.exception(e)
            raise e

    '''余票监测'''

    def timeslot_check(self, date=None, time=None):
        if time_delta(self.begin_time, datetime.time) > 7:
            self.get_cookie('0')
            time.sleep(3)
            self.get_cookie('1')

        request_url = cfg.get("web_info", "timeslot_registry_url").strip()
        params = {
            'facilityIdFilter': '1dae5b1c-e2b3-44a4-848f-df8ce2ddde42',
            'startDate': date,
            'endDate': date,
            'startTime': '00:00',
            'endTime': '23:59',
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
            if time is not None:
                slotTime = slot['slotTime'].replace(" ", "")
                if slotTime[0:4] == time and int(slot['capacityPortal']['free']):
                    result['intervalIndex'] = idx + 1
                    return result
            else:
                if int(slot['capacityPortal']['free']) > 0:
                    result['intervalIndex'] = idx + 1
                    return result
        # 延迟2秒执行，防止被墙
        time.sleep(2)
        # 如果没有符合条件的，则迭代调用，直到刷出余票
        return self.timeslot_check(date, time)

    '''获取用户信息'''

    def get_user_info(self):
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

    '''生成草稿订单'''
    def create_draft(self, arrival, regNumber=None):
        if time_delta(self.begin_time, datetime.time) > 7:
            self.get_cookie('0')
            time.sleep(3)
            self.get_cookie('1')

        if regNumber is None:
            logger.exception('请填写车牌号')
            return

        request_url = cfg.get("web_info", "create_draft_url").strip()
        param = {
            "fio": self.user_info['fullName'],
            "organizationName": "",
            "inn": self.user_info['inn'],
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
        if time_delta(self.begin_time, datetime.time) > 7:
            self.get_cookie('0')
            time.sleep(3)
            self.get_cookie('1')
        request_url = cfg.get("web_info", "create_draft_url").strip()
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
            if vehicle['regNumber'] == regNumber and vehicle['status'] == '1':
                self.vehicle = vehicle
                logger.info("车辆信息获取成功")
                return

        raise ValueError('车辆不存在或车辆状态不可用')

    '''更新车辆信息'''
    def update_draft(self, reservationId=None):
        if time_delta(self.begin_time, datetime.time) > 7:
            self.get_cookie('0')
            time.sleep(3)
            self.get_cookie('1')

        if reservationId is None:
            logger.exception("请传入订单ID")
            return

        request_url = cfg.get("web_info", "create_draft_url").strip()
        param = {
            "typeOfTransportation": 1,
            "reservationId": reservationId,
            "vehicles": [{
                "id": self.vehicle['id'],
                "regNumber": self.vehicle['regNumber'],
                "vehicleType": self.vehicle['vehicleType'],
                "subType": self.vehicle['subType'],
                "status": self.vehicle['status'],
                "scanDoc": self.vehicle['scanDoc']
            }]
        }
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
        if time_delta(self.begin_time, datetime.time) > 7:
            self.get_cookie('0')
            time.sleep(3)
            self.get_cookie('1')

        request_url = cfg.get("web_info", "submit_draft_url").strip()
        param = {
            "reservationId": reservationId,
            "countryId": "156",
            "facilityId": "1dae5b1c-e2b3-44a4-848f-df8ce2ddde42",
            "arrivalDatePlan": arrival['arrivalDatePlan'],
            "timeslot": "27.09.2024, 03:00 - 04:00",
            "captachaInputText": "8513",
            "captachaHash": "RTjPWqprwRFpFmDWB/28TQ==",
            "intervalIndex": arrival['intervalIndex'],
            "transportType": 1,
            "modeType": 1,
            "isTso": 'false'
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
        if time_delta(self.begin_time, datetime.time) > 7:
            self.get_cookie('0')
            time.sleep(3)
            self.get_cookie('1')

        request_url = cfg.get("web_info", "available_slots_url").strip()
        param = {
            "facilityId": '1dae5b1c-e2b3-44a4-848f-df8ce2ddde42',
            "vehicleId": self.vehicle.id,
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

if __name__ == '__main__':
    task = Task()
    task.get_cookie("0")
    time.sleep(3)
    task.get_cookie("1")
    task.get_user_info()
    # 返回有余票的 日期 和 时间index
    arrival = task.timeslot_check('2024-09-28')
    task.create_draft(arrival, 'AU5629')

import concurrent.futures
import configparser
import datetime
import os
import pickle
import sys
import time

from selenium import webdriver
from selenium.webdriver import DesiredCapabilities
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

from src.Logging import Logging
from src.OtherUtils import time_delta, get_code_new, build_timeslot, date_delta, get_code_new_py
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

if sys.platform.startswith("win"):
    print("当前系统是Windows")
elif sys.platform.startswith("darwin"):
    print("当前系统是Mac OS")
    UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36'
else:
    print("当前系统是其他操作系统")

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

flag = True


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
        # 浏览器驱动
        if sys.platform.startswith("darwin"):
            self.chromedriver = cfg.get("other", "driver_path_mac").strip()
        else:
            self.chromedriver = cfg.get("other", "driver_path_chromedriver_v128").strip()

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
        # 禁用浏览器自动化检测功能
        self.chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        # ##大量渲染时候写入/tmp而非/dev/shm
        self.chrome_options.add_argument("-–disable-dev-shm-usage")
        # 打开开发者控制台
        # self.chrome_options.add_argument("--auto-open-devtools-for-tabs")
        desired_capabilities = DesiredCapabilities.CHROME
        desired_capabilities["pageLoadStrategy"] = "none"

        mobileEmulation = {"deviceMetrics": {"width": WIDTH, "height": HEIGHT, "pixelRatio": PIXEL_RATIO},
                           "userAgent": UA}
        self.chrome_options.add_experimental_option("mobileEmulation", mobileEmulation)

    """user_type: 0测试账号，1真实账号"""

    def get_cookie(self, user_type="0"):
        try:
            self.driver = webdriver.Chrome(executable_path=self.chromedriver,
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

            page_is_already = False
            while not page_is_already:
                try:
                    logger.info("------填入账号信息------")
                    user_input = WebDriverWait(self.driver, 20).until(
                        EC.presence_of_element_located((By.XPATH, '//*[@id="mat-input-0"]')))
                    pwd_input = WebDriverWait(self.driver, 20).until(
                        EC.presence_of_element_located((By.XPATH, '//*[@id="mat-input-1"]')))
                    login_btn = WebDriverWait(self.driver, 20).until(
                        EC.presence_of_element_located((By.XPATH,
                                                        '/html/body/app-root/layout-with-nav/app-flex-container/div/app-flex-item/div/app-signin/div/div[2]/div/div[3]/app-specialists-signin/div[2]/form/button')))
                    page_is_already = True
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
                    logger.info("------登录成功,等待页面加载------")
                except Exception as e:
                    logger.error('页面加载失败，准备重新加载 %s' % e)

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
            self.driver.quit()
            raise e

    """余票监测"""

    def timeslot_check(self, begin_date=None, end_date=None):
        global flag
        result = {}
        facilityIdFilter = '1dae5b1c-e2b3-44a4-848f-df8ce2ddde42'
        free_key = ''
        while flag:
            try:
                self.ckeck_cookie()

                request_url = cfg.get("web_info", "timeslot_registry_url").strip()
                params = {
                    'startDate': begin_date,
                    'endDate': end_date,
                }
                headers_temp = headers
                headers_temp['referer'] = 'https://eopp.epd-portal.ru/en/reservations/new/reservation'
                res = requestUtil.request(url=request_url,
                                          method='get',
                                          headers=headers_temp,
                                          param=params,
                                          content_type='application/json',
                                          user_type='0')
                for idx in range(len(res['entries'])):
                    timeslot = res['entries'][idx]
                    if timeslot['facilityId'] == facilityIdFilter:
                        for key in timeslot['capacitiesByDates']:
                            if int(timeslot['capacitiesByDates'][key]['capacityPortal']['free']) > 0:
                                free_key = key
                                break
                    if free_key != '':
                        flag = False
                        break
                if flag:
                    logger.info('------所选日期暂无余票，持续监测中------')
                    # 延迟2秒执行，防止被墙
                    WAIT_TIME = float(cfg.get('task_info', 'WAIT_TIME').strip())
                    time.sleep(WAIT_TIME)
            except Exception as e:
                logger.exception(e)
        result['arrivalDatePlan'] = free_key
        return result


    """获取用户信息"""

    def get_user_info(self):
        logger.info('------获取用户信息------')
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

    """获取图片验证码"""
    def create_captcha(self):
        global flag
        VER_CODE_TIME = int(cfg.get('task_info', 'VER_CODE_TIME').strip())
        while flag:
            begin_time = time.time()
            logger.info('------获取图片验证码------')
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
            while flag:
                end_time = time.time()
                if end_time - begin_time >= VER_CODE_TIME:
                    break

    """生成草稿订单"""
    def create_draft(self, regNumber=None):
        logger.info('------生成草稿订单------')
        self.ckeck_cookie()

        if regNumber is None:
            logger.exception('请填写车牌号')
            return

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
            logger.info("------草稿订单创建成功------")

            # 查询车辆信息
            self.search_vehicles(regNumber)

            reservationRequestId = res['entity']['reservationRequestId']
            # 更新车辆信息
            self.update_draft(reservationRequestId)
            logger.info("------订单信息填写完成------")
            return reservationRequestId
        else:
            # 请求失败，2秒后重试
            time.sleep(2)
            self.create_draft(regNumber)

    """查询车辆信息，regNumber-车牌号"""
    def search_vehicles(self, regNumber=None):
        logger.info(f'------查询车辆{regNumber}信息------')
        self.ckeck_cookie()

        request_url = cfg.get("web_info", "search_vehicles_url").strip()
        param = {"commonParams":{"pageIndex":1,"pageSize":500,"sortColumn":"created_at","isDescSort":True},"filters":{}}
        headers_temp = headers
        headers_temp['referer'] = 'https://eopp.epd-portal.ru/en/reservations/new/reservation'
        res = requestUtil.request(url=request_url,
                                  method='post',
                                  headers=headers_temp,
                                  param=param,
                                  content_type='application/json',
                                  user_type='1')
        if len(res['payload']) <= 0:
            raise ValueError('暂无可用车辆')
        for vehicle in res['payload']:
            if vehicle['regNumber'] == regNumber and vehicle['status'] == 1:
                self.vehicle = vehicle
                logger.info("车辆信息获取成功")
                return

        raise ValueError('车辆不存在或车辆状态不可用')

    """更新订单车辆信息"""
    def update_draft(self, reservationId=None):
        logger.info('------更新订单车辆信息------')
        self.ckeck_cookie()

        if reservationId is None:
            logger.exception("请传入订单ID")
            return

        request_url = cfg.get("web_info", "update_draft_url").strip()
        param = {
            "typeOfTransportation": '1',
            "reservationId": str(reservationId),
            "vehicles": [{
                "id": self.vehicle['id'],
                "regNumber": self.vehicle['regNumber'],
                "vehicleType": str(self.vehicle['vehicleTypeId']),
                "subType": str(self.vehicle['subTypeId']),
                "status": str(self.vehicle['status']),
                "scanDoc": [{
                    "name": self.vehicle['scanDoc'][0]['name'],
                    "path": self.vehicle['scanDoc'][0]['path'],
                    "size": str(self.vehicle['scanDoc'][0]['size']),
                    "createdAt": self.vehicle['scanDoc'][0]['createdAt']
                }]
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

    """提交订单"""
    def submit_draft_url(self, arrival, reservationId):
        logger.info('------开始提交订单：%s ------' % arrival)
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

    """改签订单"""
    def reschedule(self, arrival, reservationId):
        logger.info('------开始改签订单：%s ------' % arrival)
        self.ckeck_cookie()

        request_url = cfg.get("web_info", "reschedule_url").strip()
        param = {
            "reservationRequestId": reservationId,
            "timeslot": build_timeslot(arrival),
            "date": arrival['arrivalDatePlan'],
            "captachaInputText": self.captcha['captachaInputText'],
            "captachaHash": self.captcha['captachaHash'],
            "transportType": 1,
            "intervalIndex": arrival['intervalIndex'],
            "facilityId": "1dae5b1c-e2b3-44a4-848f-df8ce2ddde42"
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
            logger.info("------订单改签成功------")
            return True
        else:
            logger.exception("======订单改签失败======")
            return False

    """查询余票情况"""
    def available_slots(self, arrival):
        global flag
        logger.info("------查询余票情况------")
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
                    arrival['arrivalDatePlan'] = arrival['arrivalDatePlan']
                    logger.info(f"{arrival['arrivalDatePlan']} {slot['slotCaption']}: 有余票")
                    flag = False
                    return arrival
        flag = False
        logger.error("暂无余票，重新监测")
        return None

    """校验Cookie"""
    def ckeck_cookie(self):
        logger.info("------开始校验Cookie------")
        if not os.path.exists("../cookies_test.pkl"):
            logger.warn('******Cookie文件不存在，重新登录生成******')
            self.get_cookie('0')
            time.sleep(1)
            self.get_cookie('1')
        else:
            # 获取文件创建时间
            mtime = os.path.getmtime("../cookies_test.pkl")
            dtime = datetime.datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")
            dtime_obj = datetime.datetime.strptime(dtime, "%Y-%m-%d %H:%M:%S")
            if time_delta(begin_time=datetime.timedelta(seconds=dtime_obj.timestamp()),
                          end_time=datetime.timedelta(seconds=time.time())) > 7:
                logger.warn('******Cookie过期，重新获取******')
                self.get_cookie('0')
                time.sleep(2)
                self.get_cookie('1')

        logger.info('------Cookie有效...------')


if __name__ == '__main__':
    task = Task()
    task.ckeck_cookie()
    task_type = cfg.get("task_info", "task_type").strip()
    if task_type == '1':
        """新建订单任务"""
        regNumber = cfg.get("submit_info", "reg_number").strip()
        begin_date = cfg.get("submit_info", "begin_date").strip()
        end_date = cfg.get("submit_info", "end_date").strip()

        # 获取用户信息
        task.get_user_info()

        is_success = False
        submit_num = 0
        reservationRequest_id = ''
        while not is_success:
            flag = True
            try:
                with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
                    # Step1 获取验证码
                    future_code = executor.submit(task.create_captcha)
                    # Step2: 新建草稿订单
                    if reservationRequest_id == '':
                        future_one = executor.submit(task.create_draft, regNumber)
                    # Step3: 扫描当天任意时段余票
                    future_two = executor.submit(task.timeslot_check, begin_date, end_date)
                    # 等待所有线程结束
                    executor.shutdown(wait=True)
                    # 获取线程返回的结果
                    if reservationRequest_id == '':
                        reservationRequest_id = future_one.result()
                    arrival = future_two.result()
                # Step4: 查看余票详情
                arrival_new = task.available_slots(arrival)
                # Step5: 提交订单
                submit_num += 1
                logger.info("------准备第%d次提交订单------" % submit_num)
                submit_result = task.submit_draft_url(arrival_new, reservationRequest_id)
                if submit_result:
                    is_success = True
            except Exception as e:
                # 处理其他所有异常
                logger.exception("******发现错误%s，准备重试******" % e)

    else:
        """改签订单任务"""
        reservation_id = cfg.get("reschedule_info", "reservation_id").strip()
        begin_date = cfg.get("reschedule_info", "begin_date").strip()
        end_date = cfg.get("reschedule_info", "end_date").strip()

        is_success = False
        reschedule_num = 0
        while not is_success:
            flag = True
            try:
                with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
                    # Step1: 获取验证码
                    future_one = executor.submit(task.create_captcha)
                    # Step2: 扫描当天任意时段余票
                    future_two = executor.submit(task.timeslot_check, begin_date, end_date)
                    # 等待所有线程结束
                    executor.shutdown(wait=True)
                    # 获取线程返回的结果
                    arrival = future_two.result()
                # Step3: 查看余票详情
                arrival_new = task.available_slots(arrival)
                reschedule_num += 1
                logger.info("------准备第%d次改签订单------" % reschedule_num)
                # Step4: 改签订单
                reschedule_result = task.reschedule(arrival_new, reservation_id)
                if reschedule_result:
                    is_success = True
            except Exception as e:
                # 处理其他所有异常
                logger.exception("******发现错误%s，准备重试******" % e)
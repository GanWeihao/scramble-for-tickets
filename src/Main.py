import configparser
import time

from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.wait import WebDriverWait

from src.Logging import Logging

from selenium import webdriver
from selenium.webdriver import DesiredCapabilities
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

cfg = configparser.RawConfigParser()
conf_path = "config.conf"
cfg.read([conf_path], encoding='utf-8')

logger = Logging(__name__).get_logger()

WIDTH = 720
HEIGHT = 1280
PIXEL_RATIO = 3.0
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36'
Sec_Ch_Ua = '"Google Chrome";v="125", "Chromium";v="125", "Not.A/Brand";v="24"'


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

        self.open_browser()

    def open_browser(self):
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
        # # 忽略证书错误（实操没卵用）
        # self.chrome_options.add_argument('--ignore-certificate-errors')

        # 保存浏览历史下次读取直接读取里面的内容
        # dir_path = os.getcwd()
        # self.chrome_options.add_argument(f'user-data-dir={dir_path}/userData')

        mobileEmulation = {"deviceMetrics": {"width": WIDTH, "height": HEIGHT, "pixelRatio": PIXEL_RATIO},
                           "userAgent": UA}
        self.chrome_options.add_experimental_option("mobileEmulation", mobileEmulation)

        service = Service(self.driver_path)
        # service = Service(self.driver_path_chromedriver_v128)
        self.driver = webdriver.Chrome(executable_path=self.driver_path_chromedriver_v128, options=self.chrome_options, keep_alive=True)  # 此项稳定版打开
        # self.driver = webdriver.Chrome(executable_path=self.driver_path)  # 默认谷歌浏览器, 指定下驱动的位置
        # self.driver = webdriver.Chrome()  # 默认谷歌浏览器
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

    def get_cookie(self, user_type="0"):
        # 先进入登录页面进行登录
        logger.info("------开始登录------")
        self.driver.get(self.login_url)

        user_input = WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.XPATH, '//*[@id="mat-input-0"]')))
        user_input.send_keys(self.test_account['account'])  # 换为实际用户名
        time.sleep(1)
        pwd_input = self.driver.find_element(By.XPATH, '//*[@id="mat-input-1"]')
        pwd_input.send_keys(self.test_account['password'])  # 换为实际密码
        time.sleep(1)
        login_btn = self.driver.find_element(By.XPATH, '/html/body/app-root/layout-with-nav/app-flex-container/div/app-flex-item/div/app-signin/div/div[2]/div/div[3]/app-specialists-signin/div[2]/form/button')
        login_btn.click()
        time.sleep(1)

        logger.info("用户类型 --- %s ---" % user_type)


if __name__ == '__main__':
    task = Task()
    task.get_cookie("1")
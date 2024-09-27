import os
project_path = os.path.abspath(os.path.dirname(__file__))
os.chdir(project_path)

import configparser
import concurrent.futures

from src.Logging import Logging
from src.Task import Task

cfg = configparser.RawConfigParser()
conf_path = "config.conf"
cfg.read([conf_path], encoding='utf-8')

logger = Logging(__name__).get_logger()

if __name__ == '__main__':
    task = Task()
    task.ckeck_cookie()
    task_type = cfg.get("task_info", "task_type").strip()
    if task_type == '1':
        """新建订单任务"""
        regNumber = cfg.get("submit_info", "reg_number").strip()
        begin_date = cfg.get("submit_info", "begin_date").strip()
        end_date = cfg.get("submit_info", "end_date").strip()
        time_str = cfg.get("submit_info", "time_str").strip()
        submit_type = cfg.get("submit_info", "submit_type").strip()

        # 获取用户信息
        future_three = task.get_user_info()

        is_success = False
        submit_num = 0
        reservationRequest_id = ''
        while not is_success:
            flag = True
            try:
                with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
                    # 获取验证码
                    future_code = executor.submit(task.create_captcha)

                    # Step1: 新建草稿订单
                    if reservationRequest_id == '':
                        future_one = executor.submit(task.create_draft, regNumber)

                    if submit_type == '1':
                        # Step2: 扫描当天任意时段余票
                        future_two = executor.submit(task.timeslot_check, begin_date, end_date, None)
                    else:
                        # Step2: 扫描当天指定时段余票
                        future_two = executor.submit(task.timeslot_check, begin_date, end_date, time_str)
                    # 等待所以线程结束
                    executor.shutdown(wait=True)
                    # 获取线程返回的结果
                    if reservationRequest_id == '':
                        reservationRequest_id = future_one.result()
                    arrival = future_two.result()

                # Step3: 提交订单
                submit_num += 1
                logger.info("------准备第%d次提交订单------" % submit_num)
                submit_result = task.submit_draft_url(arrival, reservationRequest_id)
                if submit_result:
                    is_success = True
                else:
                    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as resubmit_executor:
                        # 重新获取验证码
                        resubmit_executor.submit(task.create_captcha)
                        # 上述暂无余票，重新检查余票情况
                        available_slots_task = resubmit_executor.submit(task.available_slots, arrival)
                        resubmit_executor.shutdown(wait=True)
                        arrival_new = available_slots_task.result()
                    if arrival_new is not None:
                        submit_num += 1
                        logger.info("------准备第%d次提交订单------" % submit_num)
                        is_success = task.submit_draft_url(arrival_new, reservationRequest_id)
            except Exception as e:
                # 处理其他所有异常
                logger.exception("******发现错误%s，准备重试******" % e)

    else:
        """改签订单任务"""
        reservation_id = cfg.get("reschedule_info", "reservation_id").strip()
        begin_date = cfg.get("reschedule_info", "begin_date").strip()
        end_date = cfg.get("reschedule_info", "end_date").strip()
        time_str = cfg.get("reschedule_info", "time_str").strip()
        reschedule_type = cfg.get("reschedule_info", "reschedule_type").strip()

        is_success = False
        reschedule_num = 0
        while not is_success:
            flag = True
            try:
                with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
                    # Step1: 获取验证码
                    future_one = executor.submit(task.create_captcha)
                    if reschedule_type == '1':
                        # Step2: 扫描当天任意时段余票
                        future_two = executor.submit(task.timeslot_check, begin_date, end_date, None)
                    else:
                        # Step2: 扫描当天指定时段余票
                        future_two = executor.submit(task.timeslot_check, begin_date, end_date, time_str)
                    # 等待所有线程结束
                    executor.shutdown(wait=True)
                    # 获取线程返回的结果
                    arrival = future_two.result()

                reschedule_num += 1
                logger.info("------准备第%d次改签订单------" % reschedule_num)
                # Step3: 改签订单
                reschedule_result = task.reschedule(arrival, reservation_id)
                if reschedule_result:
                    is_success = True
            except Exception as e:
                # 处理其他所有异常
                logger.exception("******发现错误%s，准备重试******" % e)
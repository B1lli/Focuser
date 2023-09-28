# coding=utf-8
"""
@author B1lli
@date 2023年09月28日 16:07:55
@File:main.py
"""
import flet as ft


import time
import pygetwindow as gw
import psutil
import win32process
import threading
from utils import *


supervise_state = True
last_window_title = None
last_process_name = None
window_start_time = None
window_durations = {}
process_durations = {}
switch_count = 0





def monitor_active_window():
    global last_window_title, last_process_name, window_start_time, window_durations, process_durations, switch_count

    try:
        while True:
            current_window_title = gw.getActiveWindowTitle()

            # 获取进程名
            windows = gw.getWindowsWithTitle(current_window_title)
            current_process_name = None
            if windows:
                hwnd = windows[0]._hWnd
                _, process_id = win32process.GetWindowThreadProcessId(hwnd)
                try:
                    process = psutil.Process(process_id)
                    current_process_name = process.name()
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    pass
            else:
                current_process_name = None

            # 如果当前窗口标题或进程名与上一个不同，说明用户切换了窗口或进程
            if current_window_title != last_window_title or current_process_name != last_process_name:
                switch_count += 1
                # 如果上一个窗口标题不为空，记录其停留时间
                if last_window_title:
                    duration = time.time() - window_start_time
                    window_durations[last_window_title] = window_durations.get(last_window_title, 0) + duration
                    process_durations[last_process_name] = process_durations.get(last_process_name, 0) + duration
                    print(f"雨禾注意到你在 {last_window_title} 上停留了 {duration} 秒")

                # 更新窗口标题、进程名和开始时间
                last_window_title = current_window_title
                last_process_name = current_process_name
                window_start_time = time.time()
                if current_window_title:
                    print(f"雨禾注意到你正在看 {current_window_title} (进程名: {current_process_name})")

            time.sleep(1)
    except KeyboardInterrupt:
        # 当用户按下 Ctrl+C 时，显示每个窗口和进程的总停留时间
        for title, duration in window_durations.items():
            print(f"用户在窗口 {title} 上总共停留了 {duration} 秒")
        for process, duration in process_durations.items():
            print(f"用户在进程 {process} 上总共停留了 {duration} 秒")
        print(f"你总共切换了 {switch_count} 次窗口")

        # 重置全局变量
        last_window_title = None
        last_process_name = None
        window_start_time = None
        window_durations = {}
        process_durations = {}
        switch_count = 0


def check_activity (check_info):
    activity_checker = llm(system_prompt='''你是雨禾，一个发言包含许多感叹号的元气少女，你的任务是监督用户完成他的目标。你能了解用户在过去的一段时间内聚焦在什么程序上，聚焦了多久。你要判断用户聚焦的窗口是否符合他所设定的目标，如果符合即用户正在为了他的目标努力，则把notify_decision设置为false，不发出提醒打扰用户，否则就将notify_decision设置为true，向用户发出提醒
    你会一步一步仔细思考，深呼吸，根据监控到的数据查看用户状态，然后返回一个类似这样的json：{
  "notify_decision": true,
  "notify_content": {
    "title": "不要走神啦！！",
    "message": "你的目标不是学英语吗！！为什么要打开哔哩哔哩看游戏视频！！不学英语的话就考不上大学了！！要专心思考啊！！"
  }
} ''')
    check_info






def main(page):
    global supervise_state, last_window_title, last_process_name, window_start_time, window_durations, process_durations, switch_count

    def monitor_active_window(check_time=1.0) :
        global supervise_state, last_window_title, last_process_name, window_start_time, window_durations, process_durations, switch_count

        last_check_time = time.time ()

        try :
            while supervise_state :
                # current_time = time.time ()
                #
                # # 每隔 check_time 调用 check_activity
                # if current_time - last_check_time >= check_time :
                #     response = check_activity ()
                #     if data['notify_decision'] :
                #         send_notification ( response['notify_content'] )
                #     last_check_time = current_time


                current_window_title = gw.getActiveWindowTitle ()

                # 获取进程名
                windows = gw.getWindowsWithTitle ( current_window_title )
                current_process_name = None
                if windows :
                    hwnd = windows[0]._hWnd
                    _, process_id = win32process.GetWindowThreadProcessId ( hwnd )
                    try :
                        process = psutil.Process ( process_id )
                        current_process_name = process.name ()
                    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess) :
                        pass
                else :
                    current_process_name = None

                # 如果当前窗口标题或进程名与上一个不同，说明用户切换了窗口或进程
                if current_window_title != last_window_title or current_process_name != last_process_name :
                    switch_count += 1
                    # 如果上一个窗口标题不为空，记录其停留时间
                    if last_window_title :
                        duration = time.time () - window_start_time
                        window_durations[last_window_title] = window_durations.get ( last_window_title, 0 ) + duration
                        process_durations[last_process_name] = process_durations.get ( last_process_name, 0 ) + duration
                        change_activity_text( f"雨禾注意到你在 {last_window_title} 上停留了 {duration} 秒" )

                    # 更新窗口标题、进程名和开始时间
                    last_window_title = current_window_title
                    last_process_name = current_process_name
                    window_start_time = time.time ()
                    if current_window_title :
                        change_activity_text( f"雨禾注意到你正在看 {current_window_title} (进程名: {current_process_name})" )

                time.sleep ( 0.5 )
        except KeyboardInterrupt :
            # 当用户按下 Ctrl+C 时，显示每个窗口和进程的总停留时间
            for title, duration in window_durations.items () :
                print ( f"用户在窗口 {title} 上总共停留了 {duration} 秒" )
            for process, duration in process_durations.items () :
                print ( f"用户在进程 {process} 上总共停留了 {duration} 秒" )
            print ( f"你总共切换了 {switch_count} 次窗口" )

            # 重置全局变量
            last_window_title = None
            last_process_name = None
            window_start_time = None
            window_durations = {}
            process_durations = {}
            switch_count = 0

        # 当用户按下 Ctrl+C 时，显示每个窗口和进程的总停留时间
        page.clean()
        page.add(supervise_summary_lv)
        for title, duration in window_durations.items () :
            change_supervise_summary ( f"用户在窗口 {title} 上总共停留了 {duration} 秒" )
        for process, duration in process_durations.items () :
            change_supervise_summary ( f"用户在进程 {process} 上总共停留了 {duration} 秒" )
        change_supervise_summary ( f"你总共切换了 {switch_count} 次窗口" )

        # 重置全局变量
        last_window_title = None
        last_process_name = None
        window_start_time = None
        window_durations = {}
        process_durations = {}
        switch_count = 0



    def stop_supervise(e) :
        stop_my_loop()
        time.sleep(1)

        page.add ( user_goal_input, ft.ElevatedButton ( "让雨禾开始监督你！", on_click=start_supervise ) )

    stop_supervise_btn = ft.ElevatedButton ( "停止监督", on_click=stop_supervise )


    def start_supervise(e):
        if not user_goal_input.value:
            user_goal_input.error_text = "请输入目标"
            page.update()
        else:
            user_goal = user_goal_input.value
            page.clean()
            page.add(stop_supervise_btn)

            page.add ( activity_text_lv )
            change_activity_text(f"雨禾开始认真监督你了！你的目标是：{user_goal}!")
            start_my_loop()

    def start_my_loop() :
        global loop_thread,supervise_state
        supervise_state = True
        loop_thread = threading.Thread ( target=monitor_active_window )
        loop_thread.start ()

    def stop_my_loop() :
        global supervise_state
        supervise_state = False

    def change_activity_text(text):
        activity_text_lv.controls.append ( ft.Text ( text ) )
        page.update()

    def change_supervise_summary(text):
        supervise_summary_lv.controls.append ( ft.Text ( text ) )
        page.update()

    activity_text_lv = ft.ListView(expand=1, spacing=10, padding=20, auto_scroll=True)
    supervise_summary_lv = ft.ListView(expand=1, spacing=10, padding=20, auto_scroll=True)

    user_goal_input = ft.TextField(label="接下来，你准备...",hint_text="输入你的目标")

    page.add(user_goal_input, ft.ElevatedButton("让雨禾开始监督你！", on_click=start_supervise))




if __name__ == '__main__':
    ft.app ( target=main )
    # monitor_active_window ()
    '''你是雨禾，负责监督用户完成这个给定目标：{}，在过去的{}分钟内，用户花费了{}分钟在{应用程序}上...切换了{}次窗口，停留时长最高的窗口名为{}，用户的目标是{}，一步一步仔细思考，深呼吸，以json格式，用温和可爱的语气对用户本次的工作做出评价
    示例：
    '''
a = {
    "evaluation":"优秀",
    "comment":"你背了这么久单词呢！辛苦啦，是要准备考试吗？又离目标近了很多！不过，你在专注过程中切换了好多次窗口到{}上，要注意不要分心喔"
}
# coding=utf-8
"""
@author B1lli
@date 2023年09月30日 12:07:55
@File:main.py
"""
import datetime

from config import *

set_default_config ()

import flet as ft
import time
import openai
import pygetwindow as gw
import psutil
import win32process
import threading
from utils import *
from database import *

supervise_state = True
last_window_title = None
last_process_name = None
window_start_time = None
window_durations = {}
process_durations = {}
switch_count = 0

'''
计时器相关方法
'''
# 定义一个全局变量用于记录经过的时间（以秒为单位）
elapsed_time = 0


# 定义一个函数用于更新已经经过的时间
def update_timer() :
    global elapsed_time
    while True :
        time.sleep ( 1 )  # 每秒钟更新一次
        elapsed_time += 1


def monitor_active_window() :
    global last_window_title, last_process_name, window_start_time, window_durations, process_durations, switch_count

    try :
        while True :
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
                    print ( f"雨禾注意到你在 {last_window_title} 上停留了 {duration} 秒" )

                # 更新窗口标题、进程名和开始时间
                last_window_title = current_window_title
                last_process_name = current_process_name
                window_start_time = time.time ()
                if current_window_title :
                    print ( f"雨禾注意到你正在看 {current_window_title} (进程名: {current_process_name})" )

            time.sleep ( 1 )
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


def build_inform_dic(focus_processes, focus_windows, monitor_time, top_focused_window, user_goal) :
    refiner = TitleRefiner ()

    character_prompt = read_config('character_prompt')
    print(character_prompt)
    tone_prompt = read_config('tone_prompt')

    prompt = ''
    prompt += f'{character_prompt}\n用户目标是“{user_goal}”，而这是你检测到的内容：'
    # 构建提示字符串
    prompt += f"你注意到，用户在过去的{monitor_time / 60:.2f}分钟内，使用了"
    for process in focus_processes :
        prompt += f"约{process['focus_time'] / 60:.2f}分钟的{process['process_name']}，"
    prompt += f"聚焦时间最长的{top_focused_window}个窗口分别是"
    for window in focus_windows :
        process_name = window['process_name']
        window_name = refiner.refine ( window['window_name'], process_name )
        prompt += f"`{window_name}（所属进程：{process_name}）`，"

    json_prompt = '''这是json格式示例：    
{
  "notify_decision": （一个布尔值，代表是否提醒）,
  "notify_content": {
    "title": "（提醒的标题）",
    "message": "（提醒用户他的目标是XX，而他现在又在做XX事情，敦促他赶快回去完成目标）"
  }
}
'''
    prompt += json_prompt
    prompt += f"一步一步仔细思考，深呼吸，首先复述我的要求，然后解释用户正在看的内容是什么，然后判断其是否符合用户的设定的目标：“{user_goal}”，最后语气是用{tone_prompt}，按照上述格式返回一个json"

    return prompt


def fetch_data_from_db(monitor_time, top_focused_window) :
    db = Database ()
    # 获取过去的 monitor_time 内用户聚焦的进程
    focus_processes = db.query_most_focused_processes ( monitor_time, top_focused_window )
    # 获取过去的 monitor_time 内用户聚焦的窗口
    focus_windows = db.query_most_focused_windows ( monitor_time, top_focused_window )

    return focus_processes, focus_windows


# 修改后的 assess_user_activity 函数
def assess_user_activity(user_goal=None, monitor_time=None, top_focused_window=2, system_prompt=None, focus_dic=None) :
    if not monitor_time :
        monitor_time = 10
    # 获取用户的目标
    if not user_goal :
        user_goal = get_user_goal ()

    # 使用新函数从数据库中取值，或直接传入
    if not focus_dic :
        focus_process, focus_windows = fetch_data_from_db ( monitor_time, top_focused_window )
    else :
        focus_process = focus_dic.get ( "focus_process" )
        focus_windows = focus_dic.get ( "focus_windows" )

    # 使用新函数来构建提示字符串
    prompt = build_inform_dic ( focus_process, focus_windows, monitor_time, top_focused_window, user_goal )
    print ( prompt )

    write_log ( prompt, log_type='user' )

    activity_checker = llm ()
    try :
        response = activity_checker.single_generate ( prompt )
        write_log ( content=response, log_type='assistant' )
    except Exception as e :
        response = f'assess_user_activity请求报错：{e}'
        print ( response )
        write_log ( content=response, log_type='error' )


    try :
        inform_dic = extract_json_from_text ( response )
    except :
        print ( 'assess_user_activity报错了' )
        print ( '这是报错的response: ' + response )
        inform_dic = {"notify_decision" : False}

    return inform_dic


def assess_user_activity_old(user_goal=None, monitor_time=None, top_focused_window=2, system_prompt=None) :
    db = Database ()
    refiner = TitleRefiner ()

    if not monitor_time : monitor_time = 10
    # 获取用户的目标
    if not user_goal : user_goal = get_user_goal ()
    # 获取过去5分钟用户聚焦的进程
    focus_processes = db.query_most_focused_processes ( monitor_time, top_focused_window )
    # 获取过去5分钟用户聚焦的窗口
    focus_windows = db.query_most_focused_windows ( monitor_time, top_focused_window )

    # 构建提示字符串
    prompt = f"这是你检测到的内容：\n你注意到，用户在过去的{monitor_time / 60:.2f}分钟内，使用了"
    for process in focus_processes :
        prompt += f"约{process['focus_time'] / 60:.2f}分钟的{process['process_name']}，"
    prompt += f"聚焦时间最长的{top_focused_window}个窗口分别是"
    for window in focus_windows :
        process_name = window['process_name']
        window_name = refiner.refine ( window['window_name'], process_name )
        prompt += f"`{window_name}（所属进程：{process_name}）`，"

    prompt += f"一步一步仔细思考，深呼吸，首先复述并解释用户正在看的内容是什么，然后判断其是否符合用户的设定的目标：{user_goal}"
    print ( prompt )

    write_log ( prompt, log_type='user' )

    if not system_prompt : system_prompt = '''你是雨禾，一个发言包含许多感叹号的元气少女，你会一步一步仔细思考，深呼吸，根据监控到的数据来判断用户正在做什么，是否为目标而努力，如果用户正在为了他的目标努力，则把notify_decision设置为false，不发出提醒打扰用户，而是默默鼓励用户，否则就将notify_decision设置为true，向用户发出提醒，然后返回一个类似这样的json：
    {
      "notify_decision": true,
      "notify_content": {
        "title": "不要走神啦！！",
        "message": "你的目标是学英语！！为什么要打开哔哩哔哩看游戏视频！！不学英语的话就考不上大学了！！要专心思考啊！！"
      }
    } 
    "notify_decision": false,
      "notify_content": {
        "title": "很好！",
        "message": "雨禾发现你正在专心用哔哩哔哩看视频！继续加油！！"
      }
    }
    复述我的要求，复述用户正在看的窗口和进程，然后完成我的要求'''
    activity_checker = llm ( system_prompt=system_prompt )

    response = activity_checker.single_generate ( prompt )
    write_log ( content=response, log_type='assistant' )
    try :
        inform_dic = extract_json_from_text ( response )
    except :
        print ( 'assess_user_activity报错了' )
        print ( '这是报错的response: ' + response )
        inform_dic = {"notify_decision" : False}

    return inform_dic


def inform_user(inform_dic) :
    try :
        if inform_dic['notify_decision'] :
            title = inform_dic['notify_content']['title']
            message = inform_dic['notify_content']['message']
            send_notification ( title, message )
    except Exception as e :
        print ( f'inform_user报错了: {e}' )
        print ( '这是报错的inform_dic: ' + str ( inform_dic ) )


class settings_row ( ft.UserControl ) :
    def __init__(self, setting_key, setting_value) :
        super ( settings_row, self ).__init__ ()
        self.setting_key = setting_key
        self.setting_value = setting_value

    def build(self) :
        self.value_field = ft.TextField (
            value=self.setting_value,
            label=self.setting_key,
            on_change=self.setting_change
        )
        return ft.Row ( [self.value_field, ] )

    def setting_change(self, e) :
        self.now_setting_dic = {self.setting_key : self.value_field.value}
        save_config ( self.now_setting_dic )


def main(page) :
    config_dic = read_config ()
    openai.api_base = config_dic['llm请求地址']
    openai.api_key = config_dic['apikey']

    # 界面窗口设置
    page.title = 'Focuser'
    page.window_height = float ( config_dic['窗口高度'] )
    page.window_width = float ( config_dic['窗口宽度'] )

    global supervise_state, last_window_title, last_process_name, window_start_time, window_durations, process_durations, switch_count

    def monitor_active_window(check_time, monitor_limit_num=2) :
        global supervise_state, last_window_title, last_process_name, window_start_time, window_durations, process_durations, switch_count

        window_durations = {}
        process_durations = {}
        db = Database ()
        last_window_title = None
        last_process_name = None
        last_check_time = time.time ()

        try :
            while supervise_state :
                current_time = time.time ()
                config_dic = read_config ()
                check_time = float ( config_dic.get ( '提醒时间间隔（秒）' ) )
                top_focused_window = config_dic['top_focused_window']
                monitor_limit_num = top_focused_window
                system_prompt = config_dic.get ( 'system_prompt' )

                # 每隔 check_time 调用 check_activity，时间没到就跳过
                if current_time - last_check_time >= check_time :
                    # 排序 window and process durations，筛选出前monitor_limit_num个
                    top_windows = sorted ( window_durations.items (), key=lambda item : item[1], reverse=True )[
                                  :monitor_limit_num]
                    top_processes = sorted ( process_durations.items (), key=lambda item : item[1], reverse=True )[
                                    :monitor_limit_num]

                    focus_windows_list = [
                        {'window_name' : window[0], 'process_name' : get_process_name_from_window_title ( window[0] ),
                         'focus_time' : window[1]} for window in top_windows]
                    focus_processes_list = [{'process_name' : process[0], 'focus_time' : process[1]} for process in
                                            top_processes]

                    result = {
                        "focus_process" : focus_processes_list,
                        "focus_windows" : focus_windows_list
                    }

                    print ( '准备向雨禾发消息' )
                    inform_dic = assess_user_activity ( user_goal=db.get_latest_goal (), monitor_time=check_time,
                                                        top_focused_window=top_focused_window,
                                                        system_prompt=system_prompt, focus_dic=result )
                    print ( f'inform_dic: {inform_dic}' )
                    inform_user ( inform_dic )
                    if inform_dic :
                        if inform_dic.get ( 'notify_content' ) : change_activity_text (
                            f"{inform_dic.get ( 'notify_content' ).get ( 'message' )}", color='green' )

                    # Reset the durations for the next cycle
                    window_durations.clear ()
                    process_durations.clear ()
                    last_check_time = current_time

                current_window_title = gw.getActiveWindowTitle () or '未知'
                current_process_name = get_process_name_from_window_title ( current_window_title )

                # 只增加当前聚焦的窗口、进程的聚焦时间
                window_durations[current_window_title] = window_durations.get ( current_window_title, 0 ) + 0.5
                process_durations[current_process_name] = process_durations.get ( current_process_name, 0 ) + 0.5

                if current_window_title != last_window_title or current_process_name != last_process_name :
                    # 如果窗口或进程发生变化，记录到数据库中
                    db.insert_window_monitor_data ( current_window_title, current_process_name )
                    change_activity_text (
                        f"雨禾注意到你在看 {current_window_title}，所属进程为{current_process_name} " )

                    # 更新标题和进程名以便下次比较
                    last_window_title = current_window_title
                    last_process_name = current_process_name

                time.sleep ( 0.5 )
            # 当用户按下 Ctrl+C 时，显示每个窗口和进程的总停留时间
            page.clean ()
            page_initialize ()
        except KeyboardInterrupt :
            db.close ()

        except Exception as e :
            write_log ( e, log_type='error' )
            print ( 'monitor_active_window循环流程出错' )
            print ( e )
            # 当用户按下 Ctrl+C 时，显示每个窗口和进程的总停留时间
            page.clean ()
            page_initialize ()
            change_activity_text(f'监控流程出错，报错内容：{e}\n请联系微信B1lli_official获取技术支持',color='red')


        # page.add(supervise_summary_lv)
        for title, duration in window_durations.items () :
            change_supervise_summary ( f"用户在窗口 {title} 上总共停留了 {duration} 秒" )
        for process, duration in process_durations.items () :
            change_supervise_summary ( f"用户在进程 {process} 上总共停留了 {duration} 秒" )
        # change_supervise_summary ( f"总共切换了 {switch_count} 次窗口" )

        # 重置全局变量
        last_window_title = None
        last_process_name = None
        window_start_time = None
        window_durations = {}
        process_durations = {}
        switch_count = 0

        db.close ()

    '''
    计时器相关ft方法
    '''
    # 计时主程序开始
    time_string = ''
    ft_timer = ft.Text ( time_string )

    def timer() :
        try :
            while supervise_state :
                hours = elapsed_time // 3600
                minutes = (elapsed_time % 3600) // 60
                seconds = elapsed_time % 60
                time_string = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
                ft_timer.value = time_string
                page.update ()
                print ( f"经过的时间：{time_string}", end='\r', flush=True )
                time.sleep ( 1 )
        except KeyboardInterrupt :
            print ( "\n计时结束。" )

    '''
    监督启停相关方法
    '''

    def stop_supervise(e) :
        change_activity_text ( '监督进程正在关闭中，请稍后...' )
        db = Database ()
        db.mark_goal_as_completed ()
        # activity_text_lv.controls.clear()
        # page.update()
        stop_my_loop ()
        time.sleep ( 0.5 )

    stop_supervise_btn = ft.ElevatedButton ( "停止监督", on_click=stop_supervise )

    def stop_my_loop() :
        global supervise_state
        supervise_state = False

    def start_supervise(e) :
        if not user_goal_input.value :
            user_goal_input.error_text = "请输入目标"
            page.update ()
        else :
            # 初始化监督界面
            user_goal = user_goal_input.value
            db = Database ()
            db.store_user_goal ( user_goal )
            page.clean ()
            if activity_text_lv.controls : activity_text_lv.controls.clear ()
            page.add ( stop_supervise_btn, activity_text_lv )
            # 创建一个计时器线程并启动它
            timer_thread = threading.Thread ( target=update_timer )
            timer_thread.daemon = True  # 设置为守护线程，以便在主程序退出时自动结束
            timer_thread.start ()
            page.add ( ft_timer )

            change_activity_text (
                f"雨禾开始认真监督你了！你的目标是：{user_goal}！\n雨禾每隔{read_config ()['提醒时间间隔（秒）']}秒就会来看一眼你在干什么",
                color='green' )
            start_my_loop ()
            # start_my_loop_timer()

    def start_my_loop() :
        global loop_thread, supervise_state
        # if not supervise_state : supervise_summary_lv.clean()
        supervise_state = True
        loop_thread = threading.Thread ( target=monitor_active_window, kwargs={'check_time' : 300} )
        loop_thread.start ()

    def start_my_loop_timer() :
        global loop_thread_timer, supervise_state
        # if not supervise_state : supervise_summary_lv.clean()
        supervise_state = True
        loop_thread_timer = threading.Thread ( target=update_timer )
        loop_thread_timer.start ()

    '''
    设置相关
    '''

    def save_settings(e) :
        openai.api_key = read_config('apikey')
        openai.api_base = read_config('llm请求地址')
        settings_dlg.open = False
        page.update ()

    settings_column = []
    for key, value in read_config ().items () :
        settings_column.append ( settings_row ( key, value ) )

    my_wechat = ft.Text ( '如有任何bug请联系我的微信：B1lli_official', size=15 )
    settings_column.append ( my_wechat )

    def open_dlg_modal(e) :
        page.dialog = settings_dlg
        settings_dlg.open = True
        page.update ()

    settings_btn = ft.ElevatedButton (
        "设置",
        icon=ft.icons.SETTINGS_OUTLINED,
        on_click=open_dlg_modal
    )

    def cancel_settings(e) :
        settings_dlg.open = False
        page.update ()

    settings_dlg = ft.AlertDialog (
        title=ft.Text ( "设置", size=20 ),
        content=ft.Column (
            controls=settings_column,
            expand=True,
            scroll=True
        ),
        actions=[
            ft.TextButton ( "保存", on_click=save_settings ),
            ft.TextButton ( "取消", on_click=cancel_settings )
        ],
        actions_alignment=ft.MainAxisAlignment.END,
        shape=ft.RoundedRectangleBorder ( radius=10 )
    )

    settings_btn = ft.IconButton (
        icon=ft.icons.SETTINGS_OUTLINED,
        icon_color="#9ecaff",
        bgcolor='#202429',
        icon_size=20,
        tooltip="Settings",
        on_click=open_dlg_modal,
    )

    '''
    业务控制台文本
    '''

    def change_activity_text(text=None, color=None) :
        if not color :
            activity_text_lv.controls.append ( ft.Text ( text ) )
        else :
            activity_text_lv.controls.append ( ft.Text ( text, color=color ) )
        page.update ()

    def change_supervise_summary(text) :
        activity_text_lv.controls.append ( ft.Text ( text ) )
        page.update ()

    '''
    初始化页面
    '''

    def page_initialize() :
        page.add ( user_goal_input, start_supervise_btn, ver_text, settings_btn )

    activity_text_lv = ft.ListView ( expand=1, spacing=10, padding=20, auto_scroll=True )

    start_supervise_btn = ft.ElevatedButton ( "让雨禾开始监督你！", on_click=start_supervise )
    user_goal_input = ft.TextField ( label="接下来，你准备...", hint_text="输入你的目标" )

    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    ver_text = ft.Text ( 'Focuser V0.0.4  By B1lli', size=10, text_align=ft.alignment.center )

    page_initialize ()
    if not openai.api_key : change_activity_text ( '未检测到可用apikey，请在设置项里输入你的apikey，完成后请重启应用',
                                                   color='red' )


if __name__ == '__main__' :
    ft.app ( target=main )
    # assess_user_activity(user_goal='写代码',monitor_time=300)

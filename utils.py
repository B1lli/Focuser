# coding=utf-8
"""
@author B1lli
@date 2023年09月30日 13:49:18
@File:utils.py
"""
import json
import openai
from plyer import notification
import pygetwindow as gw
import psutil
import win32process
import time
import re
from config import *

config_dic = read_config ()


openai.api_base = config_dic.get('llm请求地址')
openai.api_key = config_dic.get('apikey')

import os
import datetime


def write_log(content, log_type=None) :
    # 获取AppData/Local路径
    appdata_path = os.environ.get ( 'LOCALAPPDATA' )
    focuser_dir = os.path.join ( appdata_path, 'Focuser' )

    # 确保目录存在
    if not os.path.exists ( focuser_dir ) :
        os.makedirs ( focuser_dir )

    log_file = os.path.join ( focuser_dir, 'log.txt' )

    # 获取当前时间并格式化
    current_time = datetime.datetime.now ().strftime ( '%Y-%m-%d %H:%M:%S' )

    # 构建要写入的内容
    log_content = f"{current_time}\n类型：{log_type}\n{content}\n"

    # 写入文件
    with open ( log_file, 'a',encoding='utf-8' ) as file :
        file.write ( log_content )


# 使用方式:
# write_log('你的内容', '你的类型')


def send_notification(title, message):
    """
    发送Windows通知

    参数:
        title (str): 通知的标题
        message (str): 通知的内容
    """
    try:
        notification.notify(
            title=title,
            message=message,
            app_name="YourAppName",  # 你可以替换为你的应用名称
            timeout=10  # 通知显示的时间（秒）
        )
    except Exception as e:
        error = f'send_notification报错了: {e}'
        write_log(error,log_type='error')
        print(error)

def decode_chr(s):
    if type(s) != str:print(f'本次decode_chr类型非str，为{type(s)}')
    s = str(s)
    s = s.replace('\\\\','\\')
    pattern = re.compile(r'(\\u[0-9a-fA-F]{4}|\n)')
    result = ''
    pos = 0
    while True:
        match = pattern.search(s, pos)
        if match is None:
            break
        result += s[pos:match.start()]
        if match.group() == '\n':
            result += '\n'
        else:
            result += chr(int(match.group()[2:], 16))
        pos = match.end()
    result += s[pos:]
    return result


class llm():
    def __init__(self,system_prompt=None,model='gpt-3.5-turbo-0613'):
        self.system_prompt = system_prompt
        self.model = model

    def single_generate(self, user_query, decode=True):
        '''
        单次生成回复，用于种种只需要单轮上下文的调用场景
        :param user_query: content
        :return: content
        '''
        messages = []
        if self.system_prompt:messages.append({"role" : "system", "content" : self.system_prompt})
        messages.append({"role" : "user", "content" : user_query})
        response = openai.ChatCompletion.create (
            model=self.model,
            messages=messages,
        )
        self.single_generate_content = response["choices"][0]["message"]['content']
        if decode :
            self.single_generate_content = decode_chr ( self.single_generate_content )
            return self.single_generate_content
        return self.single_generate_content

    def custom_generate(self,messages,decode=True):
        '''
        自定义生成，需要组装好message上下文传进去，返回给你的也是message
        :param messages:message
        :return:message
        '''
        response = openai.ChatCompletion.create (
            model=self.model,
            messages=messages,
        )
        if decode:
            response["choices"][0]["message"]['content'] = decode_chr(response["choices"][0]["message"]['content'])
            return response["choices"][0]["message"]
        return response["choices"][0]["message"]

    def stream_generate(self, messages, decode=True) :
        '''
        流式传输
        :param messages: message
        :param decode: bool，是否返回解码文字
        :return: 流式传输的content
        用法：
        life_messages = [{"role" : "user", "content" : "你好"}]
        for age_event_delta in life_generator.stream_generate ( life_messages ) :
            age_event_delta_lst.append ( age_event_delta )
            print ( age_event_delta, end='' )
        '''
        completion = openai.ChatCompletion.create (
            model="gpt-3.5-turbo",
            messages=messages,
            stream=True
        )

        if decode :
            return self._stream_generate_decoded ( completion )
        else :
            return self._stream_generate_raw ( completion )

    def _stream_generate_decoded(self, completion) :
        for chunk in completion :
            try :
                if chunk.choices[0].delta :
                    yield decode_chr ( chunk.choices[0].delta.content )
            except Exception as e :
                print ( e )
                continue

    def _stream_generate_raw(self, completion) :
        for chunk in completion :
            try :
                if chunk.choices[0].delta :
                    yield chunk.choices[0].delta.content
            except Exception as e :
                print ( e )
                continue


def extract_json_from_text(text):
    """
    从文本中解析JSON并转换为字典。

    :param text: 输入的长文本
    :return: 如果找到并成功解析JSON，则返回字典；否则返回None
    """
    # 定义起始和结束标识符
    start_marker = '{'
    end_marker = '}'

    # 查找标识符的位置
    start_index = text.find(start_marker)
    end_index = text.rfind(end_marker)

    # 如果文本中包含标识符
    if start_index != -1 and end_index != -1 and start_index < end_index:
        json_str = text[start_index:end_index+1]
        try:
            # 尝试解析JSON
            parsed_dict = json.loads(json_str)
            return parsed_dict
        except json.JSONDecodeError:
            # 如果解析失败
            return None
    else:
        return None



def get_process_name_from_window_title(window_title):
    if not window_title:return '未知'
    windows = gw.getWindowsWithTitle(window_title)
    if not windows:
        return None

    hwnd = windows[0]._hWnd
    _, process_id = win32process.GetWindowThreadProcessId(hwnd)
    try:
        process = psutil.Process(process_id)
        return process.name()
    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
        return None


def record_duration(window_title, process_name, start_time, window_durations, process_durations):
    if window_title:
        duration = time.time() - start_time
        window_durations[window_title] = window_durations.get(window_title, 0) + duration
        process_durations[process_name] = process_durations.get(process_name, 0) + duration
    return window_durations, process_durations


def display_statistics(window_durations, process_durations, switch_count):
    for title, duration in window_durations.items():
        print(f"用户在窗口 {title} 上总共停留了 {duration} 秒")
    for process, duration in process_durations.items():
        print(f"用户在进程 {process} 上总共停留了 {duration} 秒")
    print(f"你总共切换了 {switch_count} 次窗口")


class TitleRefiner :

    def __init__(self) :
        # 对于每个进程名，在这里定义处理函数
        self.processors = {
            "msedge.exe" : self._edge_processor,
            "chrome.exe" : self._chrome_processor,
            "WeChat.exe" : self._wechat_processor,
            "QQ.exe" : self._qq_processor,
            "pycharm64.exe" : self._pycharm_processor,
            "devenv.exe" : self._devenv_processor,
        }

    def refine(self, title: str, process_name: str) -> str :
        processor = self.processors.get ( process_name )
        if processor :
            return processor ( title )
        return title

    def _edge_processor(self, title: str) -> str :
        # 从“-”之前取核心信息
        return title.split ( " -" )[0]

    def _chrome_processor(self, title: str) -> str :
        # 从“- GoogleChrome”之前取核心信息
        return title.split ( " - GoogleChrome" )[0]

    def _wechat_processor(self, title: str) -> str :
        if title == "微信" :
            return "微信聊天"
        if title == "朋友圈" :
            return "微信朋友圈"
        return f"微信聊天 - {title}"

    def _qq_processor(self, title: str) -> str :
        return f"QQ聊天 - {title}"

    def _pycharm_processor(self, title: str) -> str :
        # 取文件名但不包括后缀
        filename = title.split ( " " )[0]
        return f"Python编程中 - {filename.split ( '.' )[0]}"

    def _devenv_processor(self, title: str) -> str :
        return f"VsCode编程中 - {title.split ( ' -' )[0]}"


# 使用示例
# refiner = TitleRefiner ()
# print ( refiner.refine ( "崩坏3七周年同人放映厅 和另外 6个页面- 用户配置1-Microsoft Edge", "msedge.exe" ) )
# print ( refiner.refine ( "微信", "WeChat.exe" ) )



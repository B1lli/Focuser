# coding=utf-8
"""
@author B1lli
@date 2023年09月30日 13:38:16
@File:database.py.py
"""
import os
import sqlite3
from datetime import datetime
import time
import atexit  # 1. 导入atexit模块


class Database:
    def __init__(self, db_name="focuser_data.db"):
        """Initialize the database connection and create the tables."""
        # Determine the Appdata/Local/Focuser directory
        appdata_path = os.path.join(os.environ["LOCALAPPDATA"], "Focuser")
        if not os.path.exists(appdata_path):
            os.makedirs(appdata_path)

        # Connect to the database in that directory
        db_path = os.path.join(appdata_path, db_name)
        self.conn = sqlite3.connect(db_path)
        self.cursor = self.conn.cursor()
        self.create_tables()

        # 注册关闭数据库的函数
        atexit.register(self.close_database)  # 2. 注册函数



    def create_tables(self):
        """Create tables in the database if they don't exist."""
        create_window_monitor_table = """
        CREATE TABLE IF NOT EXISTS window_monitor (
            id INTEGER PRIMARY KEY,
            timestamp REAL NOT NULL,
            formatted_time TEXT NOT NULL,
            window_title TEXT NOT NULL,
            process_name TEXT NOT NULL,
            focus_time REAL DEFAULT 0
        );
        """
        self.conn.execute(create_window_monitor_table)
        # 修改用户目标表结构，添加完成时间和耗时字段
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS user_goals (
                id INTEGER PRIMARY KEY,
                goal TEXT,
                timestamp REAL,
                formatted_time TEXT,
                completion_time REAL DEFAULT NULL,
                duration REAL DEFAULT NULL
            )
        ''')
        self.conn.commit()

    def insert_window_monitor_data(self, window_title, process_name) :
        """Insert data into the window_monitor table."""
        if not window_title :
            window_title = 'Unknown'
        if not process_name :
            process_name = 'Unknown'

        # 获取当前的timestamp
        timestamp = time.time ()
        formatted_time = datetime.fromtimestamp ( timestamp ).strftime ( '%Y-%m-%d %H:%M:%S' )

        # 获取最后一个进程/窗口的timestamp
        cursor = self.conn.cursor ()
        cursor.execute ( "SELECT timestamp FROM window_monitor ORDER BY timestamp DESC LIMIT 1" )
        last_timestamp_row = cursor.fetchone ()

        # 如果存在上一个进程/窗口，则计算focus_time，否则设置默认值
        if last_timestamp_row :
            last_timestamp = last_timestamp_row[0]
            focus_time = timestamp - last_timestamp
        else :
            focus_time = 0  # 或其他默认值

        cursor.execute (
            "INSERT INTO window_monitor (timestamp, formatted_time, window_title, process_name, focus_time) VALUES (?, ?, ?, ?, ?)",
            (timestamp, formatted_time, window_title, process_name, focus_time) )

        self.conn.commit ()

    def close(self):
        """Close the database connection."""
        self.conn.close()

    def _query_focus_time(self, columns, group_by, limit,monitor_time):
        end_time = time.time()
        start_time = end_time - monitor_time

        cursor = self.conn.cursor()
        cursor.execute(f"""
        SELECT {', '.join(columns)}, SUM(focus_time) as total_focus_time
        FROM window_monitor 
        WHERE timestamp BETWEEN ? AND ?
        GROUP BY {group_by}
        ORDER BY total_focus_time DESC
        LIMIT ?
        """, (start_time, end_time, limit))

        return cursor.fetchall()

    def query_most_focused_windows(self, monitor_time, focus_window_num):
        '''
        返回示例：{"window_name":"ChatGPT prompt设计","process_name","msedge.exe","focus_time":"183.6"}
        '''
        rows = self._query_focus_time(['window_title', 'process_name'], 'window_title, process_name', focus_window_num,monitor_time)
        return [{"window_name": row[0], "process_name": row[1], "focus_time": row[2]} for row in rows]

    def query_most_focused_processes(self, monitor_time, focus_process_num):
        '''
        返回示例：{"process_name","msedge.exe","focus_time":"227.7"}
        '''
        rows = self._query_focus_time(['process_name'], 'process_name', focus_process_num,monitor_time)
        return [{"process_name": row[0], "focus_time": row[1]} for row in rows]

    # 新增的函数：存储用户目标
    def store_user_goal(self, goal):
        current_time = time.time()
        formatted_time = datetime.fromtimestamp(current_time).strftime('%Y-%m-%d %H:%M:%S')
        self.cursor.execute("INSERT INTO user_goals (goal, timestamp, formatted_time) VALUES (?, ?, ?)", (goal, current_time, formatted_time))
        self.conn.commit()

    # 新增的函数：获取最新的用户目标
    def get_latest_goal(self):
        self.cursor.execute("SELECT goal FROM user_goals ORDER BY timestamp DESC LIMIT 1")
        row = self.cursor.fetchone()
        if row:
            return row[0]
        return None

    # 给最新的目标打上完成时间，并计算耗时
    def mark_goal_as_completed(self) :
        # 获取最新目标的创建时间
        self.cursor.execute ( "SELECT timestamp FROM user_goals ORDER BY timestamp DESC LIMIT 1" )
        start_time = self.cursor.fetchone ()[0]

        # 计算现在的时间和耗时
        current_time = time.time ()
        duration = current_time - start_time

        # 更新数据库
        self.cursor.execute ( "UPDATE user_goals SET completion_time=?, duration=? WHERE timestamp=?",
                              (current_time, duration, start_time) )
        self.conn.commit ()

    def close_database(self):
        if self.conn:
            self.conn.close()


if __name__ == "__main__":
    db = Database()
    # Test data insertion
    db.insert_window_monitor_data("Test Window", "Test Process")
    db.close()




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
        appdata_path = get_appdata_path()

        # Connect to the database in that directory
        db_path = get_appdata_path(db_name)
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

        cursor = self.conn.cursor ()

        # 获取最后一个进程/窗口的timestamp和名称
        cursor.execute ( "SELECT timestamp, process_name FROM window_monitor ORDER BY timestamp DESC LIMIT 1" )
        last_record = cursor.fetchone ()

        # 如果存在上一个进程/窗口，则计算focus_time，并为其更新focus_time
        if last_record :
            last_timestamp, last_process_name = last_record
            focus_time = timestamp - last_timestamp
            cursor.execute (
                "UPDATE window_monitor SET focus_time = ? WHERE timestamp = ?",
                (focus_time, last_timestamp)
            )
        # 否则，为当前进程设置一个默认的focus_time
        else :
            focus_time = 0  # 或其他默认值

        # 插入当前进程的记录
        cursor.execute (
            "INSERT INTO window_monitor (timestamp, formatted_time, window_title, process_name, focus_time) VALUES (?, ?, ?, ?, ?)",
            (timestamp, formatted_time, window_title, process_name, 0)  # 将当前进程的focus_time设置为0
        )

        self.conn.commit ()

    def close(self):
        """Close the database connection."""
        self.conn.close()

    def _query_focus_time(self, columns, group_by, limit, monitor_time) :
        import time

        end_time = time.time ()
        start_time = end_time - monitor_time

        cursor = self.conn.cursor ()

        # Query data that is directly within the monitor_time range
        # print('正在检查窗口启动时间在监控时间内的项目')
        cursor.execute ( f"""
        SELECT {', '.join ( columns )}, focus_time, timestamp
        FROM window_monitor 
        WHERE timestamp BETWEEN ? AND ?
        """, (start_time, end_time) )

        direct_data = cursor.fetchall ()
        # print(direct_data)

        if not direct_data:
            # print('没有direct_data，直接取数据库内最近使用的项目')
            cursor.execute ( f"""
            SELECT {', '.join ( columns )}, focus_time, timestamp
            FROM window_monitor 
            ORDER BY timestamp DESC
            LIMIT 1
            """ )
            direct_data = cursor.fetchall ()
            # print ( direct_data )

        # Process the direct data
        processed_data = []
        for row in direct_data :
            focus_time = row[-2]
            timestamp = row[-1]
            if focus_time == 0 :
                focus_time = end_time - timestamp
            processed_data.append ( list ( row[:-2] ) + [focus_time] )




        # Query data that ended within the monitor_time range but started before it
        # print('正在检查窗口启动时间在监控时间外的项目')
        cursor.execute ( f"""
        SELECT {', '.join ( columns )}, focus_time, timestamp
        FROM window_monitor 
        WHERE (timestamp + focus_time) BETWEEN ? AND ?
        """, (start_time, end_time) )

        adjust_data = cursor.fetchall ()
        # print(adjust_data)



        # Process the adjust_data
        for row in adjust_data :
            window_start_time = row[-1]
            window_focus_time = row[-2]

            window_end_time = window_start_time + window_focus_time
            focus_time_within_monitor_time = window_end_time - start_time

            processed_data.append (list(row[:-2]) +[focus_time_within_monitor_time] )


        # print(f'加工后的数据为：\n{processed_data}')

        # Group by the required columns and sum up the focus_time
        aggregated_data = {}
        for data in processed_data :
            key = tuple ( data[:-1] )  # Using the values of the columns (except focus_time) as the key
            aggregated_data[key] = aggregated_data.get ( key, 0 ) + data[-1]

        # print(f'整合好的数据为：\n{aggregated_data}')

        # Convert the aggregated data into a list of tuples and sort based on focus_time
        sorted_data = sorted ( aggregated_data.items (), key=lambda x : x[1], reverse=True )
        # print(f'排序好的数据为：\n{sorted_data}')

        # Limit the number of rows based on the 'limit' parameter
        final_data = sorted_data[:limit]
        # print(f'排序好的数据为：\n{sorted_data}')

        # Convert the data back to the original format
        result = []
        for data, focus_time in final_data :
            result.append ( list ( data ) + [focus_time] )

        return result

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
    # db.insert_window_monitor_data("Test Window", "Test Process")
    # db.close()
    # a = db.query_most_focused_windows(monitor_time=300,focus_window_num=2)
    # print(a)
    # a = {
    #     "process": {"pycharm64.exe" : 362, "msedge.exe" : 53},
    #     "window":{"Python编程中 - Focuser":214,"Edge页面 - 编程助手":51}
    # }



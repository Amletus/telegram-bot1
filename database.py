import sqlite3
from config import DATABASE_PATH


def connect_db():
    return sqlite3.connect(DATABASE_PATH, check_same_thread=False)

# Всі запити тримаються на Отче наш!
def insert_new_task(user_id, name, task_type, complexity, end_date, description, user_assist):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute('''INSERT INTO tasks (user, name, type, complexity, end_date, disc, user_assist, closed)
                      VALUES (?, ?, ?, ?, ?, ?, ?, 0)''',
                   (user_id, name, task_type, complexity, end_date, description, user_assist))
    conn.commit()
    conn.close()


def get_task_details(task_id):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute('''SELECT t.name, t.type, t.complexity, t.end_date, t.disc, u.user_name, ua.user_name as assist_name
                      FROM tasks t
                      JOIN user u ON t.user = u.user_id
                      LEFT JOIN user ua ON t.user_assist = ua.user_id
                      WHERE t.id = ?''', (task_id,))
    task_details = cursor.fetchone()
    conn.close()
    return task_details


def update_task(task_id, field, value):
    conn = connect_db()
    cursor = conn.cursor()
    sql = f'UPDATE tasks SET {field} = ? WHERE id = ?'
    cursor.execute(sql, (value, task_id))
    conn.commit()
    conn.close()


def delete_task(task_id):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM tasks WHERE id = ?', (task_id,))
    conn.commit()
    conn.close()

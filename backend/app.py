import os, io, csv, json, time, datetime
import requests
from flask import Flask, request, jsonify, send_from_directory, Response
from flask_cors import CORS
from dotenv import load_dotenv

# 尝试导入MySQL连接器
try:
    import mysql.connector
    print("成功导入mysql.connector")
except ImportError:
    try:
        # 尝试导入PyMySQL
        import pymysql
        pymysql.install_as_MySQLdb()
        import MySQLdb as mysql
        print("使用PyMySQL作为MySQL连接器")
    except ImportError:
        print("警告: 无法导入MySQL连接器，请确保已安装mysql-connector-python或pymysql")

# ──────────────────────────────────────────────
load_dotenv()                       # 读取 .env

GPT_BASE_URL = os.getenv("GPT_BASE_URL")
GPT_MODEL    = os.getenv("GPT_MODEL")
GPT_API_KEY  = os.getenv("GPT_API_KEY")

app = Flask(__name__, static_folder="static", static_url_path="")
CORS(app)  # 允许跨域请求

# ──────────────────────────────────────────────
def db_conn():
    """简单 MySQL 连接（根用户+默认库 elderly）"""
    max_attempts = 10
    attempt = 0
    
    # 检测是否在Docker环境中
    in_docker = os.path.exists('/.dockerenv')
    
    # 连接参数
    host = "db" if in_docker else "localhost"  # Docker中使用db，直接运行使用localhost
    user = "root"
    password = "root"
    database = "elderly"
    
    print(f"尝试连接MySQL服务器 {host}...")
    
    while attempt < max_attempts:
        try:
            # 尝试使用mysql.connector
            if 'mysql.connector' in sys.modules:
                conn = mysql.connector.connect(
                    host=host, user=user, password=password, database=database,
                    connection_timeout=30  # 增加连接超时时间
                )
                print(f"使用mysql.connector连接成功，连接ID: {id(conn)}")
                return conn
            # 尝试使用MySQLdb/PyMySQL
            else:
                conn = pymysql.connect(
                    host=host, user=user, password=password, database=database,
                    connect_timeout=30  # 增加连接超时时间
                )
                print(f"使用pymysql连接成功，连接ID: {id(conn)}")
                return conn
        except Exception as e:
            attempt += 1
            print(f"数据库连接尝试 {attempt}/{max_attempts} 失败: {e}")
            
            # 如果不在Docker中，尝试创建数据库
            if not in_docker and attempt == 2:
                try:
                    print("尝试创建数据库elderly...")
                    temp_conn = pymysql.connect(host=host, user=user, password=password)
                    temp_cur = temp_conn.cursor()
                    temp_cur.execute("CREATE DATABASE IF NOT EXISTS elderly")
                    temp_conn.commit()
                    temp_cur.close()
                    temp_conn.close()
                    print("数据库创建成功!")
                except Exception as create_err:
                    print(f"创建数据库失败: {create_err}")
            
            if attempt == max_attempts:
                print("达到最大尝试次数，连接失败")
                raise
            import time
            time.sleep(3)  # 等待3秒再重试

def init_db():
    """初始化数据库表结构"""
    print("开始初始化数据库表结构...")
    try:
        conn = db_conn()
        if 'mysql.connector' in sys.modules:
            # mysql.connector需要指定参数
            cur = conn.cursor()
        else:
            # PyMySQL可以不指定参数
            cur = conn.cursor()
        
        # 聊天记录表
        print("创建聊天记录表...")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS chat_log (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT DEFAULT 1,
                user_message TEXT,
                bot_message TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                conversation_id VARCHAR(50)
            )
        """)
        
        # 用户画像表
        print("创建用户画像表...")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS user_profile (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(50),
                age INT,
                mobility_status VARCHAR(100),
                prefer_transport VARCHAR(50),
                health_notes TEXT,
                common_places TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            )
        """)
        
        # 行程记录表
        print("创建行程记录表...")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS trip_records (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT,
                start_location VARCHAR(100),
                end_location VARCHAR(100),
                transport_mode VARCHAR(50),
                start_time DATETIME,
                end_time DATETIME,
                notes TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 常用地点表
        print("创建常用地点表...")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS favorite_places (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT,
                place_name VARCHAR(100),
                address VARCHAR(255),
                category VARCHAR(50),
                frequency INT DEFAULT 1,
                last_visited DATETIME
            )
        """)
        
        # 初始用户画像（示例数据）
        print("检查是否需要创建初始用户...")
        cur.execute("SELECT COUNT(*) FROM user_profile")
        row_count = cur.fetchone()
        count = row_count[0] if isinstance(row_count, tuple) else row_count
        
        if count == 0:
            print("创建初始用户...")
            cur.execute("""
                INSERT INTO user_profile (name, age, mobility_status, prefer_transport, health_notes, common_places)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, ("张爷爷", 72, "腿脚不太方便,需要少走路", "公交车,出租车", "有高血压,每周三去医院复查", "家(青山小区),协和医院,阳光超市"))
        
        conn.commit()
        cur.close()
        conn.close()
        print("数据库初始化完成!")
        
    except Exception as e:
        print(f"初始化数据库出错: {e}")
        traceback.print_exc()
        raise

# ───────────────────── 导入需要的系统模块 ───────────────────
import sys
import traceback

# 初始化数据库
try:
    init_db()
except Exception as e:
    print(f"警告: 数据库初始化失败: {e}")
    print("系统将尝试在接收请求时再次初始化数据库")

# ──────────────────────── 首页 ────────────────
@app.route("/")
def home():
    return send_from_directory("static", "index.html")

# ────────────────── 获取用户画像 ───────────────
@app.route("/api/user_profile", methods=["GET"])
def get_user_profile():
    user_id = request.args.get("user_id", 1)
    
    conn = db_conn()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM user_profile WHERE id = %s", (user_id,))
    profile = cur.fetchone()
    cur.close()
    conn.close()
    
    if profile:
        return jsonify(profile)
    else:
        return jsonify({"error": "用户不存在"}), 404

# ────────────────── 更新用户画像 ───────────────
@app.route("/api/user_profile", methods=["POST"])
def update_user_profile():
    """更新用户个人资料"""
    try:
        data = request.json
        print(f"收到的用户资料更新请求: {data}")
        
        # 验证必要字段
        if "id" not in data:
            return jsonify({"success": False, "error": "缺少用户ID"}), 400
        
        user_id = data.get("id")
        name = data.get("name", "")
        age = data.get("age", 0)
        mobility_status = data.get("mobility_status", "行动正常")
        prefer_transport = data.get("prefer_transport", "公交车")
        health_notes = data.get("health_notes", "")
        
        # 连接数据库
        conn = db_conn()
        cur = conn.cursor()
        
        # 检查用户是否存在
        cur.execute("SELECT id FROM user_profile WHERE id = %s", (user_id,))
        exists = cur.fetchone()
        
        if exists:
            # 更新用户信息
            cur.execute("""
                UPDATE user_profile 
                SET name = %s, age = %s, mobility_status = %s, prefer_transport = %s, health_notes = %s, updated_at = NOW()
                WHERE id = %s
            """, (name, age, mobility_status, prefer_transport, health_notes, user_id))
        else:
            # 创建新用户
            cur.execute("""
                INSERT INTO user_profile 
                (id, name, age, mobility_status, prefer_transport, health_notes, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, NOW(), NOW())
            """, (user_id, name, age, mobility_status, prefer_transport, health_notes))
        
        conn.commit()
        print(f"用户资料更新成功, 用户ID: {user_id}")
        
        cur.close()
        conn.close()
        
        return jsonify({"success": True})
        
    except Exception as e:
        print(f"更新用户资料出错: {e}")
        traceback.print_exc()  # 打印完整的错误堆栈
        try:
            if 'cur' in locals() and cur:
                cur.close()
            if 'conn' in locals() and conn:
                conn.close()
        except:
            pass
        return jsonify({"success": False, "error": str(e)}), 500

# ───────────────────── 获取用户行程 ───────────────
@app.route("/api/trips", methods=["GET"])
def get_trips():
    user_id = request.args.get("user_id", 1)
    
    conn = db_conn()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM trip_records WHERE user_id = %s ORDER BY start_time DESC LIMIT 10", (user_id,))
    trips = cur.fetchall()
    cur.close()
    conn.close()
    
    return jsonify(trips)

# ───────────────────── 记录新行程 ───────────────
@app.route("/api/trips", methods=["POST"])
def add_trip():
    data = request.json
    required_fields = ["user_id", "start_location", "end_location", "transport_mode"]
    
    # 检查必填字段
    for field in required_fields:
        if field not in data:
            return jsonify({"error": f"缺少必填字段: {field}"}), 400
    
    conn = db_conn()
    cur = conn.cursor()
    
    # 插入行程记录
    cur.execute("""
        INSERT INTO trip_records 
        (user_id, start_location, end_location, transport_mode, start_time, end_time, notes)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, (
        data.get("user_id", 1),
        data.get("start_location"),
        data.get("end_location"),
        data.get("transport_mode"),
        data.get("start_time", datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        data.get("end_time"),
        data.get("notes", "")
    ))
    
    conn.commit()
    new_id = cur.lastrowid
    cur.close()
    conn.close()
    
    # 添加行程后自动分析常用地点
    try:
        requests.post(
            f"http://localhost:8000/api/analyze_places",
            headers={"Content-Type": "application/json"},
            data=json.dumps({"user_id": data.get("user_id", 1)}),
            timeout=1  # 非阻塞调用，不等待结果
        )
    except:
        # 忽略错误，不影响主流程
        pass
    
    return jsonify({"success": True, "id": new_id})

# ───────────────────── 查询常用地点 ───────────────
@app.route("/api/places", methods=["GET"])
def get_places():
    user_id = request.args.get("user_id", 1)
    
    conn = db_conn()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM favorite_places WHERE user_id = %s ORDER BY frequency DESC", (user_id,))
    places = cur.fetchall()
    cur.close()
    conn.close()
    
    return jsonify(places)

# ───────────────────── GPT 出行规划接口 ───────────
@app.route("/api/trip_planning", methods=["POST"])
def trip_planning():
    """处理出行规划请求"""
    data = request.json
    user_id = data.get("user_id", 1)
    destination = data.get("destination", "")
    purpose = data.get("purpose", "")
    preferred_time = data.get("preferred_time", "")
    
    if not destination:
        return jsonify({"error": "缺少目的地信息"}), 400
    
    # 获取用户资料
    conn = db_conn()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM user_profile WHERE id = %s", (user_id,))
    profile = cur.fetchone() or {}
    
    # 构建系统提示
    system_prompt = """你是一位经验丰富、非常耐心的老年人出行助手。请根据老年人的信息和需求，提供最适合的出行方案。
输出格式要点：
1. 使用清晰、简洁的语言，就像家人在说话一样
2. 给出1-2条推荐路线，并简要解释推荐理由
3. 将重要信息使用**加粗**显示
4. 总字数控制在120字以内，避免信息过载
5. 使用清晰的分段和标题，方便阅读

必须使用以下Markdown格式：
**推荐路线一：[交通方式]**

- [具体路线步骤1]
- [具体路线步骤2]

**推荐理由：**[简短理由]

尽量具体说明路线，包括车站名、路程时间和注意事项。
"""
    
    # 构建用户指令
    user_prompt = f"""
    用户信息:
    - 姓名: {profile.get('name', '老年用户')}
    - 年龄: {profile.get('age', 70)}岁
    - 身体状况: {profile.get('mobility_status', '行动正常')}
    - 偏好交通方式: {profile.get('prefer_transport', '公交车')}
    - 健康信息: {profile.get('health_notes', '')}
    
    出行需求:
    - 目的地: {destination}
    - 目的: {purpose}
    - 期望出行时间: {preferred_time}
    
    请为我规划前往{destination}的最佳路线，考虑我的健康状况、交通偏好和时间要求。给出1-2条具体路线推荐，包括交通方式、预计时间、换乘点等关键信息。
    """
    
    try:
        # 调用OpenAI API
        payload = json.dumps(
            {
                "model": GPT_MODEL,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ]
            },
            ensure_ascii=False
        ).encode("utf-8")
        
        r = requests.post(
            f"{GPT_BASE_URL}/chat/completions", 
            headers={
                "Authorization": f"Bearer {GPT_API_KEY}",
                "Content-Type": "application/json; charset=utf-8",
            },
            data=payload
        )
        r.raise_for_status()
        
        # 提取回复
        plan = r.json()["choices"][0]["message"]["content"]
        
        # 创建一个新对话
        conversation_id = "trip_" + str(int(time.time()))
        
        # 保存到对话记录
        cur.execute(
            "INSERT INTO chat_log (user_id, conversation_id, user_message, bot_message) VALUES (%s, %s, %s, %s)",
            (user_id, conversation_id, f"请帮我规划去{destination}的路线，目的是{purpose}，时间是{preferred_time}", plan)
        )
        conn.commit()
        
        cur.close()
        conn.close()
        
        return jsonify({
            "success": True, 
            "plan": plan,
            "conversation_id": conversation_id
        })
        
    except Exception as e:
        print(f"规划出行出错: {e}")
        try:
            if cur:
                cur.close()
            if conn:
                conn.close()
        except:
            pass
        return jsonify({"success": False, "error": str(e)}), 500

# ───────────────────── GPT 对话接口 ───────────
@app.route("/api/chat", methods=["POST"])
def chat():
    """处理用户聊天请求"""
    data = request.json
    message = data.get("message", "")
    user_id = data.get("user_id", 1)
    conversation_id = data.get("conversation_id", "chat_" + str(int(time.time())))
    
    # 获取用户资料
    conn = db_conn()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM user_profile WHERE id = %s", (user_id,))
    profile = cur.fetchone() or {}
    
    # 获取历史对话（最多10条）
    cur.execute(
        "SELECT user_message, bot_message FROM chat_log WHERE conversation_id = %s ORDER BY id DESC LIMIT 10",
        (conversation_id,)
    )
    history = cur.fetchall()
    
    # 构建对话历史
    chat_history = []
    for msg in reversed(history):
        chat_history.append({"role": "user", "content": msg["user_message"]})
        chat_history.append({"role": "assistant", "content": msg["bot_message"]})
    
    # 构建系统提示
    system_prompt = f"""你是一位经验丰富、非常耐心的老年人出行助手。你需要提供清晰、简洁、友好的回答，适合老年人理解。
注意:
1. 回复必须简短清晰，总字数控制在80-100字以内
2. 使用简单直接的语言，像跟家人聊天一样
3. 重要信息使用**加粗**显示
4. 分段要清晰，每段不超过2行
5. 避免专业术语，使用老年人熟悉的表达

用户信息:
- 姓名: {profile.get('name', '老年用户')}
- 年龄: {profile.get('age', 70)}岁
- 身体状况: {profile.get('mobility_status', '行动正常')}
- 出行偏好: {profile.get('prefer_transport', '公交车')}
"""
    
    # 构建完整消息列表
    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(chat_history)
    messages.append({"role": "user", "content": message})
    
    try:
        # 调用OpenAI API
        payload = json.dumps(
            {
                "model": GPT_MODEL,
                "messages": messages
            },
            ensure_ascii=False
        ).encode("utf-8")
        
        r = requests.post(
            f"{GPT_BASE_URL}/chat/completions", 
            headers={
                "Authorization": f"Bearer {GPT_API_KEY}",
                "Content-Type": "application/json; charset=utf-8",
            },
            data=payload
        )
        r.raise_for_status()
        
        # 提取回复
        reply = r.json()["choices"][0]["message"]["content"]
        
        # 保存到数据库
        cur.execute(
            "INSERT INTO chat_log (user_id, conversation_id, user_message, bot_message) VALUES (%s, %s, %s, %s)",
            (user_id, conversation_id, message, reply)
        )
        conn.commit()
        
        cur.close()
        conn.close()
        
        # 每累积10条消息触发一次地点分析
        message_count = len(history) + 1
        if message_count % 10 == 0:
            try:
                requests.post(
                    f"http://localhost:8000/api/analyze_places",
                    headers={"Content-Type": "application/json"},
                    data=json.dumps({"user_id": user_id}),
                    timeout=1  # 非阻塞调用，不等待结果
                )
            except:
                # 忽略错误，不影响主流程
                pass
        
        return jsonify({"reply": reply, "conversation_id": conversation_id})
        
    except Exception as e:
        print(f"调用ChatGPT API出错: {e}")
        try:
            if cur:
                cur.close()
            if conn:
                conn.close()
        except:
            pass
        return jsonify({"error": str(e)}), 500

# ───────────────────── CSV 导出 ───────────────
@app.route("/api/export")
def export():
    conn = db_conn()
    cur = conn.cursor()
    cur.execute("SELECT user_message, bot_message, timestamp FROM chat_log ORDER BY id DESC LIMIT 100")
    rows = cur.fetchall()
    cur.close()
    conn.close()

    # 生成内存中的 CSV
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["用户消息", "助手回复", "时间"])
    writer.writerows(rows)
    buf.seek(0)

    return Response(
        buf.read(),
        mimetype="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=chatlog.csv"},
    )

# ───────────────────── 分析常用地点 ───────────────
@app.route("/api/analyze_places", methods=["POST"])
def analyze_places():
    """分析聊天记录和行程记录，自动提取常用地点"""
    user_id = request.json.get("user_id", 1)
    force_refresh = request.json.get("force_refresh", False)
    timestamp = request.json.get("timestamp", int(time.time()))
    
    print(f"收到分析常用地点请求，用户ID: {user_id}, 强制刷新: {force_refresh}, 时间戳: {timestamp}")
    
    conn = None
    cur = None
    
    try:
        # 获取用户的聊天记录
        conn = db_conn()
        cur = conn.cursor(dictionary=True)
        
        # 先检查用户是否存在，不存在则创建
        cur.execute("SELECT id FROM user_profile WHERE id = %s", (user_id,))
        user_exists = cur.fetchone()
        
        if not user_exists:
            print(f"用户 {user_id} 不存在，创建新用户")
            cur.execute("""
                INSERT INTO user_profile 
                (id, name, created_at, updated_at)
                VALUES (%s, '新用户', NOW(), NOW())
            """, (user_id,))
            conn.commit()
        
        # 获取最近的行程记录，特别关注最新添加的
        cur.execute("""
            SELECT end_location, purpose, start_time, created_at 
            FROM trip_records 
            WHERE user_id = %s 
            ORDER BY created_at DESC
            LIMIT 20
        """, (user_id,))
        trip_records = cur.fetchall()
        
        # 记录最新添加的行程，确保它们在分析中被优先考虑
        recent_trips = []
        for i, trip in enumerate(trip_records):
            if i < 3:  # 最近3条行程
                location = trip.get("end_location", "")
                if location and location.strip():
                    recent_trips.append(location.strip())
        
        print(f"获取到{len(trip_records)}条行程记录，最新3条: {recent_trips}")
        
        # 获取用户的聊天记录
        cur.execute("SELECT user_message, bot_message FROM chat_log WHERE user_id = %s ORDER BY id DESC LIMIT 50", (user_id,))
        chat_history = cur.fetchall()
        
        # 检查是否有足够的聊天记录或行程记录
        if not chat_history and not trip_records:
            # 如果没有足够的数据，返回一些预设的地点
            default_places = "家(住所),附近医院(医疗),社区超市(购物),城市公园(休闲)"
            
            # 更新用户画像
            cur.execute(
                "UPDATE user_profile SET common_places = %s, updated_at = NOW() WHERE id = %s",
                (default_places, user_id)
            )
            conn.commit()
            
            # 添加默认地点到favorite_places表
            places_array = default_places.split(',')
            for place_info in places_array:
                if '(' in place_info and ')' in place_info:
                    place_name = place_info.split('(')[0].strip()
                    category = place_info.split('(')[1].split(')')[0].strip()
                    
                    # 检查地点是否已存在
                    cur.execute(
                        "SELECT id FROM favorite_places WHERE user_id = %s AND place_name = %s",
                        (user_id, place_name)
                    )
                    exists = cur.fetchone()
                    
                    if not exists:
                        # 添加新地点
                        cur.execute(
                            "INSERT INTO favorite_places (user_id, place_name, category, frequency, last_visited) VALUES (%s, %s, %s, %s, NOW())",
                            (user_id, place_name, category, 1)
                        )
            
            conn.commit()
            
            print(f"用户 {user_id} 无聊天或行程记录，返回默认地点")
            
            if cur:
                cur.close()
            if conn:
                conn.close()
                
            return jsonify({"success": True, "places": default_places, "is_default": True})
        
        # 获取用户信息
        cur.execute("SELECT common_places FROM user_profile WHERE id = %s", (user_id,))
        user_profile = cur.fetchone()
        existing_places = user_profile.get("common_places", "") if user_profile else ""
        
        # 提取并合并聊天中提到的地点和行程目的地
        chat_messages = []
        for msg in chat_history:
            chat_messages.append(f"用户: {msg.get('user_message', '')}")
            chat_messages.append(f"助手: {msg.get('bot_message', '')}")
        
        # 构建行程数据，标记最新的行程
        trip_data = []
        for i, trip in enumerate(trip_records):
            created_time = trip.get("created_at").strftime("%Y-%m-%d %H:%M:%S") if trip.get("created_at") else ""
            trip_data.append({
                "location": trip.get("end_location", ""),
                "purpose": trip.get("purpose", ""),
                "time": created_time,
                "is_recent": True if i < 3 else False  # 标记最近3条为最新
            })
        
        # 构建改进的系统提示，强调保留具体地点名称和最新行程的重要性
        system_prompt = """你是一位地点分析专家，请从用户的聊天记录和行程历史中识别常用地点。
任务：
1. 识别用户频繁提及或前往的具体地点，保留完整名称（如"北大六院"而非简单的"医院"）
2. 为每个地点提供准确类别(医疗/购物/休闲等)
3. 最新添加的行程（标记为is_recent=true的）必须优先考虑并包含在结果中，即使只有一次记录
4. 按重要性排序，最新/最频繁访问的地点排在前面

特别注意：
- 最近添加的地点必须包含在结果中，无论出现次数多少
- 如果用户最近前往"北大六院"，分析结果里必须包含完整的"北大六院"而不是简化为"医院"
- 保留地名的特异性，不要泛化或简化地点名称

返回格式要求：
将结果以逗号分隔的字符串格式返回，格式为"具体地点名称(类别),具体地点名称(类别)"
例如："家(住所),北大六院(医疗),永辉超市(购物),中山公园(休闲)"
不要返回JSON或其他格式，只返回上述逗号分隔的字符串。
"""
        
        # 构建用户提示，特别强调最新添加的行程记录
        user_prompt = f"""
        用户的聊天记录片段:
        {json.dumps(chat_messages[-20:], ensure_ascii=False)}
        
        用户的行程记录(按时间从新到旧排序):
        {json.dumps(trip_data, ensure_ascii=False)}
        
        用户已有的常用地点: {existing_places}
        
        用户最近新添加的地点: {json.dumps(recent_trips, ensure_ascii=False)}
        
        请基于以上信息，分析出用户的常用地点。请以"地点(类别)"格式，用逗号分隔，返回5-8个最重要的地点。
        
        注意事项:
        1. 保留地点的完整具体名称（如"北大六院"而非简单的"医院"）
        2. 最近新添加的行程记录必须包含在结果中，这是最高优先级
        3. 特别是最新添加的地点：{json.dumps(recent_trips, ensure_ascii=False)}，这些必须出现在结果中
        4. 如果看到特定的地点名称（如"北大六院"），请原样保留，不要泛化为"医院"
        """
        
        # 调用ChatGPT API
        try:
            payload = json.dumps(
                {
                    "model": GPT_MODEL,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ]
                },
                ensure_ascii=False
            ).encode("utf-8")
            
            r = requests.post(
                f"{GPT_BASE_URL}/chat/completions",
                headers={
                    "Authorization": f"Bearer {GPT_API_KEY}",
                    "Content-Type": "application/json; charset=utf-8",
                },
                data=payload,
                timeout=60
            )
            r.raise_for_status()
            
            # 提取分析结果
            places_list = r.json()["choices"][0]["message"]["content"].strip()
            
            # 确保places_list不为空并包含最近添加的地点
            if not places_list:
                places_list = "家(住所),附近医院(医疗),社区超市(购物),城市公园(休闲)"
            
            # 检查最新的行程是否包含在分析结果中
            places_lower = places_list.lower()
            for recent_trip in recent_trips:
                if recent_trip.lower() not in places_lower:
                    # 如果最新行程不在结果中，手动添加
                    print(f"最新行程 '{recent_trip}' 没有在分析结果中，手动添加")
                    # 为缺失的地点添加默认类别
                    trip_with_category = f"{recent_trip}(地点)"
                    places_list = trip_with_category + "," + places_list
            
            print(f"用户 {user_id} 地点分析成功: {places_list}")
            
            # 更新用户画像中的常用地点，确保更新时间戳
            cur.execute(
                "UPDATE user_profile SET common_places = %s, updated_at = NOW() WHERE id = %s",
                (places_list, user_id)
            )
            conn.commit()
            
            # 将地点也添加到favorite_places表
            places_array = places_list.split(',')
            for place_info in places_array:
                if '(' in place_info and ')' in place_info:
                    place_name = place_info.split('(')[0].strip()
                    category = place_info.split('(')[1].split(')')[0].strip()
                    
                    # 检查地点是否已存在
                    cur.execute(
                        "SELECT id FROM favorite_places WHERE user_id = %s AND place_name = %s",
                        (user_id, place_name)
                    )
                    exists = cur.fetchone()
                    
                    if exists:
                        # 更新既有地点
                        cur.execute(
                            "UPDATE favorite_places SET category = %s, frequency = frequency + 1, last_visited = NOW() WHERE id = %s",
                            (category, exists["id"])
                        )
                    else:
                        # 添加新地点
                        cur.execute(
                            "INSERT INTO favorite_places (user_id, place_name, category, frequency, last_visited) VALUES (%s, %s, %s, %s, NOW())",
                            (user_id, place_name, category, 1)
                        )
            
            conn.commit()
            
            # 为了确保数据一致性，再次读取用户资料
            cur.execute("SELECT common_places FROM user_profile WHERE id = %s", (user_id,))
            updated_profile = cur.fetchone()
            final_places = updated_profile.get("common_places", places_list) if updated_profile else places_list
            
            if cur:
                cur.close()
            if conn:
                conn.close()
                
            return jsonify({
                "success": True, 
                "places": final_places,
                "timestamp": timestamp
            })
            
        except Exception as e:
            print(f"分析地点时API调用错误: {e}")
            # 如果API调用失败，但有最新行程，直接将其添加到现有地点中
            try:
                if recent_trips:
                    new_places = []
                    existing_places_lower = existing_places.lower() if existing_places else ""
                    
                    for trip in recent_trips:
                        if trip.lower() not in existing_places_lower:
                            new_places.append(f"{trip}(地点)")
                    
                    if new_places:
                        if existing_places:
                            updated_places = ",".join(new_places) + "," + existing_places
                        else:
                            updated_places = ",".join(new_places)
                        
                        # 更新用户画像
                        cur.execute(
                            "UPDATE user_profile SET common_places = %s, updated_at = NOW() WHERE id = %s",
                            (updated_places, user_id)
                        )
                        conn.commit()
                        
                        print(f"API调用失败，但成功添加最新行程到常用地点: {updated_places}")
                        
                        if cur:
                            cur.close()
                        if conn:
                            conn.close()
                        
                        return jsonify({"success": True, "places": updated_places, "timestamp": timestamp})
            except Exception as inner_e:
                print(f"处理失败后备选项时出错: {inner_e}")
            
            # 如果所有尝试都失败，返回默认地点
            default_places = "家(住所),附近医院(医疗),社区超市(购物),城市公园(休闲)"
            
            # 更新用户画像
            try:
                cur.execute(
                    "UPDATE user_profile SET common_places = %s, updated_at = NOW() WHERE id = %s",
                    (default_places, user_id)
                )
                conn.commit()
            except Exception as db_error:
                print(f"更新用户画像时出错: {db_error}")
                
            if cur:
                cur.close()
            if conn:
                conn.close()
                
            return jsonify({"success": True, "places": default_places, "is_default": True, "timestamp": timestamp})
    
    except Exception as e:
        print(f"分析地点时发生错误: {e}")
        traceback.print_exc()  # 打印完整的堆栈跟踪
        
        try:
            if 'cur' in locals() and cur:
                cur.close()
            if 'conn' in locals() and conn:
                conn.close()
        except:
            pass
        
        # 确保即使发生错误也返回默认地点
        default_places = "家(住所),附近医院(医疗),社区超市(购物),城市公园(休闲)"
        return jsonify({"success": True, "places": default_places, "is_default": True, "timestamp": timestamp})

# 在系统初始化时添加一个自动更新常用地点的触发器函数
def auto_analyze_places():
    """在添加新的聊天记录或行程记录后，自动分析常用地点"""
    # 这个功能可以通过定时任务或触发器在后台执行
    # 实际项目中，可以使用Flask的signals或事件监听器来实现
    pass

# ───────────────────── 数据库管理API ───────────────
@app.route("/api/admin/database", methods=["GET"])
def view_database():
    table = request.args.get("table")
    allowed_tables = ["user_profile", "chat_log", "favorite_places", "trip_records"]
    
    if not table or table not in allowed_tables:
        return jsonify({"error": "无效的表名"}), 400
    
    try:
        conn = db_conn()
        cur = conn.cursor(dictionary=True)
        
        # 限制返回记录数量防止性能问题
        limit = 50 if table == "chat_log" else 100
        cur.execute(f"SELECT * FROM {table} LIMIT {limit}")
        
        data = cur.fetchall()
        
        # 处理日期时间格式
        for row in data:
            for key, value in row.items():
                if isinstance(value, datetime.datetime):
                    row[key] = value.strftime("%Y-%m-%d %H:%M:%S")
        
        cur.close()
        conn.close()
        
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ───────────────────── 入口 ───────────────────
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)

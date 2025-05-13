# ElderlyAssistant
# 老年人智能出行助手

基于ChatGPT的老年人适老化出行服务系统，旨在通过自然语言交互方式，为老年人提供便捷、智能、安全的出行规划和辅助服务。

## 项目概述

本项目是一个基于ChatGPT大语言模型的智能出行助手系统，专为老年人设计，具有以下特点：

- **自然语言交互**：通过简单的语音或文本对话方式，降低老年人使用技术的门槛
- **个性化服务**：基于用户画像（如身体状况、出行偏好）提供定制化的出行建议
- **全流程服务**：覆盖出行前规划、途中辅助、出行后记录的全周期服务
- **适老化设计**：大字体、高对比度、简化操作的界面设计，符合老年人使用习惯
- **安全保障**：重视老年人出行安全，提供紧急情况响应机制

## 系统功能

### 核心功能

1. **智能对话问答**：基于ChatGPT的自然语言交互，解答老年人的出行相关问题
2. **出行方案规划**：根据目的地、时间、出行目的等，结合用户画像提供个性化出行建议
3. **用户画像管理**：记录并更新用户的健康状况、出行偏好、常去地点等信息
4. **行程记录管理**：保存历史出行记录，便于回顾查询

### 技术特点

- 基于Flask的轻量级后端服务
- MySQL数据库存储用户数据和交互历史
- 适老化的HTML5/JavaScript前端界面
- ChatGPT API集成，实现智能对话功能
- Docker容器化部署，简化安装和管理

## 安装与启动

本系统提供两种启动方式：Docker容器启动（推荐）和直接Python启动。

### 方式一：Docker启动（推荐）

#### 前置条件
- 安装Docker和Docker Compose

#### 启动步骤
1. 确保Docker服务已启动
2. 双击运行`start_app.bat`
3. 访问 http://localhost:8000 使用系统

或者手动执行以下命令：
```bash
docker-compose up -d
```

### 方式二：直接Python启动

#### 前置条件
- Python 3.8+
- MySQL数据库服务

#### 安装依赖
1. 双击运行`install_dependencies.bat`
   或者手动执行：
   ```bash
   pip install -r requirements.txt
   ```

#### 启动系统
1. 双击运行`start_app.bat`
   或者手动执行：
   ```bash
   python run.py
   ```
2. 访问 http://localhost:8000 使用系统

## 常见问题解决

### 1. MySQL连接问题

如果遇到MySQL连接错误（如"ModuleNotFoundError: No module named 'mysql'"），请尝试：

```bash
pip install mysql-connector-python --force-reinstall
```

### 2. Docker容器无法启动

确保Docker服务已启动，然后运行：

```bash
docker-compose down
docker-compose up -d
```

### 3. 端口占用问题

如果8000端口被占用，可以修改`run.py`文件中的端口号：

```python
app.run(host='0.0.0.0', port=8001, debug=True)  # 将8000改为其他未占用端口
```

或者在`docker-compose.yml`中修改端口映射：

```yaml
ports:
  - "8001:8000"  # 将左侧的8000改为其他未占用端口
```

## 系统配置

编辑`.env`文件以自定义系统配置：

```
GPT_BASE_URL=      # ChatGPT API基础URL
GPT_MODEL=chatgpt-4o-latest                    # 使用的ChatGPT模型
GPT_API_KEY=your_api_key_here                  # 您的API密钥
```

## 系统架构

系统由三部分组成：

1. **前端**：基于HTML5/JavaScript的适老化Web界面
2. **后端**：Flask Web服务提供API接口和业务逻辑处理
3. **数据库**：MySQL存储用户数据、对话历史和行程记录

## 使用指南

### 首次使用

1. 访问系统首页（http://localhost:8000）
2. 切换到"个人信息"标签页，填写基本信息
3. 保存个人信息后即可开始使用其他功能

### 出行规划

1. 点击"出行规划"标签页
2. 输入目的地、选择出行目的和期望出发时间
3. 点击"为我规划路线"按钮
4. 查看系统生成的个性化出行方案
5. 可选择保存此行程到历史记录

### 智能对话

1. 点击"聊天问答"标签页
2. 在输入框中输入问题或需求
3. 点击发送按钮或按回车键
4. 查看AI助手的回复

## 开发信息

- 系统版本：v1.1.3 (2024-05-07)
- 开发框架：Flask + HTML5/JavaScript
- 数据库：MySQL 8.0
- 人工智能：ChatGPT-4o
- 容器化：Docker & Docker Compose

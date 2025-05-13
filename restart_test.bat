@echo off
echo 正在重启老年人出行助手系统...
docker-compose down
docker-compose up --build -d
echo 系统已重启，请访问 http://localhost:8000 测试功能

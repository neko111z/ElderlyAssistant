FROM python:3.11-slim
ENV PYTHONUNBUFFERED=1

# 国内 PyPI 镜像 + 300 s 超时
RUN mkdir -p /etc/pip && \
    printf "[global]\nindex-url = https://pypi.tuna.tsinghua.edu.cn/simple\ndefault-timeout = 300\n" > /etc/pip.conf

WORKDIR /app
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app
CMD ["python", "app.py"]

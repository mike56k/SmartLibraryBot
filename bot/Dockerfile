FROM python:3.13-slim
# Real-time logging and no .pyc files
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /SmartLibraryBot
COPY bot ./bot/
COPY requirements.txt bot.conf bot.log ./
RUN pip install --no-cache-dir --upgrade -r ./requirements.txt
CMD ["sleep", "10000"]
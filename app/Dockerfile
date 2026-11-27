FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# add a non-root user
RUN useradd -m appuser
# switch to the non-root user
USER appuser
COPY . .
# expose the port that the app will run on
EXPOSE 8000
CMD ["python", "main.py"]
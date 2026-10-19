FROM apify/actor-python:3.12

WORKDIR /usr/src/app
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

COPY requirements.txt ./
RUN python -m pip install --no-cache-dir -r requirements.txt \
    && python -m playwright install --with-deps chromium --only-shell

COPY . ./
RUN python -m src.main --check

CMD ["python", "-u", "-m", "src.main"]

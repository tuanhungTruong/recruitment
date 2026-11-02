FROM python:3.12-slim

WORKDIR /app
COPY aggregator.py aggregator.py
COPY aggregator/ aggregator/

ENTRYPOINT ["python", "aggregator.py"]
CMD ["--help"]

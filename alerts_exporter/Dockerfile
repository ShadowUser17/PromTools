FROM python:3.9-alpine

WORKDIR /root

RUN pip3 install --no-cache prometheus-client
COPY ./alerts_exporter.py /usr/local/bin/

EXPOSE 9095/tcp

ENTRYPOINT ["/usr/local/bin/python3", "/usr/local/bin/alerts_exporter.py"]
CMD ["-l", "0.0.0.0', '-p', '9095", "-t", "http://127.0.0.1:9093"]

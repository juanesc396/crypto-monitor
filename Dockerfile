FROM python:3.11.9

WORKDIR /scripts

COPY req.txt .

RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r req.txt

CMD ["bash"]
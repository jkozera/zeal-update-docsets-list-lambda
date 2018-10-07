FROM python:3.6

RUN mkdir /zevdocs-update-docsets-lambda && apt-get update && apt-get install -qy zip
COPY update_docsets /zevdocs-update-docsets-lambda/update_docsets
COPY setup.py /zevdocs-update-docsets-lambda/setup.py
COPY deploy.sh /zevdocs-update-docsets-lambda/deploy.sh

RUN cd /zevdocs-update-docsets-lambda && ./deploy.sh ziponly

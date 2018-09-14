FROM python:2.7
MAINTAINER unknownlighter@gmail.com

RUN pip install twisted
RUN pip install pyopenssl

ADD server.py /server.py

EXPOSE 80

CMD python /server.py

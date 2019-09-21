FROM python:3.7-buster
ENTRYPOINT ["python", "/opt/code/gnotify.py"]

RUN mkdir /opt/code /var/gnotify && chown nobody:nogroup /var/gnotify

COPY requirements.txt /opt/code/
RUN pip install -U pip setuptools && pip install -r /opt/code/requirements.txt

COPY gnotify.py /opt/code

VOLUME /var/gnotify
USER nobody


FROM python:3.10-alpine
RUN mkdir /app
WORKDIR /app
ADD requirements.txt /app/
RUN pip install -r requirements.txt

COPY freaksplay/*.py /app/freaksplay/

CMD python -m freaksplay
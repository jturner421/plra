# syntax=docker/dockerfile:1
FROM python:3.7.3
RUN export DEBIAN_FRONTEND=noninteractive && \
    apt-get install -y gcc

# Create and activate virtualenv:
RUN python3 -m venv /venv
ENV PATH=/venv/bin:$PATH
ENV VIRTUAL_ENV=/venv
RUN pip install --upgrade pip
RUN pip install pipenv

WORKDIR /usr/src/app
COPY . .

# Install inside virtualenv:
RUN pip install -r requirements.txt
ENV PYTHONPATH "${PYTHONPATH}:/usr/src/app/SCCM/SCCM"
ENV PYTHONFAULTHANDLER=1

CMD ["python", "SCCM/bin/state_check_convert.py" ]
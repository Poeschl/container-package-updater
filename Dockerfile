FROM docker.io/python:3.12-slim as build

ENV PIPENV_VENV_IN_PROJECT=1
WORKDIR /action/workspace

COPY Pipfile Pipfile.lock /action/workspace/
RUN pip install pipenv && pipenv sync

FROM docker.io/python:3.12-slim as run

WORKDIR /action/workspace
ENV PYTHONPATH=/action/workspace:$PYTHONPATH

RUN apt-get update && apt-get -y --no-install-recommends install \
    git \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

COPY --from=build /action/workspace/.venv /action/workspace/.venv
COPY containerpackageupdater/*.py /action/workspace/containerpackageupdater/

ENTRYPOINT ["/action/workspace/.venv/bin/python", "/action/workspace/containerpackageupdater/main.py"]

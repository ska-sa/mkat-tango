ARG BUILD_IMAGE=artefact.skao.int/ska-build-python:0.1.1
ARG BASE_IMAGE=artefact.skao.int/ska-tango-images-tango-python:0.1.0

FROM $BUILD_IMAGE AS build

USER root
WORKDIR /home/app
COPY  . .
RUN apt update
RUN apt install pkg-config -y
RUN pip install . -U
CMD ["tail", "-f", "/dev/null"]
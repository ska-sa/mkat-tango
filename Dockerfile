FROM docker-registry.camlab.kat.ac.za/camtango_nodb_bionic:latest
WORKDIR /usr/src/app
COPY  docker
RUN python2 -m pip install . -U
CMD ["tail", "-f"]

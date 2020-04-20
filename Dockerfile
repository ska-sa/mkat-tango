FROM docker-registry.camlab.kat.ac.za/camtango_nodb_bionic:latest
WORKDIR /usr/src/app
COPY  . .
RUN python2 -m pip install . -U
RUN python3 -m pip install . -U
CMD ["tail", "-f"]

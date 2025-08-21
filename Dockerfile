FROM ubuntu:latest
LABEL authors="eytan"

ENTRYPOINT ["top", "-b"]
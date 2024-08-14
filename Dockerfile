FROM python:3.12-bookworm
LABEL maintainer="KBase Developers [engage@kbase.us]"

WORKDIR /kb/module
RUN apt-get update \
    && apt-get upgrade -y && \
    update-ca-certificates && \
    apt-get -y install xvfb curl && \
    # these are all needed by PyQt5
    apt-get -y install libdbus-1-3 libxcb-keysyms1 libxcb-image0 libxkbcommon-x11-0 libxkbcommon0 libxcb-icccm4 libxcb-image0 libxcb-render-util0 libxcb-shape0 libxcb-xinerama0 && \
    apt-get clean && \
    # Install FastTree
    mkdir -p /kb/module/FastTree/bin && \
    cd /kb/module/FastTree/bin && \
    curl -o FastTree http://www.microbesonline.org/fasttree/FastTree && \
    chmod 555 FastTree && \
    pip install --upgrade pip

COPY ./ /kb/module
# install the python requirements
RUN pip install -r requirements.txt && \
    mkdir -p /kb/module/work && \
    chmod -R a+rw /kb/module && \
    mv /kb/module/compile_report.json /kb/module/work/compile_report.json

WORKDIR /kb/module
ENTRYPOINT [ "./scripts/entrypoint.sh" ]

CMD [ ]

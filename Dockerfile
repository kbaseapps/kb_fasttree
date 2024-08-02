FROM kbase/sdkpython:3.8.10
LABEL maintainer="KBase Developers [engage@kbase.us]"

WORKDIR /kb/module
# Update
RUN apt-get update \
    && apt-get upgrade -y && \
    update-ca-certificates && \
    apt-get -y install xvfb curl && \
    # Install FastTree
    mkdir -p /kb/module/FastTree/bin && \
    cd /kb/module/FastTree/bin && \
    curl -o FastTree http://www.microbesonline.org/fasttree/FastTree && \
    chmod 555 FastTree && \
    pip install --upgrade pip && \
    # install the python requirements
    # Note: You must use PyQt5==5.11.3 on debian
    pip install ete3==3.1.2 PyQt5==5.11.3 numpy==1.23.1 pytest coverage pytest-cov vcrpy

COPY ./ /kb/module

RUN mkdir -p /kb/module/work && \
    chmod -R a+rw /kb/module && \
    mv /kb/module/compile_report.json /kb/module/work/compile_report.json

WORKDIR /kb/module
ENTRYPOINT [ "./scripts/entrypoint.sh" ]

CMD [ ]

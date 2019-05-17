FROM kbase/kbase:sdkbase2.latest
MAINTAINER KBase Developer [Dylan Chivian (DCChivian@lbl.gov)]

# -----------------------------------------
# In this section, you can install any system dependencies required
# to run your App.  For instance, you could place an apt-get update or
# install line here, a git checkout to download code, or run any other
# installation scripts.

#RUN apt-get update

# Install ETE3
#RUN apt-get -y --fix-missing install python-numpy python-qt4 python-lxml python-six
# only need qt4
#RUN apt-get -y install python-qt4
RUN apt-get update && \
    apt-get -y install xvfb python-qt4 && \
    pip install ete3==3.0.0b35

# -----------------------------------------

RUN mkdir -p /kb/module
COPY ./ /kb/module
RUN mkdir -p /kb/module/work
RUN chmod -R a+rw /kb/module
WORKDIR /kb/module
RUN make all


# Install FastTree
#
RUN mkdir -p /kb/module/FastTree/bin
WORKDIR /kb/module/FastTree/bin
#RUN curl http://www.microbesonline.org/fasttree/FastTree > FastTree2.1.9_64
RUN \
    git clone https://github.com/kbaseapps/kb_fasttree && \
    cp kb_fasttree/src/FastTree2.1.9_64 . && \
# INCLUDES ARE FAILING
#     gcc -Wall -O3 -finline-functions -funroll-loops -o FastTree2.1.9_64 -lm kb_fasttree/src/FastTree.c && \
#    cp kb_fasttree/src/FastTree2.1.9_64_DEBUG ./FastTree2.1.9_64 && \
#RUN \
#    curl https://github.com/dcchivian/kb_fasttree/blob/master/src/FastTree2.1.9_64 > FastTree2.1.9_64 && \
    chmod 555 FastTree2.1.9_64 && \
    ln -s FastTree2.1.9_64 FastTree


WORKDIR /kb/module
ENTRYPOINT [ "./scripts/entrypoint.sh" ]

CMD [ ]


FROM kbase/kbase:sdkbase.latest
MAINTAINER Dylan Chivian
# -----------------------------------------

# Insert apt-get instructions here to install
# any required dependencies for your module.


# Install ETE3
#RUN apt-get install python-numpy python-qt4 python-lxml python-six
#RUN pip install python-numpy
#RUN pip install python-qt4
#RUN sudo pip install python-qt5
#RUN pip install python-lxml
#RUN pip install python-six
#RUN pip install --upgrade ete3
RUN pip install ete3==3.0.0b35
#RUN pip install ete3



# RUN apt-get update
# -----------------------------------------

# Install SDK Module
#
RUN mkdir -p /kb/module
COPY ./ /kb/module
RUN mkdir -p /kb/module/work
WORKDIR /kb/module
RUN make


# Install FastTree
#
RUN mkdir -p /kb/module/FastTree/bin
WORKDIR /kb/module/FastTree/bin
#RUN curl http://www.microbesonline.org/fasttree/FastTree > FastTree2.1.9_64
RUN \
    git clone https://github.com/dcchivian/kb_fasttree && \
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



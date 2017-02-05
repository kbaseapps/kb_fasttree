FROM kbase/kbase:sdkbase.latest
MAINTAINER Dylan Chivian
# -----------------------------------------

# Insert apt-get instructions here to install
# any required dependencies for your module.



# Update Transform (should go away eventually)
#RUN \
#  . /kb/dev_container/user-env.sh && \
#  cd /kb/dev_container/modules && \
#  rm -rf transform && \ 
#  git clone https://github.com/kbase/transform -b develop
#
## setup the transform, but ignore errors because sample data cannot be found!
#RUN \
#  . /kb/dev_container/user-env.sh; \
#  cd /kb/dev_container/modules/transform/t/demo; \
#  python setup.py; \
#  exit 0;



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



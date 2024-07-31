FROM kbase/sdkpython:3.8.10
MAINTAINER KBase Developer [Dylan Chivian (DCChivian@lbl.gov)]

# -----------------------------------------
# In this section, you can install any system dependencies required
# to run your App.  For instance, you could place an apt-get update or
# install line here, a git checkout to download code, or run any other
# installation scripts.

# Update
RUN apt-get update

# udpate certs
RUN apt-get upgrade -y
RUN sed -i 's/\(.*DST_Root_CA_X3.crt\)/!\1/' /etc/ca-certificates.conf
RUN update-ca-certificates


# Install ETE3
RUN apt-get -y install xvfb
RUN pip install --upgrade pip
# Note: You must use PyQt5==5.11.3 on debian
RUN pip install ete3==3.1.2 PyQt5==5.11.3 numpy==1.23.1 pytest coverage pytest-cov

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
RUN curl -o FastTree http://www.microbesonline.org/fasttree/FastTree && \
    chmod 555 FastTree


WORKDIR /kb/module
ENTRYPOINT [ "./scripts/entrypoint.sh" ]

CMD [ ]

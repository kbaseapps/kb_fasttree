SERVICE = kb_fasttree
SERVICE_CAPS = kb_fasttree
SPEC_FILE = kb_fasttree.spec
URL = https://kbase.us/services/kb_fasttree
DIR = $(shell pwd)
LIB_DIR = lib
SCRIPTS_DIR = scripts
TEST_DIR = test
LBIN_DIR = bin
EXECUTABLE_SCRIPT_NAME = run_$(SERVICE_CAPS)_async_job.sh
STARTUP_SCRIPT_NAME = start_server.sh
TEST_SCRIPT_NAME = run_tests.sh
COMPILE_REPORT = ./compile_report.json

.PHONY: test

default: compile

all: build compile

compile:
	rm $(COMPILE_REPORT) || true
	KB_SDK_COMPILE_REPORT_FILE=$(COMPILE_REPORT) kb-sdk compile $(SPEC_FILE) \
		--verbose \
		--out $(LIB_DIR) \
		--plclname $(SERVICE_CAPS)::$(SERVICE_CAPS)Client \
		--jsclname javascript/Client \
		--pyclname $(SERVICE_CAPS).$(SERVICE_CAPS)Client \
		--javasrc src \
		--java \
		--pysrvname $(SERVICE_CAPS).$(SERVICE_CAPS)Server \
		--pyimplname $(SERVICE_CAPS).$(SERVICE_CAPS)Impl;

build:
	chmod +x $(SCRIPTS_DIR)/entrypoint.sh

test:
	if [ ! -f /kb/module/work/token ]; then echo -e '\nOutside a docker container please run "kb-sdk test" rather than "make test"\n' && exit 1; fi
	xvfb-run bash $(TEST_DIR)/$(TEST_SCRIPT_NAME)

clean:
	rm -rfv $(LBIN_DIR)

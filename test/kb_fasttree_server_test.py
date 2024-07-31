"""Tests for the kb_fasttree implementation."""

import json
import time
import unittest
from configparser import ConfigParser  # py3
from os import environ
from pathlib import Path

from installed_clients.WorkspaceClient import Workspace as workspaceService
from kb_fasttree.kb_fasttreeImpl import kb_fasttree

# Set a variable to refer to the test directory
TEST_BASE_DIR = Path(__file__).resolve().parent

MSA_JSON_FILE = TEST_BASE_DIR / "data" / "DsrA.MSA.json"


class kb_fasttreeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        token = environ.get("KB_AUTH_TOKEN", None)
        cls.ctx = {
            "token": token,
            "provenance": [
                {
                    "service": "kb_fasttree",
                    "method": "please_never_use_it_in_production",
                    "method_params": [],
                }
            ],
            "authenticated": 1,
        }
        config_file = environ.get("KB_DEPLOYMENT_CONFIG", None)
        cls.cfg = {}
        config = ConfigParser()
        config.read(config_file)
        for nameval in config.items("kb_fasttree"):
            cls.cfg[nameval[0]] = nameval[1]
        cls.wsURL = cls.cfg["workspace-url"]
        cls.wsClient = workspaceService(cls.wsURL, token=token)
        cls.serviceImpl = kb_fasttree(cls.cfg)

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, "wsName"):
            cls.wsClient.delete_workspace({"workspace": cls.wsName})
            print("Test workspace was deleted")

    def getWsClient(self):
        return self.__class__.wsClient

    def getWsName(self):
        if hasattr(self.__class__, "wsName"):
            return self.__class__.wsName
        suffix = int(time.time() * 1000)
        wsName = "test_kb_fasttree_" + str(suffix)
        ret = self.getWsClient().create_workspace({"workspace": wsName})
        self.__class__.wsName = wsName
        return wsName

    def getImpl(self):
        return self.__class__.serviceImpl

    def getContext(self):
        return self.__class__.ctx

    ##############
    # UNIT TESTS #
    ##############

    #### basic fasttree test
    ##
    # HIDE @unittest.skip("skipped test_kb_fasttree_run_FastTree_01()")  # uncomment to skip
    def test_kb_fasttree_run_FastTree_01(self):
        # Prepare test objects in workspace if needed using
        # self.getWsClient().save_objects({'workspace': self.getWsName(), 'objects': []})
        #
        # Run your method by
        # ret = self.getImpl().your_method(self.getContext(), parameters...)
        #
        # Check returned data with
        # self.assertEqual(ret[...], ...) or other unittest methods

        obj_basename = "fasttree"
        obj_out_name = obj_basename + "." + "test_fasttree.Tree"
        obj_out_type = "KBaseTrees.Tree"

        # MSA
        with MSA_JSON_FILE.open() as msa_json_fh:
            msa_obj = json.load(msa_json_fh)

        provenance = [{}]
        msa_info = self.getWsClient().save_objects(
            {
                "workspace": self.getWsName(),
                "objects": [
                    {
                        "type": "KBaseTrees.MSA",
                        "data": msa_obj,
                        "name": "test_MSA",
                        "meta": {},
                        "provenance": provenance,
                    }
                ],
            }
        )[0]

        [
            OBJID_I,
            NAME_I,
            TYPE_I,
            SAVE_DATE_I,
            VERSION_I,
            SAVED_BY_I,
            WSID_I,
            WORKSPACE_I,
            CHSUM_I,
            SIZE_I,
            META_I,
        ] = range(11)  # object_info tuple
        msa_ref = f"{msa_info[WSID_I]}/{msa_info[OBJID_I]}/{msa_info[VERSION_I]}"

        parameters = {
            "workspace_name": self.getWsName(),
            "desc": "test_FastTree",
            "input_ref": msa_ref,
            "output_name": obj_out_name,
            "species_tree_flag": "0",
            "intree_ref": "",
            "fastest": "0",
            "pseudo": "0",
            "gtr": "0",
            "wag": "0",
            "noml": "0",
            "nome": "0",
            "cat": "20",
            "nocat": "0",
            "gamma": "0",
        }

        ret = self.getImpl().run_FastTree(self.getContext(), parameters)[0]
        self.assertIsNotNone(ret["report_ref"])

        # check created obj
        report_obj = self.getWsClient().get_objects([{"ref": ret["report_ref"]}])[0]["data"]
        self.assertIsNotNone(report_obj["objects_created"][0]["ref"])

        created_obj_0_info = self.getWsClient().get_object_info_new(
            {"objects": [{"ref": report_obj["objects_created"][0]["ref"]}]}
        )[0]
        self.assertEqual(created_obj_0_info[NAME_I], obj_out_name)
        self.assertEqual(created_obj_0_info[TYPE_I].split("-")[0], obj_out_type)

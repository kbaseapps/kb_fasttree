"""Tests for the kb_fasttree implementation."""

import json
import logging
import sys
from configparser import ConfigParser  # py3
from datetime import datetime, timezone
from os import environ
from pathlib import Path
from unittest.mock import patch

import vcr
import vcr.request
from installed_clients.WorkspaceClient import Workspace
from kb_fasttree.kb_fasttreeImpl import kb_fasttree
from vcr.unittest import VCRTestCase

# Set a variable to refer to the test directory
TEST_BASE_DIR = Path(__file__).resolve().parent

MSA_JSON_FILE = TEST_BASE_DIR / "data" / "DsrA.MSA.json"
MSA_NAME = "test_MSA"

# initialise logging for vcrpy
logging.basicConfig()
vcr_log = logging.getLogger("vcr")
# set to INFO or DEBUG for debugging
vcr_log.setLevel(logging.WARNING)


def body_matcher(r1: vcr.request.Request, r2: vcr.request.Request) -> None:
    """Compare the body contents of two requests to work out if they are identical or not."""
    r1_body = json.loads(r1.body.decode())
    r2_body = json.loads(r2.body.decode())
    for body in [r1_body, r2_body]:
        if "id" in body:
            del body["id"]

    assert r1_body == r2_body


def check_non_zero_file_size(path: Path) -> None:
    """Assert that a file exists and that it is non-zero in size."""
    assert path.exists()
    assert path.is_file()
    assert path.stat().st_size > 0


def compare_files(file_one: Path, file_two: Path) -> None:
    """Assert that the contents of two files are identical.

    :param file_one: file to check
    :type file_one: Path
    :param file_two: expected file contents
    :type file_two: Path
    """
    contents = []
    for this_file in [file_one, file_two]:
        assert this_file.exists()
        assert this_file.is_file()
        contents.append(this_file.read_text())

    assert contents[0] == contents[1]


class kb_fasttreeTest(VCRTestCase):
    def _get_vcr(self: "kb_fasttreeTest", **kwargs):
        """Configure the VCR matcher."""
        myvcr = super(kb_fasttreeTest, self)._get_vcr(**kwargs)
        myvcr.register_matcher("body_matcher", body_matcher)
        myvcr.match_on = ["method", "scheme", "path", "body_matcher"]
        myvcr.filter_headers = ["authorization", "set-cookie"]
        myvcr.decode_compressed_response = True
        return myvcr

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
        cls.ws_client = Workspace(cls.cfg["workspace-url"], token=token)
        cls.service_impl = kb_fasttree(cls.cfg)
        # to regenerate the server responses, uncomment this line
        # and delete the `test/cassettes` folder
        # cls.run_id = datetime.now(tz=timezone.utc).strftime("%Y%m%d_%H%M%S")
        # corresponds with the data in the saved cassette and the expected output files
        cls.run_id = "20240801_204739"

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, "ws_name"):
            try:
                cls.ws_client.delete_workspace({"workspace": cls.ws_name})
            except:
                print("Workspace already deleted")
            else:
                print("Test workspace was deleted")

    def get_ws_client(self):
        return self.ws_client

    def get_ws_name(self):
        if hasattr(self, "ws_name"):
            return self.ws_name
        ws_name = f"test_kb_fasttree_{self.run_id}"
        self.get_ws_client().create_workspace({"workspace": ws_name})
        self.ws_name = ws_name
        return ws_name

    def get_impl(self):
        return self.service_impl

    def get_context(self):
        return self.ctx

    def get_msa_ref(self):
        if hasattr(self, "msa_ref"):
            return self.msa_ref

        # load the MSA file and save it as a MSA tree in KBase
        with MSA_JSON_FILE.open() as msa_json_fh:
            msa_obj = json.load(msa_json_fh)

        msa_info = self.get_ws_client().save_objects(
            {
                "workspace": self.get_ws_name(),
                "objects": [
                    {
                        "type": "KBaseTrees.MSA",
                        "data": msa_obj,
                        "name": MSA_NAME,
                        "meta": {},
                        "provenance": [{}],
                    }
                ],
            }
        )[0]
        self.msa_ref = f"{msa_info[6]}/{msa_info[0]}/{msa_info[4]}"

        return self.msa_ref

    ##############
    # UNIT TESTS #
    ##############

    def test_kb_fasttree_run_FastTree_01(self):
        print(sys.path)

        obj_out_name = "DsrA.test"
        obj_out_type = "KBaseTrees.Tree"
        msa_ref = self.get_msa_ref()
        parameters = {
            "workspace_name": self.get_ws_name(),
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

        # patch generate_run_id to return self.run_id
        with patch("kb_fasttree.fasttree.generate_run_id", return_value=self.run_id):
            ret = self.get_impl().run_FastTree(self.get_context(), parameters)[0]
            assert ret["report_ref"] is not None

            # check created obj
            report_obj = self.get_ws_client().get_objects([{"ref": ret["report_ref"]}])[0]["data"]
            assert report_obj["objects_created"][0]["ref"] is not None

            created_obj_0_info = self.get_ws_client().get_object_info_new(
                {"objects": [{"ref": report_obj["objects_created"][0]["ref"]}]}
            )[0]
            assert created_obj_0_info[1] == obj_out_name
            assert created_obj_0_info[2].split("-")[0] == obj_out_type

            # check that the expected files are in the expected places
            run_dir = Path(self.cfg["scratch"]) / self.run_id
            assert run_dir.exists()

            for sub_dir_name in ["output", "output_html"]:
                sub_dir = run_dir / sub_dir_name
                assert sub_dir.exists()

            check_non_zero_file_size(run_dir / f"{MSA_NAME}.fasta")
            compare_files(
                run_dir / f"{MSA_NAME}.fasta",
                TEST_BASE_DIR / "data" / "expected" / f"{MSA_NAME}.fasta",
            )

            file_list = {
                "output": [
                    f"{obj_out_name}{suffix}" for suffix in ["-labels.newick", ".newick", ".pdf"]
                ],
                "output_html": [
                    f"{obj_out_name}.html",
                    f"{obj_out_name}.png",
                ],  # , "output_html.zip"],
            }
            for sub_dir_name in file_list:
                for f in file_list[sub_dir_name]:
                    check_non_zero_file_size(run_dir / sub_dir_name / f)
                    if not f.endswith("pdf") and not f.endswith("png"):
                        compare_files(
                            run_dir / sub_dir_name / f,
                            TEST_BASE_DIR / "data" / "expected" / sub_dir_name / f,
                        )

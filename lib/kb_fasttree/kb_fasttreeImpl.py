# -*- coding: utf-8 -*-
# BEGIN_HEADER
import os

from kb_fasttree import fasttree

# END_HEADER


class kb_fasttree:
    """
        Module Name:
        kb_fasttree

        Module Description:
        ** A KBase module: kb_fasttree
    **
    ** This module runs FastTree to make Trees for either DNA or PROTEIN MSAs
    **
    """

    ######## WARNING FOR GEVENT USERS ####### noqa
    # Since asynchronous IO can lead to methods - even the same method -
    # interrupting each other, you must be *very* careful when using global
    # state. A method could easily clobber the state set by another while
    # the latter method is running.
    ######################################### noqa
    VERSION = "1.1.0"
    GIT_URL = "https://github.com/kbaseapps/kb_fasttree.git"
    GIT_COMMIT_HASH = "fb832abc45e39b54c266bed9165ace9ff4346a9d"

    # BEGIN_CLASS_HEADER
    # END_CLASS_HEADER

    # config contains contents of config file in a hash or None if it couldn't
    # be found
    def __init__(self, config):
        # BEGIN_CONSTRUCTOR
        self.workspace_url = config["workspace-url"]
        self.callback_url = os.environ.get("SDK_CALLBACK_URL")
        if not self.callback_url:
            raise ValueError("SDK_CALLBACK_URL not set in environment")

        self.scratch = os.path.abspath(config["scratch"])
        if not os.path.exists(self.scratch):
            os.makedirs(self.scratch)

        # END_CONSTRUCTOR
        pass

    def run_FastTree(self, ctx, params):
        """
        Method for Tree building of either DNA or PROTEIN sequences
        **
        **        input_type: MSA
        **        output_type: Tree
        :param params: instance of type "FastTree_Params" (FastTree Input
           Params) -> structure: parameter "workspace_name" of type
           "workspace_name" (** The workspace object refs are of form: ** **
           objects = ws.get_objects([{'ref':
           params['workspace_id']+'/'+params['obj_name']}]) ** ** "ref" means
           the entire name combining the workspace id and the object name **
           "id" is a numerical identifier of the workspace or object, and
           should just be used for workspace ** "name" is a string identifier
           of a workspace or object.  This is received from Narrative.),
           parameter "desc" of String, parameter "input_ref" of type
           "data_obj_ref", parameter "output_name" of type "data_obj_name",
           parameter "species_tree_flag" of Long, parameter "intree_ref" of
           type "data_obj_ref", parameter "fastest" of Long, parameter
           "pseudo" of Long, parameter "gtr" of Long, parameter "wag" of
           Long, parameter "noml" of Long, parameter "nome" of Long,
           parameter "cat" of Long, parameter "nocat" of Long, parameter
           "gamma" of Long
        :returns: instance of type "FastTree_Output" (FastTree Output) ->
           structure: parameter "report_name" of type "data_obj_name",
           parameter "report_ref" of type "data_obj_ref", parameter
           "output_ref" of type "data_obj_ref"
        """
        # ctx is the context object
        # return variables are: returnVal
        # BEGIN run_FastTree
        config = {
            "workspace_url": self.workspace_url,
            "callback_url": self.callback_url,
            "scratch": self.scratch,
        }

        returnVal = fasttree.run_fasttree(config, ctx, params)
        # END run_FastTree

        # At some point might do deeper type checking...
        if not isinstance(returnVal, dict):
            raise ValueError(
                "Method run_FastTree " + "return value returnVal " + "is not type dict as required."
            )
        # return the results
        return [returnVal]

    def status(self, ctx):
        # BEGIN_STATUS
        returnVal = {
            "state": "OK",
            "message": "",
            "version": self.VERSION,
            "git_url": self.GIT_URL,
            "git_commit_hash": self.GIT_COMMIT_HASH,
        }
        # END_STATUS
        return [returnVal]

#BEGIN_HEADER
#END_HEADER


class kb_fasttree:
    '''
    Module Name:
    kb_fasttree

    Module Description:
    ** A KBase module: kb_fasttree
**
** This module runs FastTree to make Trees for either DNA or PROTEIN MSAs
**
    '''

    ######## WARNING FOR GEVENT USERS #######
    # Since asynchronous IO can lead to methods - even the same method -
    # interrupting each other, you must be *very* careful when using global
    # state. A method could easily clobber the state set by another while
    # the latter method is running.
    #########################################
    #BEGIN_CLASS_HEADER
    #END_CLASS_HEADER

    # config contains contents of config file in a hash or None if it couldn't
    # be found
    def __init__(self, config):
        #BEGIN_CONSTRUCTOR
        #END_CONSTRUCTOR
        pass

    def run_FastTree(self, ctx, params):
        # ctx is the context object
        # return variables are: returnVal
        #BEGIN run_FastTree
        #END run_FastTree

        # At some point might do deeper type checking...
        if not isinstance(returnVal, dict):
            raise ValueError('Method run_FastTree return value ' +
                             'returnVal is not type dict as required.')
        # return the results
        return [returnVal]

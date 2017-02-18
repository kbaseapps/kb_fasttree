# -*- coding: utf-8 -*-
#BEGIN_HEADER
import os
import sys
import shutil
import hashlib
import subprocess
import requests
import re
import traceback
import uuid
from datetime import datetime
from pprint import pprint, pformat
import numpy as np
import gzip

from Bio import SeqIO
from Bio.Seq import Seq
from Bio.SeqRecord import SeqRecord
from Bio.Alphabet import generic_protein
from biokbase.workspace.client import Workspace as workspaceService
from requests_toolbelt import MultipartEncoder
from biokbase.AbstractHandle.Client import AbstractHandle as HandleService
from DataFileUtil.DataFileUtilClient import DataFileUtil as DFUClient
from KBaseReport.KBaseReportClient import KBaseReport

# silence whining
import requests
requests.packages.urllib3.disable_warnings()

import ete3  # Tree drawing package we install in Dockerfile

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

    ######## WARNING FOR GEVENT USERS ####### noqa
    # Since asynchronous IO can lead to methods - even the same method -
    # interrupting each other, you must be *very* careful when using global
    # state. A method could easily clobber the state set by another while
    # the latter method is running.
    ######################################### noqa
    VERSION = "0.0.1"
    GIT_URL = "https://github.com/kbaseapps/kb_fasttree.git"
    GIT_COMMIT_HASH = "89c087510b4a2f3bdda13e51e192c6b4c892aa77"

    #BEGIN_CLASS_HEADER
    workspaceURL = None
    shockURL = None
    handleURL = None

    FASTTREE_bin = '/kb/module/FastTree/bin/FastTree'

    # target is a list for collecting log messages
    def log(self, target, message):
        # we should do something better here...
        if target is not None:
            target.append(message)
        print(message)
        sys.stdout.flush()

    def get_single_end_read_library(self, ws_data, ws_info, forward):
        pass

    def get_feature_set_seqs(self, ws_data, ws_info):
        pass

    def get_genome_feature_seqs(self, ws_data, ws_info):
        pass

    def get_genome_set_feature_seqs(self, ws_data, ws_info):
        pass


    # Helper script borrowed from the transform service, logger removed
    #
    def upload_file_to_shock(self,
                             console,  # DEBUG
                             shock_service_url = None,
                             filePath = None,
                             ssl_verify = True,
                             token = None):
        """
        Use HTTP multi-part POST to save a file to a SHOCK instance.
        """
        self.log(console,"UPLOADING FILE "+filePath+" TO SHOCK")

        if token is None:
            raise Exception("Authentication token required!")

        #build the header
        header = dict()
        header["Authorization"] = "Oauth {0}".format(token)
        if filePath is None:
            raise Exception("No file given for upload to SHOCK!")

        dataFile = open(os.path.abspath(filePath), 'rb')
        m = MultipartEncoder(fields={'upload': (os.path.split(filePath)[-1], dataFile)})
        header['Content-Type'] = m.content_type

        #logger.info("Sending {0} to {1}".format(filePath,shock_service_url))
        try:
            response = requests.post(shock_service_url + "/node", headers=header, data=m, allow_redirects=True, verify=ssl_verify)
            dataFile.close()
        except:
            dataFile.close()
            raise
        if not response.ok:
            response.raise_for_status()
        result = response.json()
        if result['error']:
            raise Exception(result['error'][0])
        else:
            return result["data"]


    def upload_SingleEndLibrary_to_shock_and_ws (self,
                                                 ctx,
                                                 console,  # DEBUG
                                                 workspace_name,
                                                 obj_name,
                                                 file_path,
                                                 provenance,
                                                 sequencing_tech):

        self.log(console,'UPLOADING FILE '+file_path+' TO '+workspace_name+'/'+obj_name)

        # 1) upload files to shock
        token = ctx['token']
        forward_shock_file = self.upload_file_to_shock(
            console,  # DEBUG
            shock_service_url = self.shockURL,
            filePath = file_path,
            token = token
            )
        #pprint(forward_shock_file)
        self.log(console,'SHOCK UPLOAD DONE')

        # 2) create handle
        self.log(console,'GETTING HANDLE')
        hs = HandleService(url=self.handleURL, token=token)
        forward_handle = hs.persist_handle({
                                        'id' : forward_shock_file['id'], 
                                        'type' : 'shock',
                                        'url' : self.shockURL,
                                        'file_name': forward_shock_file['file']['name'],
                                        'remote_md5': forward_shock_file['file']['checksum']['md5']})

        
        # 3) save to WS
        self.log(console,'SAVING TO WORKSPACE')
        single_end_library = {
            'lib': {
                'file': {
                    'hid':forward_handle,
                    'file_name': forward_shock_file['file']['name'],
                    'id': forward_shock_file['id'],
                    'url': self.shockURL,
                    'type':'shock',
                    'remote_md5':forward_shock_file['file']['checksum']['md5']
                },
                'encoding':'UTF8',
                'type':'fasta',
                'size':forward_shock_file['file']['size']
            },
            'sequencing_tech':sequencing_tech
        }
        self.log(console,'GETTING WORKSPACE SERVICE OBJECT')
        ws = workspaceService(self.workspaceURL, token=ctx['token'])
        self.log(console,'SAVE OPERATION...')
        new_obj_info = ws.save_objects({
                        'workspace':workspace_name,
                        'objects':[
                            {
                                'type':'KBaseFile.SingleEndLibrary',
                                'data':single_end_library,
                                'name':obj_name,
                                'meta':{},
                                'provenance':provenance
                            }]
                        })[0]
        self.log(console,'SAVED TO WORKSPACE')

        return new_obj_info[0]

    #END_CLASS_HEADER

    # config contains contents of config file in a hash or None if it couldn't
    # be found
    def __init__(self, config):
        #BEGIN_CONSTRUCTOR
        self.workspaceURL = config['workspace-url']
        self.shockURL = config['shock-url']
        self.handleURL = config['handle-service-url']
        self.serviceWizardURL = config['service-wizard-url']

        self.callbackURL = os.environ.get('SDK_CALLBACK_URL')
        if self.callbackURL == None:
            raise ValueError ("SDK_CALLBACK_URL not set in environment")

        self.scratch = os.path.abspath(config['scratch'])
        # HACK!! temporary hack for issue where megahit fails on mac because of silent named pipe error
        #self.host_scratch = self.scratch
        #self.scratch = os.path.join('/kb','module','local_scratch')
        # end hack
        if not os.path.exists(self.scratch):
            os.makedirs(self.scratch)

        #END_CONSTRUCTOR
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
        #BEGIN run_FastTree

        # init
        #
        dfu = DFUClient(self.callbackURL)
        console = []
        invalid_msgs = []
        self.log(console,'Running run_FastTree with params=')
        self.log(console, "\n"+pformat(params))
        report = ''
#        report = 'Running run_FastTree with params='
#        report += "\n"+pformat(params)


        #### do some basic checks
        #
        if 'workspace_name' not in params:
            raise ValueError('workspace_name parameter is required')
        if 'input_ref' not in params:
            raise ValueError('input_ref parameter is required')
        if 'output_name' not in params:
            raise ValueError('output_name parameter is required')


        #### Get the input_ref MSA object
        ##
        try:
            ws = workspaceService(self.workspaceURL, token=ctx['token'])
            objects = ws.get_objects([{'ref': params['input_ref']}])
            data = objects[0]['data']
            info = objects[0]['info']
            input_name = info[1]
            input_type_name = info[2].split('.')[1].split('-')[0]

        except Exception as e:
            raise ValueError('Unable to fetch input_ref object from workspace: ' + str(e))
            #to get the full stack trace: traceback.format_exc()

        if input_type_name == 'MSA':
            MSA_in = data
            # DEBUG
            #for field in MSA_in.keys():
            #    self.log(console, "MSA key: '"+field+"'")
            row_order = []
            default_row_labels = dict()
            if 'row_order' in MSA_in:
                row_order = MSA_in['row_order']
            else:
                row_order = sorted(MSA_in['alignment'].keys())

            if 'default_row_labels' in MSA_in:
                default_row_labels = MSA_in['default_row_labels']
            else:
                for row_id in row_order:
                    default_row_labels[row_id] = row_id
            if len(row_order) < 2:
                self.log(invalid_msgs,"must have multiple records in MSA: "+params['input_ref'])
            # DEBUG
            #for row_id in row_order:
            #    self.log(console, "row_id: '"+row_id+"' default_row_label: '"+default_row_labels[row_id]+"'")


            # export features to FASTA file
            new_ids = dict()
            input_MSA_file_path = os.path.join(self.scratch, input_name+".fasta")
            self.log(console, 'writing fasta file: '+input_MSA_file_path)
            records = []
            for row_id in row_order:
                # take care of characters that will mess up newick and/or fasttree
                row_id_disp = re.sub('\s','_',row_id)
                row_id_disp = re.sub('\/','%'+'/'.encode("hex"), row_id_disp)
                row_id_disp = re.sub(r'\\','%'+'\\'.encode("hex"), row_id_disp)
                row_id_disp = re.sub('\(','%'+'('.encode("hex"), row_id_disp)
                row_id_disp = re.sub('\)','%'+')'.encode("hex"), row_id_disp)
                row_id_disp = re.sub('\[','%'+'['.encode("hex"), row_id_disp)
                row_id_disp = re.sub('\]','%'+']'.encode("hex"), row_id_disp)
                row_id_disp = re.sub('\:','%'+':'.encode("hex"), row_id_disp)
                row_id_disp = re.sub('\;','%'+';'.encode("hex"), row_id_disp)
                row_id_disp = re.sub('\|','%'+';'.encode("hex"), row_id_disp)
                new_ids[row_id] = row_id_disp

                #self.log(console,"row_id: '"+row_id+"' row_id_disp: '"+row_id_disp+"'")  # DEBUG
                #self.log(console,"alignment: '"+MSA_in['alignment'][row_id]+"'")  # DEBUG
            # using SeqIO makes multiline sequences.  FastTree doesn't like
                #record = SeqRecord(Seq(MSA_in['alignment'][row_id]), id=row_id, description=default_row_labels[row_id])
                #records.append(record)
            #SeqIO.write(records, input_MSA_file_path, "fasta")
                #records.extend(['>'+row_id,
                records.extend(['>'+row_id_disp,
                                MSA_in['alignment'][row_id]
                               ])
            with open(input_MSA_file_path,'w',0) as input_MSA_file_handle:
                input_MSA_file_handle.write("\n".join(records)+"\n")

            # DEBUG
            #self.log(console, "MSA INPUT:")
            #self.log(console, "\n".join(records)+"\n")  # DEBUG

            # Determine whether nuc or protein sequences
            #
            NUC_MSA_pattern = re.compile("^[\.\-_ACGTUXNRYSWKMBDHVacgtuxnryswkmbdhv \t\n]+$")
            all_seqs_nuc = True
            for row_id in row_order:
                #self.log(console, row_id+": '"+MSA_in['alignment'][row_id]+"'")
                if NUC_MSA_pattern.match(MSA_in['alignment'][row_id]) == None:
                    all_seqs_nuc = False
                    break

        # Missing proper input_type
        #
        else:
            raise ValueError('Cannot yet handle input_name type of: '+type_name)


        # Get start tree (if any)
        #
        if 'intree_ref' in params and params['intree_ref'] != None:
            try:
                ws = workspaceService(self.workspaceURL, token=ctx['token'])
                objects = ws.get_objects([{'ref': params['intree_ref']}])
                data = objects[0]['data']
                info = objects[0]['info']
                intree_name = info[1]
                intree_type_name = info[2].split('.')[1].split('-')[0]

            except Exception as e:
                raise ValueError('Unable to fetch intree_ref object from workspace: ' + str(e))
                #to get the full stack trace: traceback.format_exc()
            
            if intree_type_name == 'Tree':
                tree_in = data
                intree_newick_file_path = os.path.join(self.scratch, intree_name+".newick")
                self.log(console, 'writing intree file: '+intree_newick_file_path)
                intree_newick_file_handle = open(intree_newick_file_path, 'w', 0)
                intree_newick_file_handle.write(tree_in['tree'])
                intree_newick_file_handle.close()
            else:
                raise ValueError('Cannot yet handle intree type of: '+type_name)


        # DEBUG: check the MSA file contents
#        with open(input_MSA_file_path, 'r', 0) as input_MSA_file_handle:
#            for line in input_MSA_file_handle:
#                #self.log(console,"MSA_LINE: '"+line+"'")  # too big for console
#                self.log(invalid_msgs,"MSA_LINE: '"+line+"'")


        # validate input data
        #
        if len(invalid_msgs) > 0:

            # load the method provenance from the context object
            self.log(console,"SETTING PROVENANCE")  # DEBUG
            provenance = [{}]
            if 'provenance' in ctx:
                provenance = ctx['provenance']
            # add additional info to provenance here, in this case the input data object reference
            provenance[0]['input_ws_objects'] = []
            provenance[0]['input_ws_objects'].append(params['input_ref'])
            if 'intree_ref' in params and params['intree_ref'] != None:
                provenance[0]['input_ws_objects'].append(params['intree_ref'])
            provenance[0]['service'] = 'kb_fasttree'
            provenance[0]['method'] = 'run_FastTree'

            # report
            report += "FAILURE\n\n"+"\n".join(invalid_msgs)+"\n"
            reportObj = {
                'objects_created':[],
                'text_message':report
                }

            reportName = 'fasttree_report_'+str(uuid.uuid4())
            report_obj_info = ws.save_objects({
#                'id':info[6],
                'workspace':params['workspace_name'],
                'objects':[
                    {
                        'type':'KBaseReport.Report',
                        'data':reportObj,
                        'name':reportName,
                        'meta':{},
                        'hidden':1,
                        'provenance':provenance
                    }
                ]
            })[0]


            self.log(console,"BUILDING RETURN OBJECT")
            returnVal = { 'report_name': reportName,
                          'report_ref': str(report_obj_info[6]) + '/' + str(report_obj_info[0]) + '/' + str(report_obj_info[4]),
                          'output_ref': None
                          }
            self.log(console,"run_FastTree DONE")
            return [returnVal]


        ### Construct the command
        #
        #  e.g. fasttree -in <fasta_in> -out <fasta_out> -maxiters <n> -haxours <h>
        #
        fasttree_cmd = [self.FASTTREE_bin]
#        fasttree_cmd = []  # DEBUG

        # check for necessary files
        if not os.path.isfile(self.FASTTREE_bin):
            raise ValueError("no such file '"+self.FASTTREE_bin+"'")
        if not os.path.isfile(input_MSA_file_path):
            raise ValueError("no such file '"+input_MSA_file_path+"'")
        if not os.path.getsize(input_MSA_file_path) > 0:
            raise ValueError("empty file '"+input_MSA_file_path+"'")

        # DEBUG
#        with open(input_MSA_file_path,'r',0) as input_MSA_file_handle:
#            for line in input_MSA_file_handle:
#                #self.log(console,"MSA LINE: '"+line+"'")  # too big for console
#                self.log(invalid_msgs,"MSA LINE: '"+line+"'")


        # set the output path
        timestamp = int((datetime.utcnow() - datetime.utcfromtimestamp(0)).total_seconds()*1000)
        output_dir = os.path.join(self.scratch,'output.'+str(timestamp))
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        output_newick_file_path = os.path.join(output_dir, params['output_name']+'.newick');

        # This doesn't work for some reason
#        fasttree_cmd.append('-out')
#        fasttree_cmd.append(output_newick_file_path)


        # options
        #fasttree_cmd.append('-quiet')
        fasttree_cmd.append('-nopr')
        if 'fastest' in params and params['fastest'] != None and params['fastest'] != 0:
            fasttree_cmd.append('-fastest')
        if 'pseudo' in params and params['pseudo'] != None and params['pseudo'] != 0:
            fasttree_cmd.append('-pseudo')
        if 'intree_ref' in params and params['intree_ref'] != None:
            fasttree_cmd.append('-intree')
            fasttree_cmd.append(intree_newick_file_path)
        if all_seqs_nuc and 'gtr' in params and params['gtr'] != None and params['gtr'] != 0:
            fasttree_cmd.append('-gtr')
        if not all_seqs_nuc and 'wag' in params and params['wag'] != None and params['wag'] != 0:
            fasttree_cmd.append('-wag')
        if 'noml' in params and params['noml'] != None and params['noml'] != 0:
            fasttree_cmd.append('-noml')
        if 'nome' in params and params['nome'] != None and params['nome'] != 0:
            fasttree_cmd.append('-nome')
        if 'nocat' in params and params['nocat'] != None and params['nocat'] != 0:
            fasttree_cmd.append('-nocat')
        elif not all_seqs_nuc and 'cat' in params and params['cat'] != None and params['cat'] > 0:
        # DEBUG
#        elif 'cat' in params and params['cat'] != None and params['cat'] > 0:
            fasttree_cmd.append('-cat')
            fasttree_cmd.append(str(params['cat']))
        if 'gamma' in params and params['gamma'] != None and params['gamma'] != 0:
            fasttree_cmd.append('-gamma')

        if all_seqs_nuc:
            fasttree_cmd.append('-nt')

        # better (meaning it works) to write MSA to STDIN (below)
#        fasttree_cmd.append('<')
#        fasttree_cmd.append(input_MSA_file_path)
        fasttree_cmd.append('>')
        fasttree_cmd.append(output_newick_file_path)


        # Run FASTTREE, capture output as it happens
        #
        self.log(console, 'RUNNING FASTTREE:')
        self.log(console, '    '+' '.join(fasttree_cmd))
#        self.log(console, '    '+self.FASTTREE_bin+' '+' '.join(fasttree_cmd))
#        report += "\n"+'running FASTTREE:'+"\n"
#        report += '    '+' '.join(fasttree_cmd)+"\n"

        # FastTree requires shell=True in order to see input data
        env = os.environ.copy()
#        p = subprocess.Popen(fasttree_cmd, \
        joined_fasttree_cmd = ' '.join(fasttree_cmd)  # redirect out doesn't work with subprocess unless you join command first
        p = subprocess.Popen([joined_fasttree_cmd], \
                             cwd = self.scratch, \
                             stdin = subprocess.PIPE, \
                             stdout = subprocess.PIPE, \
                             stderr = subprocess.PIPE, \
                             shell = True, \
                             env = env)
#                             stdout = subprocess.PIPE, \
#                             executable = '/bin/bash' )

#        p = subprocess.Popen(fasttree_cmd, \
#                             cwd = self.scratch, \
#                             stdout = subprocess.PIPE, \
#                             stderr = subprocess.STDOUT, \
#                             shell = True, \
#                             env = env, \
#                             executable = self.FASTTREE_bin )

#                             shell = True, \  # seems necessary?
#                            stdout = subprocess.PIPE, \
#                             stdout = output_newick_file_path, \

        
        # write MSA to process for FastTree
        #
        with open(input_MSA_file_path,'r',0) as input_MSA_file_handle:
            for line in input_MSA_file_handle:
                p.stdin.write(line)
        p.stdin.close()
        p.wait()


        # Read output
        #
        while True:
            line = p.stdout.readline()
            #line = p.stderr.readline()
            if not line: break
            self.log(console, line.replace('\n', ''))

        p.stdout.close()
        #p.stderr.close()
        p.wait()
        self.log(console, 'return code: ' + str(p.returncode))
        if p.returncode != 0:
            raise ValueError('Error running FASTTREE, return code: '+str(p.returncode) + 
                '\n\n'+ '\n'.join(console))

        # Check that FASTREE produced output
        #
        if not os.path.isfile(output_newick_file_path):
            raise ValueError("failed to create FASTTREE output: "+output_newick_file_path)
        elif not os.path.getsize(output_newick_file_path) > 0:
            raise ValueError("created empty file for FASTTREE output: "+output_newick_file_path)


        # load the method provenance from the context object
        #
        self.log(console,"SETTING PROVENANCE")  # DEBUG
        provenance = [{}]
        if 'provenance' in ctx:
            provenance = ctx['provenance']
        # add additional info to provenance here, in this case the input data object reference
        provenance[0]['input_ws_objects'] = []
        provenance[0]['input_ws_objects'].append(params['input_ref'])
        if 'intree_ref' in params and params['intree_ref'] != None:
            provenance[0]['input_ws_objects'].append(params['intree_ref'])
        provenance[0]['service'] = 'kb_fasttree'
        provenance[0]['method'] = 'run_FastTree'


        # Upload results
        #
        if len(invalid_msgs) == 0:
            self.log(console,"UPLOADING RESULTS")  # DEBUG

            tree_name = params['output_name']
            tree_description = params['desc']
            tree_type = 'GeneTree'
            if 'species_tree_flag' in params and params['species_tree_flag'] != None and params['species_tree_flag'] != 0:
                tree_type = 'SpeciesTree'

            with open(output_newick_file_path,'r',0) as output_newick_file_handle:
                output_newick_buf = output_newick_file_handle.read()
            output_newick_buf = output_newick_buf.rstrip()
            if not output_newick_buf.endswith(';'):
                output_newick_buf += ';'
            self.log(console,"\nNEWICK:\n"+output_newick_buf+"\n")
        
            # Extract info from MSA
            #
            tree_attributes = None
            default_node_labels = None
            ws_refs = None
            kb_refs = None
            leaf_list = None
            if default_row_labels:
                default_node_labels = dict()
                leaf_list = []
                for row_id in default_row_labels.keys():
                    new_row_id = new_ids[row_id]
                    #default_node_labels[row_id] = default_row_labels[row_id]
                    default_node_labels[new_row_id] = default_row_labels[row_id]
                    leaf_list.append(new_row_id)

            if 'ws_refs' in MSA_in.keys() and MSA_in['ws_refs'] != None:
                ws_refs = MSA_in['ws_refs']
            if 'kb_refs' in MSA_in.keys() and MSA_in['kb_refs'] != None:
                kb_refs = MSA_in['kb_refs']

            # Build output_Tree structure
            #
            output_Tree = {
                      'name': tree_name,
                      'description': tree_description,
                      'type': tree_type,
                      'tree': output_newick_buf
                     }
            if tree_attributes != None:
                output_Tree['tree_attributes'] = tree_attributes
            if default_node_labels != None:
                output_Tree['default_node_labels'] = default_node_labels
            if ws_refs != None:
                output_Tree['ws_refs'] = ws_refs 
            if kb_refs != None:
                output_Tree['kb_refs'] = kb_refs
            if leaf_list != None:
                output_Tree['leaf_list'] = leaf_list 

            # Store output_Tree
            #
            new_obj_info = ws.save_objects({
                            'workspace': params['workspace_name'],
                            'objects':[{
                                    'type': 'KBaseTrees.Tree',
                                    'data': output_Tree,
                                    'name': params['output_name'],
                                    'meta': {},
                                    'provenance': provenance
                                }]
                        })[0]


        # If input data is invalid
        #
        self.log(console,"BUILDING REPORT")  # DEBUG

        if len(invalid_msgs) != 0:
            reportName = 'fasttree_report_'+str(uuid.uuid4())
            report += "FAILURE\n\n"+"\n".join(invalid_msgs)+"\n"
            reportObj = {
                'objects_created':[],
                'text_message':report
                }
            report_obj_info = ws.save_objects({
                    #'id':info[6],
                    'workspace':params['workspace_name'],
                    'objects':[
                        {
                            'type':'KBaseReport.Report',
                            'data':reportObj,
                            'name':reportName,
                            'meta':{},
                            'hidden':1,
                            'provenance':provenance
                            }
                        ]
                    })[0]
            returnVal = { 'report_name': reportName,
                          'report_ref': str(report_obj_info[6]) + '/' + str(report_obj_info[0]) + '/' + str(report_obj_info[4]),
                          }
            return [returnVal]


        # Upload newick and newick labels
        #
        newick_labels_file = params['output_name']+'-labels.newick'
        output_newick_labels_file_path = os.path.join(output_dir, newick_labels_file);
        mod_newick_buf = output_newick_buf
        for row_id in new_ids:
            new_id = new_ids[row_id]
            label = default_node_labels[new_id]
            label = re.sub('\s','_',label)
            label = re.sub('\/','%'+'/'.encode("hex"), label)
            label = re.sub(r'\\','%'+'\\'.encode("hex"), label)
            label = re.sub('\(','%'+'('.encode("hex"), label)
            label = re.sub('\)','%'+')'.encode("hex"), label)
            label = re.sub('\[','%'+'['.encode("hex"), label)
            label = re.sub('\]','%'+']'.encode("hex"), label)
            label = re.sub('\:','%'+':'.encode("hex"), label)
            label = re.sub('\;','%'+';'.encode("hex"), label)
            label = re.sub('\|','%'+';'.encode("hex"), label)
            mod_newick_buf = re.sub ('\('+new_id+'\:', '('+label+':', mod_newick_buf)
            mod_newick_buf = re.sub ('\,'+new_id+'\:', ','+label+':', mod_newick_buf)

            #self.log(console, "new_id: '"+new_id+"' label: '"+label+"'")  # DEBUG
        
        with open (output_newick_labels_file_path, 'w', 0) as output_newick_labels_file_handle:
            output_newick_labels_file_handle.write(mod_newick_buf)

        # upload
        try:
            newick_upload_ret = dfu.file_to_shock({'file_path': output_newick_file_path,
                                                   #'pack': 'zip'})
                                                   'make_handle': 0})
        except:
            raise ValueError ('error uploading newick file to shock')
        try:
            newick_labels_upload_ret = dfu.file_to_shock({'file_path': output_newick_labels_file_path,
                                                   #'pack': 'zip'})
                                                   'make_handle': 0})
        except:
            raise ValueError ('error uploading newick labels file to shock')


        # Create html with tree image
        #
        timestamp = int((datetime.utcnow() - datetime.utcfromtimestamp(0)).total_seconds()*1000)
        html_output_dir = os.path.join(self.scratch,'output_html.'+str(timestamp))
        if not os.path.exists(html_output_dir):
            os.makedirs(html_output_dir)
        html_file = params['output_name']+'.html'
        png_file = params['output_name']+'.png'
        pdf_file = params['output_name']+'.pdf'
        output_html_file_path = os.path.join(html_output_dir, html_file);
        output_png_file_path = os.path.join(html_output_dir, png_file);
        output_pdf_file_path = os.path.join(output_dir, pdf_file);


        # HERE
        t = ete3.Tree("(A:1,(B:1,(E:1,D:1):0.5):0.5);")
        t.render(output_png_file_path, w=150, units="mm")        
        t.render(output_pdf_file_path, w=150, units="mm")        


        # upload
        try:
            png_upload_ret = dfu.file_to_shock({'file_path': output_png_file_path,
                                                #'pack': 'zip'})
                                                'make_handle': 0})
        except:
            raise ValueError ('error uploading png file to shock')
        try:
            pdf_upload_ret = dfu.file_to_shock({'file_path': output_pdf_file_path,
                                                #'pack': 'zip'})
                                                'make_handle': 0})
        except:
            raise ValueError ('error uploading pdf file to shock')


        # Create report obj
        #
        reportName = 'blast_report_'+str(uuid.uuid4())
        #report += output_newick_buf+"\n"
        reportObj = {'objects_created': [],
                     #'text_message': '',  # or is it 'message'?
                     'message': '',  # or is it 'text_message'?
                     'direct_html': '',
                     'direct_html_link_index': None,
                     'file_links': [],
                     'html_links': [],
                     'workspace_name': params['workspace_name'],
                     'report_object_name': reportName
                     }
#        reportObj['direct_html_link_index'] = 0
#        reportObj['html_links'] = [{'shock_id': html_upload_ret['shock_id'],
#                                    'name': html_file,
#                                    'label': params['output_name']+' HTML'}
#                                   ]
        reportObj['file_links'] = [{'shock_id': newick_upload_ret['shock_id'],
                                    'name': params['output_name']+'.newick',
                                    'label': params['output_name']+' NEWICK'
                                    },
                                   {'shock_id': newick_labels_upload_ret['shock_id'],
                                    'name': params['output_name']+'-labels.newick',
                                    'label': params['output_name']+' NEWICK (with labels)'
                                    },
                                   {'shock_id': png_upload_ret['shock_id'],
                                    'name': params['output_name']+'.png',
                                    'label': params['output_name']+' PNG'
                                    },
                                   {'shock_id': pdf_upload_ret['shock_id'],
                                    'name': params['output_name']+'.pdf',
                                    'label': params['output_name']+' PDF'
                                    }
                                   ]

        SERVICE_VER = 'release'
        reportClient = KBaseReport(self.callbackURL, token=ctx['token'], service_ver=SERVICE_VER)
        report_info = reportClient.create_extended_report(reportObj)


        # Done
        #
        self.log(console,"BUILDING RETURN OBJECT")
        returnVal = { 'report_name': report_info['name'],
                      'report_ref': report_info['ref'],
                      'output_ref': str(new_obj_info[6])+'/'+str(new_obj_info[0])+'/'+str(new_obj_info[4])
                      }

        self.log(console,"run_FastTree DONE")
        #END run_FastTree

        # At some point might do deeper type checking...
        if not isinstance(returnVal, dict):
            raise ValueError('Method run_FastTree return value ' +
                             'returnVal is not type dict as required.')
        # return the results
        return [returnVal]
    def status(self, ctx):
        #BEGIN_STATUS
        returnVal = {'state': "OK",
                     'message': "",
                     'version': self.VERSION,
                     'git_url': self.GIT_URL,
                     'git_commit_hash': self.GIT_COMMIT_HASH}
        #END_STATUS
        return [returnVal]

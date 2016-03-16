/*
** A KBase module: kb_fasttree
**
** This module runs FastTree to make Trees for either DNA or PROTEIN MSAs
** 
*/

module kb_fasttree {

    /* 
    ** The workspace object refs are of form:
    **
    **    objects = ws.get_objects([{'ref': params['workspace_id']+'/'+params['obj_name']}])
    **
    ** "ref" means the entire name combining the workspace id and the object name
    ** "id" is a numerical identifier of the workspace or object, and should just be used for workspace
    ** "name" is a string identifier of a workspace or object.  This is received from Narrative.
    */
    typedef string workspace_name;
    typedef string data_obj_name;
    typedef string data_obj_ref;


    /* FastTree Input Params
    */
    typedef structure {
        workspace_name workspace_name;
	string         desc;
	data_obj_name  input_name;
        data_obj_name  output_name;
	data_obj_name  intree;
	int            fastest;  /* boolean */
	int            pseudo;   /* boolean */
	int            gtr;      /* boolean */
	int            wag;      /* boolean */
	int            noml;     /* boolean */
	int            nome;     /* boolean */
        int            cat;      /* actually is an int */
	int            nocat;    /* boolean */
        int            gamma;    /* boolean */
    } FastTree_Params;


    /* FastTree Output
    */
    typedef structure {
	data_obj_name report_name;
	data_obj_ref  report_ref;
/*       data_obj_ref  output_tree_ref;
*/
    } FastTree_Output;
	

    /*  Method for Tree building of either DNA or PROTEIN sequences
    **
    **        input_type: MSA
    **        output_type: Tree
    */
    funcdef run_FastTree (FastTree_Params params)  returns (FastTree_Output) authentication required;
};

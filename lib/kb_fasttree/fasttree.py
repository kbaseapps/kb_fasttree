"""Implementation of the fasttree app."""

import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from pprint import pformat
from typing import Any, Dict

import ete3  # Tree drawing package we install in Dockerfile
from installed_clients.DataFileUtilClient import DataFileUtil
from installed_clients.KBaseReportClient import KBaseReport
from installed_clients.WorkspaceClient import Workspace

SERVICE_VER = "release"
FASTTREE_BIN = "/kb/module/FastTree/bin/FastTree"


def generate_run_id() -> str:
    """Generate an ID for this fasttree run, based on the current date and time.

    :return: temporally unique run ID
    :rtype: str
    """
    return datetime.now(tz=timezone.utc).strftime("%Y%m%d_%H%M%S")


def now_iso() -> str:
    """Create a timestamp."""
    return datetime.now(tz=timezone.utc).strftime("%Y-%m-%d_%H:%M:%S")


def log(target, message: str) -> None:
    """Simple logger."""
    message = "[" + now_iso() + "] " + message
    if target is not None:
        target.append(message)
    print(message)  # noqa: T201
    sys.stdout.flush()


def run_fasttree(
    config: Dict[str, str], ctx: Dict[str, Any], params: Dict[str, Any]
) -> Dict[str, Any]:
    """Method for Tree building of either DNA or PROTEIN sequences.

    :param config: dictionary containing workspace and callback server URLs plus scratch dir.
    :type config: Dict[str, str]
    :param ctx: context object
    :type ctx: Dict[str, Any]
    :param params: app params, fresh from the KBase interface
    :type params: Dict[str, Any]
    :return: KBaseReport output
    :rtype: Dict[str, Any]
    """
    # create a directory for all files related to this run to live in
    run_id = generate_run_id()
    run_dir = Path(config["scratch"]) / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    console = []
    invalid_msgs = []
    log(console, "Running run_FastTree with params=")
    log(console, "\n" + pformat(params))
    report = ""

    #### do some basic checks
    #
    if "workspace_name" not in params:
        raise ValueError("workspace_name parameter is required")
    if "input_ref" not in params:
        raise ValueError("input_ref parameter is required")
    if "output_name" not in params:
        raise ValueError("output_name parameter is required")

    #### Get the input_ref MSA object
    ##
    msa_in = None
    try:
        ws = Workspace(config["workspace_url"], token=ctx["token"])
        objects = ws.get_objects([{"ref": params["input_ref"]}])
        msa_in = objects[0]["data"]
        info = objects[0]["info"]
        input_name = info[1]
        input_type_name = info[2].split(".")[1].split("-")[0]

    except Exception as e:
        raise ValueError("Unable to fetch input_ref object from workspace: " + str(e)) from e
        # to get the full stack trace: traceback.format_exc()

    if input_type_name != "MSA":
        raise ValueError("Cannot yet handle input_name type of: " + input_type_name)

    # DEBUG
    # for field in msa_in.keys():
    #    log(console, "MSA key: '"+field+"'")
    row_order = []
    default_row_labels = {}
    row_order = msa_in["row_order"] if "row_order" in msa_in else sorted(msa_in["alignment"].keys())

    if "default_row_labels" in msa_in:
        default_row_labels = msa_in["default_row_labels"]
    else:
        for row_id in row_order:
            default_row_labels[row_id] = row_id
    if len(row_order) <= 2:
        log(invalid_msgs, "must have 3 or more records in MSA: " + params["input_ref"])
    # DEBUG
    # for row_id in row_order:
    #    log(console, "row_id: '"+row_id+"' default_row_label: '"+default_row_labels[row_id]+"'")

    # export features to FASTA file
    new_ids = {}
    input_msa_file_path = run_dir / f"{input_name}.fasta"
    log(console, f"writing fasta file: {input_msa_file_path}")
    records = []
    for row_id in row_order:
        # take care of characters that will mess up newick and/or fasttree
        row_id_disp = re.sub("\s", "_", row_id)
        row_id_disp = re.sub("\/", "%" + "/".encode("utf-8").hex(), row_id_disp)
        row_id_disp = re.sub(r"\\", "%" + "\\".encode("utf-8").hex(), row_id_disp)
        row_id_disp = re.sub("\(", "%" + "(".encode("utf-8").hex(), row_id_disp)
        row_id_disp = re.sub("\)", "%" + ")".encode("utf-8").hex(), row_id_disp)
        row_id_disp = re.sub("\[", "%" + "[".encode("utf-8").hex(), row_id_disp)
        row_id_disp = re.sub("\]", "%" + "]".encode("utf-8").hex(), row_id_disp)
        row_id_disp = re.sub("\:", "%" + ":".encode("utf-8").hex(), row_id_disp)
        row_id_disp = re.sub("\;", "%" + ";".encode("utf-8").hex(), row_id_disp)
        row_id_disp = re.sub("\|", "%" + ";".encode("utf-8").hex(), row_id_disp)
        new_ids[row_id] = row_id_disp

        # log(console,"row_id: '"+row_id+"' row_id_disp: '"+row_id_disp+"'")  # DEBUG
        # log(console,"alignment: '"+MSA_in['alignment'][row_id]+"'")  # DEBUG
        # using SeqIO makes multiline sequences.  FastTree doesn't like
        # record = SeqRecord(Seq(MSA_in['alignment'][row_id]), id=row_id, description=default_row_labels[row_id])
        # records.append(record)
        # SeqIO.write(records, input_MSA_file_path, "fasta")
        # records.extend(['>'+row_id,
        records.extend([">" + row_id_disp, msa_in["alignment"][row_id]])

    with input_msa_file_path.open("w") as input_msa_file_handle:
        input_msa_file_handle.write("\n".join(records) + "\n")

    # DEBUG
    # log(console, "MSA INPUT:")
    # log(console, "\n".join(records)+"\n")  # DEBUG

    # Determine whether nuc or protein sequences
    #
    NUC_MSA_pattern = re.compile("^[\.\-_ACGTUXNRYSWKMBDHVacgtuxnryswkmbdhv \t\n]+$")
    all_seqs_nuc = True
    for row_id in row_order:
        # log(console, row_id+": '"+msa_in['alignment'][row_id]+"'")
        if NUC_MSA_pattern.match(msa_in["alignment"][row_id]) is None:
            all_seqs_nuc = False
            break

    # Get start tree (if any)
    #
    if params.get("intree_ref"):
        tree_in = None
        try:
            ws = Workspace(config["workspace_url"], token=ctx["token"])
            objects = ws.get_objects([{"ref": params["intree_ref"]}])
            tree_in = objects[0]["data"]
            info = objects[0]["info"]
            intree_name = info[1]
            intree_type_name = info[2].split(".")[1].split("-")[0]

        except Exception as e:
            raise ValueError("Unable to fetch intree_ref object from workspace: " + str(e))
            # to get the full stack trace: traceback.format_exc()

        if intree_type_name != "Tree":
            raise ValueError("Cannot yet handle intree type of: " + intree_type_name)

        intree_newick_file_path = run_dir / f"{intree_name}.newick"
        log(console, f"writing intree file: {intree_newick_file_path}")
        with intree_newick_file_path.open("w") as fh:
            fh.write(tree_in["tree"])

    # DEBUG: check the MSA file contents
    #        with open(input_msa_file_path, 'r') as input_msa_file_handle:
    #            for line in input_msa_file_handle:
    #                #log(console,"MSA_LINE: '"+line+"'")  # too big for console
    #                log(invalid_msgs,"MSA_LINE: '"+line+"'")

    # validate input data
    #
    if len(invalid_msgs) > 0:
        # load the method provenance from the context object
        log(console, "SETTING PROVENANCE")  # DEBUG
        provenance = ctx.get("provenance", [{}])
        # add additional info to provenance here, in this case the input data object reference
        provenance[0]["input_ws_objects"] = []
        provenance[0]["input_ws_objects"].append(params["input_ref"])
        if params.get("intree_ref"):
            provenance[0]["input_ws_objects"].append(params["intree_ref"])
        provenance[0]["service"] = "kb_fasttree"
        provenance[0]["method"] = "run_FastTree"

        # report
        report += "FAILURE\n\n" + "\n".join(invalid_msgs) + "\n"
        report_obj = {"objects_created": [], "text_message": report}

        report_name = f"fasttree_report_{run_id}"
        report_obj_info = ws.save_objects(
            {
                "workspace": params["workspace_name"],
                "objects": [
                    {
                        "type": "KBaseReport.Report",
                        "data": report_obj,
                        "name": report_name,
                        "meta": {},
                        "hidden": 1,
                        "provenance": provenance,
                    }
                ],
            }
        )[0]

        log(console, "BUILDING RETURN OBJECT")
        log(console, "run_FastTree DONE")
        return {
            "report_name": report_name,
            "report_ref": f"{report_obj_info[6]}/{report_obj_info[0]}/{report_obj_info[4]}",
            "output_ref": None,
        }

    # check for necessary files
    if not Path(FASTTREE_BIN).is_file():
        err_msg = f"no such file '{FASTTREE_BIN}'"
        raise ValueError(err_msg)
    if not input_msa_file_path.is_file():
        err_msg = f"no such file '{input_msa_file_path}'"
        raise ValueError(err_msg)
    if input_msa_file_path.stat().st_size <= 0:
        err_msg = f"empty file '{input_msa_file_path}'"
        raise ValueError(err_msg)

    # set the output path
    output_dir = run_dir / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_newick_file_path = output_dir / f'{params["output_name"]}.newick'

    ### Construct the command
    #
    #  e.g. fasttree -in <fasta_in> -out <fasta_out> -maxiters <n> -haxours <h>
    #
    fasttree_cmd = [FASTTREE_BIN, "-nopr"]

    # options
    # fasttree_cmd.append('-quiet')
    if "fastest" in params and params["fastest"] is not None and params["fastest"] != 0:
        fasttree_cmd.append("-fastest")
    if "pseudo" in params and params["pseudo"] is not None and params["pseudo"] != 0:
        fasttree_cmd.append("-pseudo")
    if "intree_ref" in params and params["intree_ref"] is not None and params["intree_ref"] != "":
        fasttree_cmd.append("-intree")
        fasttree_cmd.append(str(intree_newick_file_path))
    if all_seqs_nuc and "gtr" in params and params["gtr"] is not None and params["gtr"] != 0:
        fasttree_cmd.append("-gtr")
    if not all_seqs_nuc and "wag" in params and params["wag"] is not None and params["wag"] != 0:
        fasttree_cmd.append("-wag")
    if "noml" in params and params["noml"] is not None and params["noml"] != 0:
        fasttree_cmd.append("-noml")
    if "nome" in params and params["nome"] is not None and params["nome"] != 0:
        fasttree_cmd.append("-nome")
    if "nocat" in params and params["nocat"] is not None and params["nocat"] != 0:
        fasttree_cmd.append("-nocat")
    elif not all_seqs_nuc and "cat" in params and params["cat"] is not None and params["cat"] > 0:
        # DEBUG
        fasttree_cmd.append("-cat")
        fasttree_cmd.append(str(params["cat"]))
    if "gamma" in params and params["gamma"] is not None and params["gamma"] != 0:
        fasttree_cmd.append("-gamma")

    if all_seqs_nuc:
        fasttree_cmd.append("-nt")

    # This doesn't work for some reason
    #        fasttree_cmd.append('-out')
    #        fasttree_cmd.append(output_newick_file_path)

    # better (meaning it works) to write MSA to STDIN (below)
    fasttree_cmd.append(">")
    fasttree_cmd.append(str(output_newick_file_path))

    # Run FASTTREE, capture output as it happens
    #
    log(console, "RUNNING FASTTREE:")
    log(console, "    " + " ".join(fasttree_cmd))

    # FastTree requires shell=True in order to see input data
    env = os.environ.copy()
    joined_fasttree_cmd = " ".join(fasttree_cmd)
    # redirect out doesn't work with subprocess unless you join command first
    p = subprocess.Popen(
        [joined_fasttree_cmd],
        cwd=config["scratch"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=True,
        env=env,
    )

    # write MSA to process for FastTree
    #
    with input_msa_file_path.open() as input_msa_file_handle:
        for line in input_msa_file_handle:
            p.stdin.write(line.encode())
    p.stdin.close()
    p.wait()

    # Read output
    #
    while True:
        line = p.stdout.readline()
        # line = p.stderr.readline()
        if not line:
            break
        log(console, line.replace("\n", ""))

    p.stdout.close()
    # p.stderr.close()
    p.wait()
    log(console, "return code: " + str(p.returncode))
    if p.returncode != 0:
        raise ValueError(
            "Error running FASTTREE, return code: "
            + str(p.returncode)
            + "\n\n"
            + "\n".join(console)
        )

    # Check that FASTREE produced output
    #
    if not output_newick_file_path.is_file():
        err_msg = f"failed to create FASTTREE output: {output_newick_file_path}"
        raise ValueError(err_msg)

    if output_newick_file_path.stat().st_size <= 0:
        err_msg = f"created empty file for FASTTREE output: {output_newick_file_path}"
        raise ValueError(err_msg)

    # load the method provenance from the context object
    #
    log(console, "SETTING PROVENANCE")  # DEBUG
    provenance = [{}]
    if "provenance" in ctx:
        provenance = ctx["provenance"]
    # add additional info to provenance here, in this case the input data object reference
    provenance[0]["input_ws_objects"] = [params["input_ref"]]
    if params.get("intree_ref"):
        provenance[0]["input_ws_objects"].append(params["intree_ref"])
    provenance[0]["service"] = "kb_fasttree"
    provenance[0]["method"] = "run_FastTree"

    if len(invalid_msgs) != 0:
        report_name = f"fasttree_report_{run_id}"
        report += "FAILURE\n\n" + "\n".join(invalid_msgs) + "\n"
        report_obj = {"objects_created": [], "text_message": report}
        report_obj_info = ws.save_objects(
            {
                #'id':info[6],
                "workspace": params["workspace_name"],
                "objects": [
                    {
                        "type": "KBaseReport.Report",
                        "data": report_obj,
                        "name": report_name,
                        "meta": {},
                        "hidden": 1,
                        "provenance": provenance,
                    }
                ],
            }
        )[0]
        return {
            "report_name": report_name,
            "report_ref": f"{report_obj_info[6]}/{report_obj_info[0]}/{report_obj_info[4]}",
        }

    # Upload results
    #
    log(console, "UPLOADING RESULTS")  # DEBUG

    tree_name = params["output_name"]
    tree_description = params["desc"]
    tree_type = "GeneTree"
    if (
        "species_tree_flag" in params
        and params["species_tree_flag"] is not None
        and params["species_tree_flag"] != 0
    ):
        tree_type = "SpeciesTree"

    with output_newick_file_path.open() as output_newick_file_handle:
        output_newick_buf = output_newick_file_handle.read()
    output_newick_buf = output_newick_buf.rstrip()
    if not output_newick_buf.endswith(";"):
        output_newick_buf += ";"
    log(console, "\nNEWICK:\n" + output_newick_buf + "\n")

    # Extract info from MSA
    #
    tree_attributes = None
    default_node_labels = None
    ws_refs = None
    kb_refs = None
    leaf_list = None
    if default_row_labels:
        default_node_labels = {}
        leaf_list = []
        # for row_id in default_row_labels.keys():  # some row ids don't wind up in trimmed msa
        for row_id in row_order:
            new_row_id = new_ids[row_id]
            default_node_labels[new_row_id] = default_row_labels[row_id]
            leaf_list.append(new_row_id)

    ws_refs = msa_in.get("ws_refs")
    kb_refs = msa_in.get("kb_refs")

    # Build output_tree structure
    #
    output_tree = {
        "name": tree_name,
        "description": tree_description,
        "type": tree_type,
        "tree": output_newick_buf,
    }
    # tree_attributes will always be None.
    # goodness knows what this was supposed to check for
    if tree_attributes is not None:
        output_tree["tree_attributes"] = tree_attributes
    if default_node_labels is not None:
        output_tree["default_node_labels"] = default_node_labels
    if ws_refs is not None:
        output_tree["ws_refs"] = ws_refs
    if kb_refs is not None:
        output_tree["kb_refs"] = kb_refs
    if leaf_list is not None:
        output_tree["leaf_list"] = leaf_list

    # Store output_tree
    #
    try:
        new_obj_info = ws.save_objects(
            {
                "workspace": params["workspace_name"],
                "objects": [
                    {
                        "type": "KBaseTrees.Tree",
                        "data": output_tree,
                        "name": params["output_name"],
                        "meta": {},
                        "provenance": provenance,
                    }
                ],
            }
        )[0]
    except Exception as e:
        err_msg = f'Unable to save tree {params["output_name"]} object to workspace {params["workspace_name"]}: {e}'
        raise ValueError(err_msg) from e
        # to get the full stack trace: traceback.format_exc()

    log(console, "BUILDING REPORT")  # DEBUG

    # Upload newick and newick labels
    #
    newick_labels_file = params["output_name"] + "-labels.newick"
    output_newick_labels_file_path = output_dir / newick_labels_file
    mod_newick_buf = output_newick_buf
    for row_id in new_ids:
        new_id = new_ids[row_id]
        label = default_node_labels[new_id]
        label = re.sub("\s", "_", label)
        label = re.sub("\/", "%" + "/".encode("utf-8").hex(), label)
        label = re.sub(r"\\", "%" + "\\".encode("utf-8").hex(), label)
        label = re.sub("\(", "%" + "(".encode("utf-8").hex(), label)
        label = re.sub("\)", "%" + ")".encode("utf-8").hex(), label)
        label = re.sub("\[", "%" + "[".encode("utf-8").hex(), label)
        label = re.sub("\]", "%" + "]".encode("utf-8").hex(), label)
        label = re.sub("\:", "%" + ":".encode("utf-8").hex(), label)
        label = re.sub("\;", "%" + ";".encode("utf-8").hex(), label)
        label = re.sub("\|", "%" + ";".encode("utf-8").hex(), label)
        mod_newick_buf = re.sub("\(" + new_id + "\:", "(" + label + ":", mod_newick_buf)
        mod_newick_buf = re.sub("\," + new_id + "\:", "," + label + ":", mod_newick_buf)

        # log(console, "new_id: '"+new_id+"' label: '"+label+"'")  # DEBUG

    mod_newick_buf = re.sub("_", " ", mod_newick_buf)
    with output_newick_labels_file_path.open("w") as output_newick_labels_file_handle:
        output_newick_labels_file_handle.write(mod_newick_buf)

    dfu = DataFileUtil(config["callback_url"], token=ctx["token"])
    # upload
    try:
        newick_upload_ret = dfu.file_to_shock(
            {
                "file_path": str(output_newick_file_path),
                #'pack': 'zip'})
                "make_handle": 0,
            }
        )
    except Exception as e:
        raise ValueError("error uploading newick file to shock") from e

    try:
        newick_labels_upload_ret = dfu.file_to_shock(
            {
                "file_path": str(output_newick_labels_file_path),
                #'pack': 'zip'})
                "make_handle": 0,
            }
        )
    except Exception as e:
        raise ValueError("error uploading newick labels file to shock") from e

    # Create html with tree image
    #
    # timestamp = int((datetime.utcnow() - datetime.utcfromtimestamp(0)).total_seconds() * 1000)
    # html_output_dir = run_dir / f"output_html.{timestamp}"
    html_output_dir = run_dir / "output_html"
    html_output_dir.mkdir(parents=True, exist_ok=True)

    html_file = params["output_name"] + ".html"
    png_file = params["output_name"] + ".png"
    pdf_file = params["output_name"] + ".pdf"
    output_html_file_path = html_output_dir / html_file
    output_png_file_path = html_output_dir / png_file
    output_pdf_file_path = output_dir / pdf_file
    # init ETE3 objects
    t = ete3.Tree(mod_newick_buf)
    ts = ete3.TreeStyle()

    # customize
    ts.show_leaf_name = True
    ts.show_branch_length = False
    ts.show_branch_support = True
    # ts.scale = 50 # 50 pixels per branch length unit
    ts.branch_vertical_margin = 5  # pixels between adjacent branches
    ts.title.add_face(
        ete3.TextFace(params["output_name"] + ": " + params["desc"], fsize=10), column=0
    )

    node_style = ete3.NodeStyle()
    node_style["fgcolor"] = "#606060"  # for node balls
    node_style["size"] = 10  # for node balls (gets reset based on support)
    node_style["vt_line_color"] = "#606060"
    node_style["hz_line_color"] = "#606060"
    node_style["vt_line_width"] = 2
    node_style["hz_line_width"] = 2
    node_style["vt_line_type"] = 0  # 0 solid, 1 dashed, 2 dotted
    node_style["hz_line_type"] = 0

    leaf_style = ete3.NodeStyle()
    leaf_style["fgcolor"] = "#ffffff"  # for node balls
    leaf_style["size"] = 2  # for node balls (we're using it to add space)
    leaf_style["vt_line_color"] = "#606060"  # unecessary
    leaf_style["hz_line_color"] = "#606060"
    leaf_style["vt_line_width"] = 2
    leaf_style["hz_line_width"] = 2
    leaf_style["vt_line_type"] = 0  # 0 solid, 1 dashed, 2 dotted
    leaf_style["hz_line_type"] = 0

    for n in t.traverse():
        if n.is_leaf():
            style = leaf_style
        else:
            style = ete3.NodeStyle()
            for k in node_style:
                style[k] = node_style[k]

            if n.support > 0.95:
                style["size"] = 6
            elif n.support > 0.90:
                style["size"] = 5
            elif n.support > 0.80:
                style["size"] = 4
            else:
                style["size"] = 2

        n.set_style(style)

    # save images
    dpi = 300
    img_units = "in"
    img_pix_width = 1200
    img_in_width = round(float(img_pix_width) / float(dpi), 1)
    img_html_width = img_pix_width // 2
    t.render(str(output_png_file_path), w=img_in_width, units=img_units, dpi=dpi, tree_style=ts)
    t.render(
        str(output_pdf_file_path), w=img_in_width, units=img_units, tree_style=ts
    )  # dpi irrelevant

    # make html
    html_report_lines = []
    html_report_lines += ["<html>"]
    html_report_lines += [
        "<head><title>KBase FastTree-2: " + params["output_name"] + "</title></head>"
    ]
    html_report_lines += ['<body bgcolor="white">']
    html_report_lines += ["<img width=" + str(img_html_width) + ' src="' + png_file + '">']
    html_report_lines += ["</body>"]
    html_report_lines += ["</html>"]

    html_report_str = "\n".join(html_report_lines)
    with output_html_file_path.open("w") as html_handle:
        html_handle.write(html_report_str)

    # upload images and html
    try:
        png_upload_ret = dfu.file_to_shock(
            {
                "file_path": str(output_png_file_path),
                #'pack': 'zip'})
                "make_handle": 0,
            }
        )
    except:
        raise ValueError("error uploading png file to shock")
    try:
        pdf_upload_ret = dfu.file_to_shock(
            {
                "file_path": str(output_pdf_file_path),
                #'pack': 'zip'})
                "make_handle": 0,
            }
        )
    except:
        raise ValueError("error uploading pdf file to shock")
    try:
        html_upload_ret = dfu.file_to_shock(
            {"file_path": str(html_output_dir), "make_handle": 0, "pack": "zip"}
        )
    except:
        raise ValueError("error uploading png file to shock")

    # Create report obj
    #
    report_name = f"blast_report_{run_id}"
    report_obj = {
        "objects_created": [
            {
                "ref": str(params["workspace_name"]) + "/" + str(params["output_name"]),
                "description": params["output_name"] + " Tree",
            }
        ],
        "message": "",  # or is it 'text_message'?
        "direct_html": "",
        "direct_html_link_index": 0,
        "html_links": [
            {
                "shock_id": html_upload_ret["shock_id"],
                "name": html_file,
                "label": params["output_name"] + " HTML",
            }
        ],
        "file_links": [
            {
                "shock_id": newick_upload_ret["shock_id"],
                "name": params["output_name"] + ".newick",
                "label": params["output_name"] + " NEWICK",
            },
            {
                "shock_id": newick_labels_upload_ret["shock_id"],
                "name": params["output_name"] + "-labels.newick",
                "label": params["output_name"] + " NEWICK (with labels)",
            },
            {
                "shock_id": png_upload_ret["shock_id"],
                "name": params["output_name"] + ".png",
                "label": params["output_name"] + " PNG",
            },
            {
                "shock_id": pdf_upload_ret["shock_id"],
                "name": params["output_name"] + ".pdf",
                "label": params["output_name"] + " PDF",
            },
        ],
        "workspace_name": params["workspace_name"],
        "report_object_name": report_name,
    }

    report_client = KBaseReport(config["callback_url"], token=ctx["token"], service_ver=SERVICE_VER)
    report_info = report_client.create_extended_report(report_obj)

    # Done
    #
    log(console, "BUILDING RETURN OBJECT")
    log(console, "run_FastTree DONE")
    return {
        "report_name": report_info["name"],
        "report_ref": report_info["ref"],
        "output_ref": f"{new_obj_info[6]}/{new_obj_info[0]}/{new_obj_info[4]}",
    }

    # END run_FastTree

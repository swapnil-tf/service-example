import ast
import io
import re
from typing import List

from rich.console import Console
from rich.pretty import pprint

from servicefoundry import Application


def generate_code(
    symbols_to_import: List[str],
    application_type: str,
    spec_repr: str,
    workspace_fqn: str,
):
    symbols = ",".join(symbols_to_import)
    code = f"""\
import logging
from truefoundry.deploy import (
    {symbols},
)
logging.basicConfig(level=logging.INFO)

{application_type} = {spec_repr}

{application_type}.deploy(workspace_fqn="{workspace_fqn}")\
"""
    return code


def extract_class_names(code):
    tree = ast.parse(code)

    # Function to extract keywords from the AST
    def extract_class_names_from_ast_tree(node):
        keywords = set()
        for child_node in ast.iter_child_nodes(node):
            if isinstance(child_node, ast.Call):
                keywords.add(child_node.func.id)
            keywords.update(extract_class_names_from_ast_tree(child_node))
        return keywords

    # Get keywords from the main body of the code
    main_keywords = extract_class_names_from_ast_tree(tree)
    return list(main_keywords)


def replace_enums_with_values(raw_str):
    # required to replace enums of format <AppProtocol.HTTP: 'http'> with 'http'
    pattern = r'<([a-zA-Z0-9_]+).[a-zA-Z0-9_]+: [\'"](.+)[\'"]>'
    replacement = r"'\2'"

    result = re.sub(pattern, replacement, raw_str)
    return result


def remove_none_type_fields(code):
    lines = code.split("\n")
    new_lines = [
        line
        for line in lines
        if not (line.endswith("=None") or line.endswith("=None,"))
    ]
    formatted_code = "\n".join(new_lines)
    return formatted_code


def remove_type_field(code):
    lines = code.split("\n")
    new_lines = [re.sub(r'^[ \t]*type=[\'"][^"]*[\'"],', "", line) for line in lines]
    return "\n".join(new_lines)


def add_deploy_line(code, workspace_fqn, application_type):
    deploy_line = f"{application_type}.deploy('workspace_fqn={workspace_fqn}')"
    return code + "\n" + deploy_line


def get_python_repr(obj):
    stream = io.StringIO()
    console = Console(file=stream, no_color=True, highlighter=None)
    pprint(obj, expand_all=True, console=console, indent_guides=False)
    return stream.getvalue()


COMMENT_FOR_LOCAL_SOURCE = """# Set build_source=LocalSource(local_build=False), in order to deploy code from your local.
# With local_build=False flag, docker image will be built on cloud instead of local
# Else it will try to use docker installed on your local machine to build the image"""


def add_local_source_comment(code):
    lines = code.split("\n")
    new_lines = []
    for line in lines:
        if line.lstrip(" ").startswith("build_source=GitSource"):
            new_lines.append(COMMENT_FOR_LOCAL_SOURCE)
        new_lines.append(line)
    return "\n".join(new_lines)


def convert_deployment_config_to_python(workspace_fqn: str, deployment_config: dict):
    """
    Convert a deployment config to a python file that can be used to deploy to a workspace
    """
    application = Application.parse_obj(deployment_config)
    application_type = application.__root__.type

    spec_repr = get_python_repr(application.__root__)
    spec_repr = replace_enums_with_values(spec_repr)
    spec_repr = remove_none_type_fields(spec_repr)
    spec_repr = remove_type_field(spec_repr)

    # extract class names to import
    symbols_to_import = extract_class_names(spec_repr)

    # check if GitSource exists in array of symbols to import
    if "GitSource" in symbols_to_import:
        symbols_to_import.append("LocalSource")

    generated_code = generate_code(
        symbols_to_import=symbols_to_import,
        application_type=application_type,
        spec_repr=spec_repr,
        workspace_fqn=workspace_fqn,
    )

    if "GitSource" in symbols_to_import:
        generated_code = add_local_source_comment(generated_code)

    return generated_code

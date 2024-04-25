SFY = "sfy"

# TODO: probably create another `rich_messages.py` and apply all formatting there
PROMPT_LOGOUT_SUCCESSFUL = f"""[green bold]Logged Out![/]"""
PROMPT_ALREADY_LOGGED_OUT = f"""[yellow]You are already logged out[/]"""
PROMPT_CREATING_NEW_WORKSPACE = f"""[yellow]Creating a new workspace {{!r}}[/]"""
PROMPT_DELETED_WORKSPACE = f"""[green]Deleted workspace {{!r}}[/]"""
PROMPT_DELETED_APPLICATION = f"""[green]Deleted Application {{!r}}[/]"""
PROMPT_NO_WORKSPACES = f"""[yellow]No workspaces found. Either cluster name is wrong, or your cluster doesn't contain any workspaces. You can create one with [bold]{SFY} create workspace[/][/]"""
PROMPT_NO_APPLICATIONS = f"""[yellow]No applications found. You can create one with [bold]{SFY} deploy[/] from within your application folder"""
PROMPT_NO_VERSIONS = f"""[yellow]No application versions found."""

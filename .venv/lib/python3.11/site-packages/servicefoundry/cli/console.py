from rich.console import Console

# TODO: this file should not exist here, it is being imported even outside cli
#       moreover there is RichOutputCallBack now which can be used instead of console directly
console = Console(soft_wrap=True)

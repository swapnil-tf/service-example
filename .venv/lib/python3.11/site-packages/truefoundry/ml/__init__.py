try:
    from mlfoundry import *  # noqa: F403
except ImportError:
    print(
        "To use metadata/artifact logging features, please run 'pip install truefoundry[ml]'."
    )

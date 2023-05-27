"""
Define additonal roles commonly used in presentations.

:small:{text}:``str``
:vspace:{number_of_lines}:``int``
"""


# Define the role
from docutils.parsers.rst import roles
from docutils import nodes


def small_role(role, rawtext, text, lineno, inliner, options={}, content=[]):
    node = nodes.inline(rawtext, text, **options)
    node["classes"] = ["small"]
    return [node], []


def vspace_role(role, rawtext, text, lineno, inliner, options={}, content=[]):
    try:
        nb_lines = int(text)
    except ValueError:
        print("Error in ", rawtext, ": argument should be an integer.")
        nb_lines = 0
    node = nodes.raw("", "<br>" * nb_lines, format="html")
    return [node], []


roles.register_local_role("small", small_role)
roles.register_local_role("vspace", vspace_role)

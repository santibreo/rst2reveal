from __future__ import annotations
from docutils import nodes
from docutils.transforms import Transform
from collections import defaultdict

class HTMLAttributeTransform(Transform):
    """
    Move the "data" attribute specified in the "pending" node into the
    immediately following non-comment element.
    """

    default_priority: int = 211

    def apply(self) -> None:
        pending = self.startnode
        parent = pending.parent
        child = pending
        while parent:
            # Check for appropriate following siblings:
            for index in range(parent.index(child) + 1, len(parent)):
                element = parent[index]
                if (isinstance(element, nodes.Invisible)
                    or isinstance(element, nodes.system_message)):
                    continue
                element.attributes.setdefault(
                    'html_attributes', defaultdict(list)
                )
                for key, val in pending.details.items():
                    element.attributes['html_attributes'][key].append(val)
                pending.parent.remove(pending)
                return
            else:
                # At end of section or container; apply to sibling
                child = parent
                parent = parent.parent
        error = self.document.reporter.error(
            'No suitable element following "%s" directive'
            % pending.details['directive'],
            nodes.literal_block(pending.rawsource, pending.rawsource),
            line=pending.line)
        pending.replace_self(error)

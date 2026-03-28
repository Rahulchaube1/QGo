# Copyright (c) 2024 Rahul Chaube. All Rights Reserved.
#
# QGo — AI Coding Assistant
# Author: Rahul Chaube
# License: Apache-2.0

"""Code editing engines for QGo."""

from qgo.coders.architect_coder import ArchitectCoder
from qgo.coders.base_coder import BaseCoder
from qgo.coders.editblock_coder import EditBlockCoder
from qgo.coders.udiff_coder import UDiffCoder
from qgo.coders.whole_coder import WholeCoder
from qgo.models import EditFormat


def get_coder(edit_format: EditFormat | str, **kwargs) -> BaseCoder:
    """Factory: return the appropriate coder for the given edit format."""
    fmt = EditFormat(edit_format) if isinstance(edit_format, str) else edit_format
    mapping = {
        EditFormat.EDITBLOCK: EditBlockCoder,
        EditFormat.WHOLE: WholeCoder,
        EditFormat.UDIFF: UDiffCoder,
        EditFormat.ARCHITECT: ArchitectCoder,
    }
    cls = mapping.get(fmt, EditBlockCoder)
    return cls(**kwargs)


__all__ = [
    "BaseCoder", "EditBlockCoder", "WholeCoder",
    "UDiffCoder", "ArchitectCoder", "get_coder",
]

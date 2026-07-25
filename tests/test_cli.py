from __future__ import annotations

import pytest


def test_render_gets_a_message_callback_not_a_counter() -> None:
    """`render()` reports status strings; the staged commands report counts.

    Passing the counter callback to render raised
    `TypeError: cb() missing 1 required positional argument: 'total'` deep
    inside the render, after every clip had already been encoded.
    """
    from mashup.cli import _progress, _status

    _status("x")("some message")  # one positional arg, as render calls it
    _progress("x")(1, 2)  # two, as enrich/embed call it

    with pytest.raises(TypeError):
        _progress("x")("some message")

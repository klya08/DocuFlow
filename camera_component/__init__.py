import os
import streamlit.components.v1 as components


_COMPONENT_DIR = os.path.join(
    os.path.dirname(__file__),
    "frontend"
)


_camera = components.declare_component(
    "docuflow_camera",
    path=_COMPONENT_DIR
)


def camera(key=None):

    return _camera(
        key=key,
        default=None
    )
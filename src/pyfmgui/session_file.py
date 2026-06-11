"""
PyFMGUI session file (.pyfmsession) serialization/deserialization.

A .pyfmsession file is a plain JSON file containing:
  - file_paths: list of absolute paths to all loaded data files
  - widget_params: dict mapping widget name -> flat param dict  {group/name: value}
  - global_k / global_involts: optional global calibration overrides
  - export_range: [from_1based, to_1based] for the HTML export spinboxes
"""

import json
import os

EXTENSION = ".pyfmsession"
MAGIC = "PyFMGUI_session_v1"

# ---------------------------------------------------------------------------
# Helpers to serialise / deserialise a pyqtgraph ParameterTree
# ---------------------------------------------------------------------------

def _params_to_dict(params_root):
    """Walk a pyqtgraph Parameter tree and return {path: value}."""
    out = {}
    for item in params_root:          # iterates over top-level children
        _walk(item, item.name(), out)
    return out


def _walk(param, prefix, out):
    if param.hasChildren():
        for child in param:
            _walk(child, f"{prefix}/{child.name()}", out)
    else:
        try:
            out[prefix] = param.value()
        except Exception:
            pass


def _apply_dict_to_params(params_root, flat):
    """Apply a {path: value} dict back onto a Parameter tree (best-effort)."""
    for path, value in flat.items():
        parts = path.split("/")
        try:
            node = params_root
            for part in parts:
                node = node.child(part)
            node.setValue(value)
        except Exception:
            pass  # param may not exist in this widget version – skip silently


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def save_session(path, session, widgets: dict):
    """
    Persist the current session to *path*.

    Parameters
    ----------
    path    : str  – destination file path (should end in .pyfmsession)
    session : Session object
    widgets : dict mapping label -> widget, e.g.
                {"HertzFit": hertz_fit_widget, "TingFit": ting_fit_widget, ...}
              Widgets that are None are skipped.
    """
    data = {
        "magic": MAGIC,
        "file_paths": list(session.loaded_files_paths),
        "global_k": session.global_k,
        "global_involts": session.global_involts,
        "widget_params": {},
    }

    for label, widget in widgets.items():
        if widget is None:
            continue
        if not hasattr(widget, "params"):
            continue
        try:
            data["widget_params"][label] = _params_to_dict(widget.params)
        except Exception:
            pass

    # Export-range spinboxes (HertzFit specific)
    hertz = widgets.get("HertzFit")
    if hertz is not None and hasattr(hertz, "exportRangeFrom"):
        data["export_range"] = [
            hertz.exportRangeFrom.value(),
            hertz.exportRangeTo.value(),
        ]

    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, default=_json_safe)


def _json_safe(obj):
    """Fallback JSON serialiser for non-serialisable values."""
    try:
        return float(obj)
    except (TypeError, ValueError):
        return str(obj)


def load_session(path):
    """
    Load a .pyfmsession file and return its contents as a dict.

    Returns None if the file cannot be read or has an unexpected format.
    """
    if not os.path.isfile(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        if data.get("magic") != MAGIC:
            return None
        return data
    except Exception:
        return None


def apply_session(data, session, widgets: dict):
    """
    Apply previously-loaded session data (from load_session) to widgets.

    Parameters
    ----------
    data    : dict returned by load_session()
    session : Session object
    widgets : same dict as passed to save_session()
    """
    if data is None:
        return

    # Restore global calibration overrides
    if data.get("global_k") is not None:
        session.global_k = data["global_k"]
    if data.get("global_involts") is not None:
        session.global_involts = data["global_involts"]

    # Restore parameter trees
    widget_params = data.get("widget_params", {})
    for label, flat in widget_params.items():
        widget = widgets.get(label)
        if widget is None or not hasattr(widget, "params"):
            continue
        try:
            _apply_dict_to_params(widget.params, flat)
        except Exception:
            pass

    # Restore export-range spinboxes
    export_range = data.get("export_range")
    hertz = widgets.get("HertzFit")
    if hertz is not None and export_range and hasattr(hertz, "exportRangeFrom"):
        hertz.exportRangeFrom.setValue(export_range[0])
        hertz.exportRangeTo.setValue(export_range[1])

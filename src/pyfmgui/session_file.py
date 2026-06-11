"""
PyFMGUI session file (.pyfmsession) serialization/deserialization.

A .pyfmsession file is a plain JSON file containing:
  - file_paths        : list of absolute paths to all loaded data files
  - file_metadata     : dict {file_id -> filemetadata fields} cached from file objects
  - widget_params     : dict {widget_label -> flat {group/name: value}}
  - hertz_fit_results : dict {file_id -> [ [curve_idx, result_dict], ... ]}
  - global_k / global_involts : optional global calibration overrides
  - export_range      : [from_1based, to_1based] for the HTML export spinboxes
"""

import json
import os
import numpy as np

EXTENSION = ".pyfmsession"
MAGIC = "PyFMGUI_session_v2"

# Filemetadata keys worth caching (enough to populate the param tree and display
# without needing to re-open the raw data file)
_META_KEYS = [
    'Entry_filename', 'file_path', 'file_type',
    'spring_const_Nbym', 'defl_sens_nmbyV',
    'height_channel_key', 'mapping_bool',
    'Entry_date', 'Entry_time',
    'num_curves', 'num_segments',
    'x_size', 'y_size', 'scan_size_x', 'scan_size_y',
]

# HertzModel scalar fields needed to reconstruct eval() / get_residuals()
_HERTZ_FIT_FIELDS = [
    'E0', 'delta0', 'f0', 'slope',
    'ind_geom', 'tip_parameter', 'poisson_ratio',
    'correction_model', 'fit_hline_flag',
    'redchi', 'Rsquared', 'MAE', 'RMSE',
]


# ---------------------------------------------------------------------------
# Parameter-tree helpers
# ---------------------------------------------------------------------------

def _params_to_dict(params_root):
    out = {}
    for item in params_root:
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
    for path, value in flat.items():
        parts = path.split("/")
        try:
            node = params_root
            for part in parts:
                node = node.child(part)
            node.setValue(value)
        except Exception:
            pass


# ---------------------------------------------------------------------------
# File-path collection
# ---------------------------------------------------------------------------

def _collect_file_paths(session):
    paths = []
    seen = set()
    for key, file_obj in session.loaded_files.items():
        path = None
        try:
            path = file_obj.filemetadata.get('file_path')
        except Exception:
            pass
        if not path:
            path = key
        if path and path not in seen:
            paths.append(path)
            seen.add(path)
    for p in session.loaded_files_paths:
        if p not in seen:
            paths.append(p)
            seen.add(p)
    return paths


# ---------------------------------------------------------------------------
# File metadata caching
# ---------------------------------------------------------------------------

def _collect_file_metadata(session):
    """Return {file_id: {key: value}} for every loaded file."""
    out = {}
    for file_id, file_obj in session.loaded_files.items():
        try:
            meta = file_obj.filemetadata
            out[file_id] = {k: _json_safe_val(meta.get(k)) for k in _META_KEYS if k in meta}
        except Exception:
            pass
    return out


# ---------------------------------------------------------------------------
# Hertz fit result serialization / reconstruction
# ---------------------------------------------------------------------------

def _serialize_hertz_results(session):
    """
    Convert session.hertz_fit_results to a JSON-safe structure.

    session.hertz_fit_results = {file_id: [(curve_idx, HertzModel), ...]}
    Saved as                   = {file_id: [[curve_idx, {field: val}], ...]}
    """
    out = {}
    for file_id, curve_list in session.hertz_fit_results.items():
        serialized_curves = []
        for curve_idx, result in curve_list:
            if result is None:
                serialized_curves.append([curve_idx, None])
                continue
            r = {}
            for field in _HERTZ_FIT_FIELDS:
                val = getattr(result, field, None)
                r[field] = _json_safe_val(val)
            serialized_curves.append([curve_idx, r])
        out[file_id] = serialized_curves
    return out


def _json_safe_val(val):
    """Convert a value to something JSON can handle."""
    if val is None:
        return None
    if isinstance(val, (bool, str)):
        return val
    if isinstance(val, (int, float)):
        if np.isnan(val) or np.isinf(val):
            return None
        return val
    if isinstance(val, np.integer):
        return int(val)
    if isinstance(val, np.floating):
        v = float(val)
        return None if (np.isnan(v) or np.isinf(v)) else v
    if isinstance(val, np.ndarray):
        return val.tolist()
    try:
        return float(val)
    except (TypeError, ValueError):
        return str(val)


def _reconstruct_hertz_results(saved):
    """
    Rebuild session.hertz_fit_results from the saved JSON structure.

    Returns {file_id: [(curve_idx, _RestoredHertzResult | None), ...]}
    """
    if not saved:
        return {}
    out = {}
    for file_id, curve_list in saved.items():
        restored = []
        for entry in curve_list:
            curve_idx, r = entry
            if r is None:
                restored.append((curve_idx, None))
            else:
                restored.append((curve_idx, _RestoredHertzResult(r)))
        out[file_id] = restored
    return out


class _RestoredHertzResult:
    """
    Lightweight stand-in for a HertzModel object that supports the attributes
    and methods used by hertzfit_widget (E0, delta0, f0, redchi, eval(),
    get_residuals()).
    """
    def __init__(self, d: dict):
        for field in _HERTZ_FIT_FIELDS:
            setattr(self, field, d.get(field))

    def eval(self, indentation, sample_height=None):
        """Reconstruct the Hertz force curve from saved parameters."""
        try:
            from pyfmrheo.models.hertz import get_coeff
            coeff, n = get_coeff(self.ind_geom, self.tip_parameter, self.poisson_ratio or 0.5)
        except Exception:
            # Fallback: paraboloid approximation
            coeff, n = (4.0 / 3.0) * (self.tip_parameter or 75e-9) ** 0.5, 1.5

        delta0 = self.delta0 or 0.0
        E0     = self.E0     or 0.0
        f0     = self.f0     or 0.0
        slope  = self.slope  or 0.0

        ind = np.asarray(indentation, dtype=float)
        force = np.zeros_like(ind)
        contact = ind > delta0
        d = ind[contact] - delta0
        force[contact] = coeff * E0 * d ** n + f0

        if self.fit_hline_flag and slope:
            force += slope * (ind - delta0)

        return force

    def get_residuals(self, indentation, force, sample_height=None):
        return np.asarray(force) - self.eval(indentation, sample_height)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def _json_safe(obj):
    return _json_safe_val(obj) if _json_safe_val(obj) is not None else str(obj)


def save_session(path, session, widgets: dict):
    """
    Persist the current session to *path*.

    Saves: file paths, per-file metadata, Hertz fit results,
           all parameter-tree values, and global calibration overrides.
    """
    data = {
        "magic": MAGIC,
        "file_paths":        _collect_file_paths(session),
        "file_metadata":     _collect_file_metadata(session),
        "hertz_fit_results": _serialize_hertz_results(session),
        "global_k":          session.global_k,
        "global_involts":    session.global_involts,
        "widget_params":     {},
    }

    for label, widget in widgets.items():
        if widget is None or not hasattr(widget, "params"):
            # Fall back to the cached params from last time the widget was open
            cached = getattr(session, 'widget_params_cache', {}).get(label)
            if cached:
                data["widget_params"][label] = cached
            continue
        try:
            data["widget_params"][label] = _params_to_dict(widget.params)
        except Exception:
            pass

    hertz = widgets.get("HertzFit")
    if hertz is not None and hasattr(hertz, "exportRangeFrom"):
        data["export_range"] = [
            hertz.exportRangeFrom.value(),
            hertz.exportRangeTo.value(),
        ]

    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, default=_json_safe)


def load_session(path):
    """Load a .pyfmsession file.  Returns None on failure."""
    if not os.path.isfile(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        if data.get("magic") not in (MAGIC, "PyFMGUI_session_v1"):
            return None
        return data
    except Exception:
        return None


def apply_session(data, session, widgets: dict):
    """
    Restore a previously-saved session onto *session* and *widgets*.

    Restores: global calibration, parameter trees, Hertz fit results,
              export-range spinboxes.
    The cached file_metadata is stored on session.cached_file_metadata so
    widgets can read it without re-opening files.
    """
    if data is None:
        return

    if data.get("global_k") is not None:
        session.global_k = data["global_k"]
    if data.get("global_involts") is not None:
        session.global_involts = data["global_involts"]

    # Cache file metadata so widgets can access it
    session.cached_file_metadata = data.get("file_metadata", {})

    # Store widget params for deferred application (widgets may not be open yet)
    incoming = data.get("widget_params", {})
    session.pending_widget_params = dict(incoming)
    # Also update the persistent cache so Save Session works even if widget is closed
    if not hasattr(session, 'widget_params_cache'):
        session.widget_params_cache = {}
    for label, flat in incoming.items():
        if flat:
            session.widget_params_cache[label] = flat

    # Restore Hertz fit results
    saved_hertz = data.get("hertz_fit_results", {})
    if saved_hertz:
        restored = _reconstruct_hertz_results(saved_hertz)
        # Merge into session (don't overwrite freshly computed results)
        for file_id, curve_list in restored.items():
            if file_id not in session.hertz_fit_results:
                session.hertz_fit_results[file_id] = curve_list

    # Restore parameter trees
    for label, flat in data.get("widget_params", {}).items():
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

def _collect_file_paths(session):
    """
    Return a list of absolute file paths for all loaded files.

    Tries three sources in order:
      1. filemetadata['file_path'] on each loaded file object
      2. session.loaded_files_paths (populated by some file types)
      3. The dict key itself as a last-resort fallback
    """
    paths = []
    seen = set()
    for key, file_obj in session.loaded_files.items():
        path = None
        try:
            path = file_obj.filemetadata.get('file_path')
        except Exception:
            pass
        if not path:
            path = key  # fallback – may be just a filename, but better than nothing
        if path and path not in seen:
            paths.append(path)
            seen.add(path)
    # Also include anything in loaded_files_paths not already captured
    for p in session.loaded_files_paths:
        if p not in seen:
            paths.append(p)
            seen.add(p)
    return paths


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
        "file_paths": _collect_file_paths(session),
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

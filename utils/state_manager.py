"""
Session State Manager
Handles state persistence across pages
"""

import os
import json
import re
import shutil
import uuid

import streamlit as st
import pandas as pd
from typing import Optional, Dict, Any
from datetime import datetime

# ---------------------------------------------------------------------------
# Per-visitor cache. The run id lives in the page URL so a refresh restores
# only that visitor's files, not another session's catalog.
# ---------------------------------------------------------------------------
_CACHE_DIR = os.path.join(os.path.dirname(__file__), '..', 'temp', 'runs')
_RUN_ID_RE = re.compile(r'^[a-f0-9]{32}$')

_META_KEYS = (
    'product_type',
    'phase_1_complete', 'phase_2_complete', 'phase_3_complete',
    'total_products', 'categories_count', 'keywords_generated',
    'snapshot_month',
)

MAX_ZIP_BYTES = 50 * 1024 * 1024


def _valid_run_id(value: str) -> bool:
    return bool(value) and bool(_RUN_ID_RE.match(value))


def _run_dir(run_id: str) -> str:
    return os.path.join(_CACHE_DIR, run_id)


def _cache_paths(run_id: str) -> tuple[str, str]:
    folder = _run_dir(run_id)
    return os.path.join(folder, 'pipeline.csv'), os.path.join(folder, 'meta.json')


def _ensure_run_id() -> str:
    """Bind this browser session to its own cache folder."""
    current = st.session_state.get('run_id')
    if _valid_run_id(str(current or '')):
        run_id = str(current)
    else:
        requested = ''
        try:
            requested = st.query_params.get('run', '') or ''
        except Exception:
            requested = ''
        if isinstance(requested, list):
            requested = requested[0] if requested else ''
        if _valid_run_id(str(requested)) and os.path.isdir(_run_dir(str(requested))):
            run_id = str(requested)
        else:
            run_id = uuid.uuid4().hex
        st.session_state['run_id'] = run_id
    try:
        if st.query_params.get('run') != run_id:
            st.query_params['run'] = run_id
    except Exception:
        pass
    return run_id


def _persist():
    """Write consolidated_df + key metadata to this visitor's folder."""
    df = st.session_state.get('consolidated_df')
    if df is None:
        return
    try:
        run_id = _ensure_run_id()
        folder = _run_dir(run_id)
        os.makedirs(folder, exist_ok=True)
        csv_path, meta_path = _cache_paths(run_id)
        df = df.loc[:, ~df.columns.duplicated(keep='first')]
        df.to_csv(csv_path, index=False)
        meta = {k: st.session_state.get(k) for k in _META_KEYS}
        with open(meta_path, 'w') as f:
            json.dump(meta, f)
    except Exception:
        pass


def _restore():
    """Reload this visitor's run when the URL still points at it."""
    if st.session_state.get('phase_1_complete'):
        return
    run_id = _ensure_run_id()
    csv_path, meta_path = _cache_paths(run_id)
    if not (os.path.exists(csv_path) and os.path.exists(meta_path)):
        return
    try:
        df = pd.read_csv(csv_path)
        df = df.loc[:, ~df.columns.duplicated(keep='first')]
        with open(meta_path, 'r') as f:
            meta = json.load(f)
        st.session_state['consolidated_df'] = df
        for key in _META_KEYS:
            if key in meta:
                st.session_state[key] = meta[key]
    except Exception:
        pass  # corrupted cache — ignore, visitor can re-run Phase 1


# Public alias so Phase 3 (or any page) can trigger a save after
# modifying consolidated_df directly.
save_pipeline_state = _persist


def init_session_state():
    """Initialize session state with default values"""
    defaults = {
        # Data flow between pages
        'product_type': None,
        'monthly_data': None,
        'consolidated_df': None,

        # Phase completion status
        'phase_1_complete': False,
        'phase_2_complete': False,
        'phase_3_complete': False,
        'phase_4_complete': False,
        'phase_5_complete': False,

        # UI state
        'current_phase': 1,

        # Metadata
        'last_updated': None,
        'total_products': 0,
        'categories_count': 0,
        'keywords_generated': 0,
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

    # Attempt to restore from disk if this is a fresh session
    _restore()


def save_consolidation_results(
    product_type: str,
    monthly_data: Dict,
    consolidated_df: pd.DataFrame
):
    """Save Phase 1 consolidation results to session state"""
    st.session_state.product_type = product_type
    st.session_state.monthly_data = monthly_data
    st.session_state.consolidated_df = consolidated_df
    st.session_state.phase_1_complete = True
    st.session_state.last_updated = datetime.now()
    st.session_state.total_products = len(consolidated_df)

    # Count unique categories (L3 - most specific)
    if 'Product Category L3' in consolidated_df.columns:
        st.session_state.categories_count = consolidated_df['Product Category L3'].nunique()

    _persist()


def save_keyword_results(updated_df: pd.DataFrame):
    """Save Phase 2 keyword generation results to session state"""
    st.session_state.consolidated_df = updated_df
    st.session_state.phase_2_complete = True
    st.session_state.last_updated = datetime.now()

    # Count keywords generated
    if 'Product Keyword' in updated_df.columns:
        st.session_state.keywords_generated = (updated_df['Product Keyword'] != '').sum()

    _persist()


def check_phase_prerequisites(phase_num: int) -> tuple[bool, str]:
    """
    Check if prerequisites for a phase are met

    Returns:
        (is_ready, message)
    """
    if phase_num == 1:
        return True, ""

    if phase_num == 2:
        if not st.session_state.phase_1_complete:
            return False, "Please complete Phase 1 (Data Consolidation) first."
        return True, ""

    if phase_num == 3:
        # Search volume is optional and does not block later phases.
        return True, ""

    if phase_num == 4:
        if not st.session_state.phase_1_complete:
            return False, "Please complete Phase 1 (Data Consolidation) first."
        # Phase 4 doesn't strictly require Phase 2, but we can recommend it
        return True, ""

    if phase_num == 5:
        if not st.session_state.phase_1_complete:
            return False, "Please complete Phase 1 (Data Consolidation) first."
        return True, ""

    return False, "Invalid phase number"


def get_phase_status(phase_num: int) -> str:
    """
    Get status for a phase

    Returns:
        Status string: "Complete", "Ready", "Pending", "In Progress", etc.
    """
    status_map = {
        1: st.session_state.phase_1_complete,
        2: st.session_state.phase_2_complete,
        3: st.session_state.phase_3_complete,
        4: st.session_state.phase_4_complete,
        5: st.session_state.phase_5_complete,
    }

    if phase_num == 3 and not status_map.get(3, False):
        return "Optional"

    # Check completion
    if status_map.get(phase_num, False):
        return "Complete"

    # Check if prerequisites are met
    is_ready, _ = check_phase_prerequisites(phase_num)

    if is_ready:
        return "Ready"
    else:
        return "Pending"


def get_session_stats() -> Optional[Dict[str, Any]]:
    """
    Get current session statistics for homepage display

    Returns:
        Dictionary of stats or None if no data exists
    """
    if not st.session_state.phase_1_complete:
        return None

    stats = {
        'product_type': st.session_state.product_type or 'Unknown',
        'total_products': st.session_state.total_products,
        'categories_count': st.session_state.categories_count,
        'keywords_generated': st.session_state.keywords_generated,
        'last_updated': st.session_state.last_updated,
    }

    return stats


def clear_session_data():
    """Clear this visitor's session and their cache folder."""
    run_id = st.session_state.get('run_id')
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    if _valid_run_id(str(run_id or '')):
        try:
            shutil.rmtree(_run_dir(str(run_id)), ignore_errors=True)
        except Exception:
            pass
    try:
        if 'run' in st.query_params:
            del st.query_params['run']
    except Exception:
        pass
    init_session_state()


def get_consolidated_df() -> Optional[pd.DataFrame]:
    """Safely retrieve consolidated DataFrame from session state"""
    return st.session_state.get('consolidated_df', None)


def has_data() -> bool:
    """Check if any data exists in session"""
    return st.session_state.get('phase_1_complete', False)

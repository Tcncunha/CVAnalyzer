"""
Application Tracker — UI module for registering and tracking job applications.

Provides a dashboard with statistics, a registration form, an applications
list with inline editing, and a "clear all" safety valve.
"""

import streamlit as st

from i18n import t
from tracker_manager import (
    add_application,
    clear_all,
    delete_application,
    get_stats,
    init_db,
    list_applications,
    update_application,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_STATUS_OPTIONS = ["applied", "interview", "offer", "rejected", "ghosted"]

_STATUS_LABELS: dict[str, str] = {
    "applied": "status_applied",
    "interview": "status_interview",
    "offer": "status_offer",
    "rejected": "status_rejected",
    "ghosted": "status_ghosted",
}


# ---------------------------------------------------------------------------
# Session-notice helpers (success messages survive st.rerun)
# ---------------------------------------------------------------------------

def _show_pending_success() -> None:
    """Render and consume any pending success message from a prior rerun."""
    notice = st.session_state.pop("_tracker_notice", "")
    if notice:
        st.success(notice)


def _notify_and_rerun(message: str) -> None:
    """Store a success message and rerun so the page refreshes with fresh data."""
    st.session_state["_tracker_notice"] = message
    st.rerun()


# ---------------------------------------------------------------------------
# Public render function — called by app.py
# ---------------------------------------------------------------------------

def render_tracker_page() -> None:
    """Render the full Application Tracker page."""
    init_db()
    _show_pending_success()

    st.header(t("tracker_header"))
    st.caption(t("tracker_caption"))

    # ---- Register Form ---------------------------------------------------
    _render_registration_form()

    st.divider()

    # ---- Dashboard / Stats -----------------------------------------------
    applications = list_applications()

    if not applications:
        st.info(t("tracker_no_data"))
        _render_clear_all()
        return

    _render_dashboard(applications)

    st.divider()

    # ---- Applications List -----------------------------------------------
    _render_applications_list(applications)

    st.divider()

    # ---- Clear All -------------------------------------------------------
    _render_clear_all()


# ---------------------------------------------------------------------------
# Registration form
# ---------------------------------------------------------------------------

def _render_registration_form() -> None:
    """Render the new-application registration form inside an expander."""
    with st.expander(t("tracker_register"), expanded=True):
        with st.form("tracker_register_form", clear_on_submit=True):
            company = st.text_input(t("tracker_company"))
            role = st.text_input(t("tracker_role"))
            cv_version = st.text_input(t("tracker_cv_version"))
            job_url = st.text_input(t("tracker_job_url"))
            notes = st.text_area(t("tracker_notes"))

            submitted = st.form_submit_button(t("tracker_register"), use_container_width=True)

            if submitted:
                if not company.strip():
                    st.warning(t("tracker_company_required"))
                    return
                if not role.strip():
                    st.warning(t("tracker_role_required"))
                    return
                add_application(
                    company=company.strip(),
                    role=role.strip(),
                    cv_version=cv_version.strip(),
                    job_url=job_url.strip(),
                    notes=notes.strip(),
                )
                _notify_and_rerun(t("tracker_registered"))


# ---------------------------------------------------------------------------
# Dashboard statistics
# ---------------------------------------------------------------------------

def _render_dashboard(applications: list[dict]) -> None:
    """Render KPI metrics and conversion rates, optionally filtered by CV version."""
    all_versions = sorted({a["cv_version"] for a in applications if a["cv_version"]})

    filter_options = [t("tracker_all")] + all_versions
    selected_filter = st.selectbox(
        t("tracker_filter_version"),
        options=filter_options,
        key="tracker_version_filter",
    )

    filter_version = None if selected_filter == t("tracker_all") else selected_filter
    stats = get_stats(cv_version=filter_version)

    total = stats["total"]
    by_status = stats["by_status"]

    st.subheader(t("tracker_stats_header"))

    col_total, col_interviews, col_offers, col_rejected, col_ghosted = st.columns(5)
    col_total.metric(t("tracker_total"), total)
    col_interviews.metric(t("tracker_interviews"), by_status.get("interview", 0))
    col_offers.metric(t("tracker_offers"), by_status.get("offer", 0))
    col_rejected.metric(t("tracker_rejected"), by_status.get("rejected", 0))
    col_ghosted.metric(t("tracker_ghosted"), by_status.get("ghosted", 0))

    st.caption(
        f"{t('tracker_conv_interview')}: **{stats['conversion_interview']}%** "
        f"&nbsp;&nbsp;|&nbsp;&nbsp; "
        f"{t('tracker_conv_offer')}: **{stats['conversion_offer']}%**"
    )


# ---------------------------------------------------------------------------
# Applications list
# ---------------------------------------------------------------------------

def _render_applications_list(applications: list[dict]) -> None:
    """Render each application inside its own expander with inline editing."""
    for app_data in applications:
        app_id = app_data["id"]
        title = f"{app_data['company']} — {app_data['role']}"

        with st.expander(title, expanded=False):
            st.caption(
                f"**{t('tracker_status')}:** "
                f"{t(_STATUS_LABELS.get(app_data['status'], 'status_applied'))}"
            )
            st.caption(f"🕒 {app_data['applied_date']}  ·  ✏️ {app_data['updated_date']}")

            # Status selectbox
            current_status_index = (
                _STATUS_OPTIONS.index(app_data["status"])
                if app_data["status"] in _STATUS_OPTIONS
                else 0
            )
            new_status = st.selectbox(
                t("tracker_status"),
                options=_STATUS_OPTIONS,
                format_func=lambda s: t(_STATUS_LABELS[s]),
                index=current_status_index,
                key=f"tracker_status_{app_id}",
            )

            # Editable notes
            new_notes = st.text_area(
                t("tracker_notes"),
                value=app_data.get("notes", ""),
                key=f"tracker_notes_{app_id}",
            )

            # Follow-up date
            new_follow_up = st.text_input(
                t("tracker_followup_date"),
                value=app_data.get("follow_up_date", ""),
                key=f"tracker_followup_{app_id}",
            )

            # Action buttons: update + delete
            col_update, col_delete = st.columns([3, 1])

            with col_update:
                if st.button(
                    t("tracker_update"),
                    key=f"tracker_update_btn_{app_id}",
                    use_container_width=True,
                ):
                    update_application(
                        app_id=app_id,
                        status=new_status,
                        notes=new_notes,
                        follow_up_date=new_follow_up,
                    )
                    st.rerun()

            with col_delete:
                st.checkbox(
                    t("tracker_delete"),
                    key=f"tracker_del_check_{app_id}",
                    help=t("tracker_delete"),
                    label_visibility="collapsed",
                )
                if st.button(
                    t("tracker_delete"),
                    key=f"tracker_del_btn_{app_id}",
                    use_container_width=True,
                ):
                    if st.session_state.get(f"tracker_del_check_{app_id}", False):
                        delete_application(app_id)
                        _notify_and_rerun(t("tracker_deleted"))
                    else:
                        st.warning(t("tracker_clear_confirm"))


# ---------------------------------------------------------------------------
# Clear all
# ---------------------------------------------------------------------------

def _render_clear_all() -> None:
    """Render a safety-valve 'clear all' control with confirmation."""
    with st.expander(t("tracker_clear"), expanded=False):
        st.warning(t("tracker_clear_confirm"))
        confirm = st.checkbox(
            t("tracker_clear_confirm"),
            key="tracker_clear_confirm_cb",
        )
        if st.button(
            t("tracker_clear"),
            key="tracker_clear_btn",
            use_container_width=True,
        ):
            if confirm:
                clear_all()
                _notify_and_rerun(t("tracker_deleted"))
            else:
                st.info(t("tracker_clear_confirm"))
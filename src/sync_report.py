"""HTML rendering for the sync summary dialog (extracted from sync.py).

Pure string builders: they take SyncStats-like objects and return HTML."""

try:
    from .templates_and_definitions import DEFAULT_STUDENT
except ImportError:  # pragma: no cover - direct (non-package) import in some tests
    from templates_and_definitions import DEFAULT_STUDENT


def _generate_metrics_table_html(stats) -> str:
    """
    Helper to generate the metrics table HTML.

    Args:
        stats: SyncStats object

    Returns:
        str: HTML string
    """
    # Define primary metrics
    # Format: (Icon, Label, Value, StyleClass)
    metrics = [
        ("📋", "Total spreadsheet rows", stats.remote_total_table_lines, ""),
        (
            "✅",
            "Rows with content (Valid ID)",
            stats.remote_valid_note_lines,
            "success",
        ),
        (
            "❌",
            "Rows skipped (Missing ID)",
            stats.remote_invalid_note_lines,
            "error" if stats.remote_invalid_note_lines > 0 else "muted",
        ),
        ("👻", "Empty rows (Ignored)", stats.remote_ignored_ghost_rows, "muted"),
        (
            "🔄",
            "Rows enabled for sync (SYNC=TRUE)",
            stats.remote_sync_marked_lines,
            "info",
        ),
        ("⏸️", "Rows disabled for sync (SYNC=FALSE)", stats.skipped, "muted"),
        ("⏭️", "Notes matched (Unchanged)", stats.unchanged, "muted"),
        (
            "➕",
            "Created notes",
            stats.created,
            "success-bold" if stats.created > 0 else "muted",
        ),
        (
            "✏️",
            "Updated notes",
            stats.updated,
            "warning-bold" if stats.updated > 0 else "muted",
        ),
        (
            "🗑️",
            "Deleted notes",
            stats.deleted,
            "error-bold" if stats.deleted > 0 else "muted",
        ),
        (
            "⚠️",
            "Warnings",
            len(stats.warnings),
            "warning-bold" if len(stats.warnings) > 0 else "muted",
        ),
        ("❌", "Errors", stats.errors, "error-bold" if stats.errors > 0 else "muted"),
    ]

    html = """<div class="metrics-container"><table class="metrics-table">"""

    for icon, label, value, style_class in metrics:
        row_class = "metric-row"
        if style_class == "muted" and value == 0:
            row_class += " zero-value"

        value_display = f'<span class="stat-value {style_class}">{value}</span>'

        html += f"""
        <tr class="{row_class}">
            <td class="icon-col">{icon}</td>
            <td class="label-col">{label}</td>
            <td class="value-col">{value_display}</td>
        </tr>
        """

    # Potential notes section - MERGED into same table with a separator
    html += """
    <tr class="separator-row">
        <td colspan="3"><hr></td>
    </tr>
    """

    potential_metrics = [
        ("🚀", "Total notes to process", stats.remote_total_potential_anki_notes),
        ("🎓", "Notes assigned to students", stats.remote_potential_student_notes),
        (
            "❓",
            f"Notes unassigned (Default to {DEFAULT_STUDENT})",
            stats.remote_potential_missing_students_notes,
        ),
        ("👥", "Total unique students found", stats.remote_unique_students_count),
    ]

    for icon, label, value in potential_metrics:
        html += f"""
        <tr class="metric-row info-row">
            <td class="icon-col">{icon}</td>
            <td class="label-col">{label}</td>
            <td class="value-col">{value}</td>
        </tr>
        """
    html += "</table></div>"

    # Students detail
    if stats.remote_notes_per_student:
        html += '<div class="students-section"><h4>👥 Notes per student:</h4><div class="student-tags">'
        for student, count in sorted(stats.remote_notes_per_student.items()):
            html += f'<span class="student-tag">{student}: <b>{count}</b></span>&nbsp;&nbsp;'
        html += "</div></div>"

    return html


def _generate_details_list_html(title, items, icon="•") -> str:
    """Helper to generate a list of details."""
    if not items:
        return ""

    html = f'<div class="details-block"><h3>{title}</h3><ul>'
    for item in items:
        html += f"<li>{item}</li>"
    html += "</ul></div>"
    return html


def _generate_changes_list_html(title, details, type_class="info") -> str:
    """Helper for created/updated/deleted details."""
    if not details:
        return ""

    html = f'<div class="changes-block {type_class}"><h3>{title}</h3><table class="changes-table">'

    for i, detail in enumerate(details, 1):
        note_info = f"{detail['student']}: {detail['note_id']}"
        extra = ""
        if "pergunta" in detail:
            extra = f"<br><span class='note-extract'>{detail['pergunta']}</span>"

        html += f'<tr><td class="index-col">{i}.</td><td class="note-col"><b>{note_info}</b>{extra}'

        if "changes" in detail:
            html += '<ul class="changes-list">'
            for change in detail["changes"]:
                html += f"<li>{change}</li>"
            html += "</ul>"

        html += "</td></tr>"

    html += "</table></div>"
    return html


def generate_simplified_view(total_stats, sync_errors=None, deck_results=None) -> str:
    """
    Generates simplified (aggregated) HTML view of sync statistics.
    """
    html_parts = []

    # 1. Detailed Remote Metrics (Aggregated)
    if (
        total_stats.remote_total_table_lines > 0
        or total_stats.remote_total_potential_anki_notes > 0
    ):

        html_parts.append(
            '<div class="section-header"><h2>📊 Detailed Remote Deck Metrics</h2></div>'
        )
        html_parts.append(_generate_metrics_table_html(total_stats))

    # 2. Errors
    all_errors = (sync_errors or []) + total_stats.error_details
    if all_errors:
        html_parts.append(
            _generate_details_list_html(f"⚠️ Errors ({len(all_errors)})", all_errors)
        )

    # 2.1 Warnings
    if total_stats.warnings:
        html_parts.append(
            _generate_details_list_html(
                f"⚠️ Warnings ({len(total_stats.warnings)})", total_stats.warnings
            )
        )

    # 3. Created Notes
    if total_stats.created > 0 and total_stats.creation_details:
        html_parts.append(
            _generate_changes_list_html(
                f"➕ Created Notes ({total_stats.created})",
                total_stats.creation_details,
                "created",
            )
        )

    # 4. Updated Notes
    if total_stats.updated > 0 and total_stats.update_details:
        html_parts.append(
            _generate_changes_list_html(
                f"✏️ Updated Notes ({total_stats.updated})",
                total_stats.update_details,
                "updated",
            )
        )

    # 5. Deleted Notes
    if total_stats.deleted > 0 and total_stats.deletion_details:
        html_parts.append(
            _generate_changes_list_html(
                f"🗑️ Deleted Notes ({total_stats.deleted})",
                total_stats.deletion_details,
                "deleted",
            )
        )

    # 6. No Changes Message
    if not (
        total_stats.created > 0
        or total_stats.updated > 0
        or total_stats.deleted > 0
        or all_errors
    ):
        html_parts.append("""
         <div class="no-changes-info">
            <h3>ℹ️ No detailed note modifications</h3>
            <p>This can happen when:</p>
            <ul>
                <li>Notes were already up to date</li>
                <li>Only cleanup operations were performed</li>
                <li>No changes were found in spreadsheet data</li>
            </ul>
         </div>
         """)

    return "".join(html_parts)


def generate_aggregated_summary_only(total_stats, sync_errors=None) -> str:
    """
    Generates only aggregated summary HTML.
    """
    html_parts = []

    # Errors
    all_errors = (sync_errors or []) + total_stats.error_details
    if all_errors:
        html_parts.append(
            _generate_details_list_html(
                f"⚠️ General Errors ({len(all_errors)})", all_errors
            )
        )

    # Warnings
    if total_stats.warnings:
        html_parts.append(
            _generate_details_list_html(
                f"⚠️ Warnings ({len(total_stats.warnings)})", total_stats.warnings
            )
        )

    # Metrics
    if (
        total_stats.remote_total_table_lines > 0
        or total_stats.remote_total_potential_anki_notes > 0
    ):
        html_parts.append(
            '<div class="section-header"><h2>📊 Aggregated Remote Metrics Totals</h2></div>'
        )
        html_parts.append(_generate_metrics_table_html(total_stats))

    return "".join(html_parts)


def generate_deck_detailed_metrics(stats, deck_name) -> str:
    """
    Generates complete detailed metrics HTML for an individual deck.
    """
    html_parts = []

    # Remote Metrics
    if (
        stats.remote_total_table_lines > 0
        or stats.remote_total_potential_anki_notes > 0
    ):
        # Header removed to reduce clutter as requested by implicit design cleanup
        html_parts.append(_generate_metrics_table_html(stats))

    # Note Details

    # Errors
    if stats.errors > 0 or stats.error_details:
        html_parts.append(
            _generate_details_list_html(
                f"⚠️ Errors in {deck_name}", stats.error_details
            )
        )

    # Warnings
    if stats.warnings:
        html_parts.append(
            _generate_details_list_html(f"⚠️ Warnings in {deck_name}", stats.warnings)
        )

    # Created
    if stats.created > 0 and stats.creation_details:
        html_parts.append(
            _generate_changes_list_html(
                f"➕ Created in {deck_name}", stats.creation_details, "created"
            )
        )

    # Updated
    if stats.updated > 0 and stats.update_details:
        html_parts.append(
            _generate_changes_list_html(
                f"✏️ Updated in {deck_name}", stats.update_details, "updated"
            )
        )

    # Deleted
    if stats.deleted > 0 and stats.deletion_details:
        html_parts.append(
            _generate_changes_list_html(
                f"🗑️ Deleted from {deck_name}", stats.deletion_details, "deleted"
            )
        )

    return "".join(html_parts)


def generate_detailed_html_view(
    total_stats, sync_errors=None, deck_results=None
) -> str:
    """
    Generates detailed view (per deck) of sync statistics in HTML.
    """
    html_parts = []

    # Aggregated Summary removed as per user request (it is in the Summary tab)

    # 2. Individual Deck Summary
    if deck_results and len(deck_results) >= 1:
        html_parts.append(
            '<div class="section-header"><h2>📊 Individual Deck Summary</h2></div>'
        )

        for i, deck_result in enumerate(deck_results, 1):
            # Add separator if not the first item
            if i > 1:
                html_parts.append(
                    '<div class="deck-separator-visual"><span class="separator-dot">•</span><span class="separator-dot">•</span><span class="separator-dot">•</span></div>'
                )

            deck_name = deck_result.deck_name
            stats = deck_result.stats
            status_class = "success-deck" if deck_result.success else "fail-deck"
            icon = "✅" if deck_result.success else "❌"
            new_label = (
                ' <span class="tag-new">NEW</span>' if deck_result.was_new_deck else ""
            )

            html_parts.append(f"""
            <div class="deck-block {status_class}">
                <div class="deck-header">
                    <span class="deck-icon">{icon}</span> 
                    <span class="deck-name">{i}. {deck_name}</span>
                    {new_label}
                </div>
            """)

            # Error message if failed
            if not deck_result.success and deck_result.error_message:
                html_parts.append(
                    f'<div class="error-banner">❌ {deck_result.error_message}</div>'
                )

            # Metrics
            html_parts.append(generate_deck_detailed_metrics(stats, deck_name))

            html_parts.append("</div>")

    return "".join(html_parts)


def generate_errors_view(total_stats, sync_errors=None, deck_results=None) -> str:
    """Generates errors only view in HTML."""
    html_parts = []

    # 1. Global/Sync Errors
    all_errors = (sync_errors or []) + total_stats.error_details
    if all_errors:
        html_parts.append(
            _generate_details_list_html(
                f"⚠️ General Errors ({len(all_errors)})", all_errors
            )
        )

    # 2. Deck Errors
    if deck_results:
        for result in deck_results:
            if (
                not result.success
                or result.stats.errors > 0
                or result.stats.error_details
            ):
                deck_errors = []
                if not result.success and result.error_message:
                    deck_errors.append(f"Critical: {result.error_message}")

                deck_errors.extend(result.stats.error_details)

                if deck_errors:
                    html_parts.append(
                        _generate_details_list_html(
                            f"⚠️ Errors in {result.deck_name}", deck_errors
                        )
                    )

            # Deck Warnings
            if result.stats.warnings:
                html_parts.append(
                    _generate_details_list_html(
                        f"⚠️ Warnings in {result.deck_name}", result.stats.warnings
                    )
                )

    if not html_parts:
        html_parts.append(
            '<div class="no-changes-info"><h3>✅ No errors found!</h3></div>'
        )

    return "".join(html_parts)


import streamlit as st

from src.config import settings
from src.graph.content_workflow import run_content_workflow


st.set_page_config(
    page_title="NAZAR | Growth Brain",
    page_icon="🔎",
    layout="wide",
)


# --------------------------------------------------
# HELPERS
# --------------------------------------------------

def is_configured(value: str) -> bool:
    if not value:
        return False

    return value.strip().lower() not in {
        "",
        "your_openai_api_key_here",
        "your_openrouter_api_key_here",
        "your_tavily_api_key_here",
    }


def to_display(value):
    """Convert Pydantic models and nested data to JSON-friendly values."""
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")

    if isinstance(value, dict):
        return {
            key: to_display(item)
            for key, item in value.items()
        }

    if isinstance(value, (list, tuple)):
        return [to_display(item) for item in value]

    return value


def as_dict(value):
    """Safely convert model or dictionary into a dictionary."""
    value = to_display(value)
    return value if isinstance(value, dict) else {}


def format_label(key):
    """Convert snake_case into readable labels."""
    return str(key).replace("_", " ").strip().title()


def render_readable(data):
    """Render nested data in a readable format instead of raw JSON."""
    data = to_display(data)

    if data is None:
        st.caption("No data available.")
        return

    if isinstance(data, dict):
        if not data:
            st.caption("No data available.")
            return

        for key, value in data.items():
            if value is None or value == "":
                continue

            label = format_label(key)

            if isinstance(value, dict):
                st.markdown(f"**{label}**")
                render_readable(value)

            elif isinstance(value, list):
                st.markdown(f"**{label}**")
                render_readable(value)

            else:
                st.markdown(f"**{label}:** {value}")

    elif isinstance(data, list):
        if not data:
            st.caption("No items available.")
            return

        for index, item in enumerate(data, start=1):
            if isinstance(item, (dict, list)):
                with st.container(border=True):
                    st.caption(f"Item {index}")
                    render_readable(item)
            else:
                st.markdown(f"- {item}")

    else:
        st.write(data)


def render_status(status):
    """Display verification status with an appropriate indicator."""
    status = str(status or "unknown").lower()

    if status == "supported":
        st.success("Supported")
    elif status == "needs_verification":
        st.warning("Needs Verification")
    elif status == "conflicting":
        st.error("Conflicting Evidence")
    elif status == "unsupported":
        st.error("Unsupported")
    else:
        st.info(status.replace("_", " ").title())


# --------------------------------------------------
# HEADER
# --------------------------------------------------

st.title("🔎 NAZAR Growth Brain")
st.caption(
    "Facts. Context. Perspective. | Multi-Agent Instagram Content System"
)

st.divider()


# --------------------------------------------------
# SIDEBAR
# --------------------------------------------------

with st.sidebar:
    st.header("⚙️ Configuration")

    st.text_input(
        "Instagram Account ID",
        value="nazar.for.world",
        key="account_id",
    )

    st.divider()

    st.subheader("API Status")

    openrouter_ready = is_configured(settings.openrouter_api_key)
    tavily_ready = is_configured(settings.tavily_api_key)

    if openrouter_ready:
        st.success("OpenRouter Connected")
    else:
        st.error("OpenRouter Not Configured")

    if tavily_ready:
        st.success("Tavily Connected")
    else:
        st.error("Tavily Not Configured")

    st.divider()

    st.caption(f"Environment: {settings.app_env}")
    st.caption(f"Model: {settings.openrouter_model}")

    st.divider()

    st.caption(
        "Scripts are saved only when all approval checks pass."
    )


# --------------------------------------------------
# CONTENT GENERATION
# --------------------------------------------------

st.subheader("Content Generation")

st.write(
    "Generate a researched content strategy, verify facts, "
    "create a Hinglish Reel script, and evaluate it before approval."
)

ready = openrouter_ready and tavily_ready

if not ready:
    st.warning(
        "Configure the required API keys in your local .env file "
        "before running the workflow."
    )

run_clicked = st.button(
    "🚀 Generate Content Strategy & Script",
    type="primary",
    disabled=not ready,
    use_container_width=True,
)

if run_clicked:
    account_id = st.session_state.account_id.strip()

    if not account_id:
        st.error("Please enter an Instagram account ID.")

    else:
        try:
            with st.spinner(
                "Agents are researching, verifying, writing and reviewing..."
            ):
                result = run_content_workflow(account_id)

            st.session_state["workflow_result"] = result
            st.success("Workflow completed.")

        except Exception as exc:
            st.error(
                "The workflow encountered an error. "
                "Check your terminal for diagnostic details."
            )
            print(f"Workflow error: {exc}")


# --------------------------------------------------
# WORKFLOW RESULTS
# --------------------------------------------------

result = st.session_state.get("workflow_result")

if result:
    result = to_display(result)

    st.divider()
    st.header("📊 Workflow Results")

    score = result.get("overall_score", 0) or 0
    revision_rounds = result.get("revision_rounds", 0)
    passed = result.get("passed", False)
    saved_id = result.get("saved_script_id")

    try:
        score = float(score)
    except (TypeError, ValueError):
        score = 0.0

    # SUMMARY METRICS
    col1, col2, col3 = st.columns(3)

    col1.metric(
        "Critic Score",
        f"{score:.1f}/10",
    )

    col2.metric(
        "Revision Rounds",
        revision_rounds,
    )

    col3.metric(
        "Approval",
        "Approved" if passed else "Not Approved",
    )

    # APPROVAL STATUS
    if passed:
        st.success(
            f"Script approved and saved. Script ID: {saved_id}"
        )
    else:
        st.warning(
            "The script did not pass all approval checks. "
            "It has not been saved as an approved script."
        )

    # EXTRACT RESULTS
    strategy_data = as_dict(result.get("strategy"))
    research_data = to_display(result.get("research"))
    verification_data = as_dict(result.get("verification"))
    script_data = as_dict(result.get("script"))
    critique_data = as_dict(result.get("critique"))
    numeric_data = as_dict(result.get("numeric_validation"))
    revision_history = result.get("revision_history", [])

    # --------------------------------------------------
    # CONTENT STRATEGY
    # --------------------------------------------------

    with st.expander("🎯 Content Strategy", expanded=True):
        topic = strategy_data.get("topic", "Untitled Topic")

        st.subheader(topic)

        col1, col2, col3 = st.columns(3)

        col1.markdown("**Content Bucket**")
        col1.write(strategy_data.get("content_bucket", "—"))

        col2.markdown("**Hook Style**")
        col2.write(strategy_data.get("hook_style", "—"))

        col3.markdown("**Format**")
        col3.write(strategy_data.get("format", "—"))

        st.markdown("**Tone**")
        st.write(strategy_data.get("tone", "—"))

        st.markdown("**Why this topic?**")
        st.write(
            strategy_data.get(
                "rationale",
                "No rationale provided.",
            )
        )

        confidence = strategy_data.get("confidence")

        if confidence is not None:
            try:
                st.metric(
                    "Strategy Confidence",
                    f"{float(confidence):.0%}",
                )
            except (TypeError, ValueError):
                st.write(f"Confidence: {confidence}")

        st.divider()

        col1, col2, col3 = st.columns(3)

        with col1:
            st.markdown("**Topics to Avoid**")
            avoid_topics = strategy_data.get("avoid_topics", [])
            if avoid_topics:
                for item in avoid_topics:
                    st.markdown(f"- {item}")
            else:
                st.caption("None")

        with col2:
            st.markdown("**Formats to Avoid**")
            avoid_formats = strategy_data.get("avoid_formats", [])
            if avoid_formats:
                for item in avoid_formats:
                    st.markdown(f"- {item}")
            else:
                st.caption("None")

        with col3:
            st.markdown("**Hook Styles to Avoid**")
            avoid_hooks = strategy_data.get("avoid_hook_styles", [])
            if avoid_hooks:
                for item in avoid_hooks:
                    st.markdown(f"- {item}")
            else:
                st.caption("None")

    # --------------------------------------------------
    # RESEARCH
    # --------------------------------------------------

    with st.expander("📚 Research"):
        render_readable(research_data)

    # --------------------------------------------------
    # FACT VERIFICATION
    # --------------------------------------------------

    with st.expander("🔍 Fact Verification", expanded=True):
        overall_status = verification_data.get(
            "overall_status",
            "unknown",
        )

        st.markdown("**Overall Verification Status**")
        render_status(overall_status)

        claims = verification_data.get(
            "claim_verifications",
            [],
        )

        if not claims:
            st.caption("No claim verification details available.")

        for claim in claims:
            claim_data = as_dict(claim)

            claim_id = claim_data.get("claim_id", "Claim")
            claim_text = claim_data.get("claim", "No claim text.")
            status = claim_data.get("status", "unknown")

            with st.container(border=True):
                st.markdown(f"**{claim_id}**")
                st.write(claim_text)

                render_status(status)

                confidence = claim_data.get("confidence")
                if confidence is not None:
                    try:
                        st.caption(
                            f"Confidence: {float(confidence):.0%}"
                        )
                    except (TypeError, ValueError):
                        pass

                explanation = claim_data.get("explanation")
                if explanation:
                    st.markdown("**Explanation**")
                    st.write(explanation)

                evidence_list = claim_data.get("evidence", [])

                if evidence_list:
                    st.markdown("**Evidence**")

                    for evidence in evidence_list:
                        evidence_data = as_dict(evidence)

                        source_title = evidence_data.get(
                            "source_title",
                            "Source",
                        )
                        source_url = evidence_data.get("source_url")
                        excerpt = evidence_data.get(
                            "evidence_excerpt",
                            "",
                        )

                        st.markdown(f"**{source_title}**")

                        if excerpt:
                            st.write(excerpt)

                        if source_url:
                            st.markdown(
                                f"[Open Source]({source_url})"
                            )

                        supports = evidence_data.get("supports_claim")
                        if supports is not None:
                            st.caption(
                                "Supports claim: "
                                + ("Yes" if supports else "No")
                            )

    # --------------------------------------------------
    # GENERATED SCRIPT
    # --------------------------------------------------

    with st.expander("✍️ Generated Script", expanded=True):
        st.subheader(
            script_data.get(
                "topic",
                "Generated Reel Script",
            )
        )

        segments = script_data.get("segments", [])

        if segments:
            for segment in segments:
                segment_data = as_dict(segment)

                segment_number = segment_data.get(
                    "segment_number",
                    "?",
                )
                voiceover = segment_data.get(
                    "voiceover",
                    "",
                )
                visual_direction = segment_data.get(
                    "visual_direction",
                    "",
                )

                with st.container(border=True):
                    st.markdown(f"**Segment {segment_number}**")

                    if voiceover:
                        st.write(voiceover)
                    else:
                        st.caption("No voiceover provided.")

                    if visual_direction:
                        st.markdown("**Visual Direction**")
                        st.caption(visual_direction)

        else:
            st.warning("No script segments were returned.")

        cta = script_data.get("call_to_action")

        if cta:
            st.divider()
            st.markdown("**Call to Action**")
            st.write(cta)

    # --------------------------------------------------
    # CRITIC FEEDBACK
    # --------------------------------------------------

    with st.expander("🧠 Critic Feedback", expanded=True):
        scores = critique_data.get("scores", {})

        if scores:
            score_items = list(scores.items())
            columns = st.columns(len(score_items))

            for column, (key, value) in zip(columns, score_items):
                try:
                    display_score = f"{float(value):.1f}/10"
                except (TypeError, ValueError):
                    display_score = str(value)

                column.metric(
                    format_label(key),
                    display_score,
                )
        else:
            st.caption("No individual critic scores available.")

        st.divider()

        strengths = critique_data.get("strengths", [])
        weaknesses = critique_data.get("weaknesses", [])
        instructions = critique_data.get(
            "revision_instructions",
            [],
        )

        left, right = st.columns(2)

        with left:
            st.markdown("**✅ Strengths**")

            if strengths:
                for item in strengths:
                    st.markdown(f"- {item}")
            else:
                st.caption("No strengths provided.")

        with right:
            st.markdown("**⚠️ Areas to Improve**")

            if weaknesses:
                for item in weaknesses:
                    st.markdown(f"- {item}")
            else:
                st.caption("No weaknesses provided.")

        if instructions:
            st.divider()
            st.markdown("**🔄 Revision Instructions**")

            for item in instructions:
                st.markdown(f"- {item}")

    # --------------------------------------------------
    # NUMERIC VALIDATION
    # --------------------------------------------------

    with st.expander("🔢 Numeric Validation"):
        numeric_passed = numeric_data.get("passed", False)

        if numeric_passed:
            st.success("Numeric validation passed.")
        else:
            st.error("Numeric validation failed.")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**Numbers in Script**")
            st.write(
                numeric_data.get("script_numbers", [])
            )

        with col2:
            st.markdown("**Supported Research Numbers**")
            st.write(
                numeric_data.get(
                    "supported_research_numbers",
                    [],
                )
            )

        unmatched = numeric_data.get(
            "unmatched_numbers",
            [],
        )

        if unmatched:
            st.warning(f"Unmatched numbers: {unmatched}")

        issues = numeric_data.get("issues", [])

        if issues:
            st.markdown("**Issues**")
            for issue in issues:
                st.markdown(f"- {issue}")

    # --------------------------------------------------
    # REVISION HISTORY
    # --------------------------------------------------

    with st.expander("🔄 Revision History"):
        if revision_history:
            for revision in revision_history:
                revision_data = as_dict(revision)

                round_number = revision_data.get("round", "?")
                round_score = revision_data.get("score", "—")

                with st.expander(
                    f"Round {round_number} — Score: {round_score}/10"
                ):
                    scores = revision_data.get("scores", {})

                    if scores:
                        score_items = list(scores.items())
                        columns = st.columns(len(score_items))

                        for column, (key, value) in zip(
                            columns,
                            score_items,
                        ):
                            column.metric(
                                format_label(key),
                                f"{value}/10",
                            )

                    st.markdown("**Strengths**")
                    for item in revision_data.get("strengths", []):
                        st.markdown(f"- {item}")

                    st.markdown("**Weaknesses**")
                    for item in revision_data.get("weaknesses", []):
                        st.markdown(f"- {item}")

                    st.markdown("**Revision Instructions**")
                    for item in revision_data.get(
                        "revision_instructions",
                        [],
                    ):
                        st.markdown(f"- {item}")

        else:
            st.caption("No revision history available.")

    # --------------------------------------------------
    # DEVELOPER DEBUG
    # --------------------------------------------------

    with st.expander("🛠️ Developer Debug Details"):
        st.caption(
            "Raw workflow output for debugging. "
            "This section is intended for development."
        )
        st.json(result)

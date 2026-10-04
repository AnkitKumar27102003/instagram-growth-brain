# NAZAR --- Multi-Agent Instagram Growth Brain

A prototype multi-agent system that turns account context, content
history, research, and performance feedback into a strategic Hinglish
Instagram Reel draft.

## What it does

-   Reviews sample account, content, event, trend, and competitor
    context.
-   Uses performance memory to identify descriptive patterns in prior
    hits and underperformers.
-   Selects a topic, content bucket, hook style, format, and tone with a
    rationale and confidence.
-   Retrieves research evidence and checks claims against available
    sources.
-   Writes a structured Hinglish Reel script with segments targeted at
    18--23 words.
-   Critiques hook strength, emotional arc, pacing, originality, and
    strategic alignment.
-   Revises scripts for up to three rounds when the critic score is
    below 8.5/10.
-   Stores approved scripts and feedback, distinguishing simulated from
    real performance data.
-   Uses fatigue and breakout signals as guidance, not as proof of
    causation.

## Project status

The repository's automated test suite has been reported as passing:
`115 passed`. The Streamlit interface has also been run locally. An
example end-to-end workflow completed, but its best critic score was
7.0/10, below the 8.5 approval threshold; that run correctly did not
approve or save the script.

This is a prototype. Sample feedback is synthetic, and it should not be
presented as actual Instagram performance. Research verification and
script verification are separate checks: a script may have supported
assessed claims while the overall research set still contains claims
needing verification.

## Run locally

Use a terminal from the project root.

``` powershell
# Activate the virtual environment if it is not already active
.\.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Run tests
python -m pytest -q

# Launch the Streamlit app
python -m streamlit run app/app.py
```

Open the local address printed by Streamlit, usually
`http://localhost:8501`.

For package-style scripts, use module execution from the project root,
for example:

``` powershell
python -m scripts.demo_memory
python -m scripts.demo_memory --generate-strategy
```

Running a script such as `python scripts/demo_memory.py` may fail to
resolve the `src` package depending on the Python path.

## High-level workflow

1.  **Intelligence:** collect account, content, event/trend, and
    competitor context.
2.  **Performance memory:** retrieve prior content and performance
    patterns.
3.  **Strategy:** select a topic and creative direction, accounting for
    fatigue and breakout signals.
4.  **Research:** gather facts, sources, and evidence.
5.  **Verification:** assess research claims and their support.
6.  **Writing:** produce the structured Hinglish Reel script.
7.  **Critique and revision:** score the draft and revise within the
    configured limit.
8.  **Final checks and storage:** validate the script; save only when
    approval conditions are met.
9.  **Learning:** use recorded feedback to inform future strategy.

See `docs/architecture.md` for the Mermaid diagram. Add the separate
architecture infographic to the repository if you want a visual image
alongside the editable diagram.

## Data and evaluation notes

-   Demo metrics are simulated and intended only to demonstrate memory
    and learning workflows.
-   Fatigue and breakout calculations are descriptive signals; they do
    not establish that a topic or format caused performance changes.
-   Research and verification depend on retrieved source quality and
    model output. Review citations and uncertain claims before
    publishing.
-   A critic score below 8.5/10 is not approved, even if other
    validation checks pass.
-   Do not claim real Instagram analytics integration unless a live data
    connection has actually been implemented and tested.

## Suggested demo sequence

1.  Run the automated tests.
2.  Launch the Streamlit app and generate a strategy.
3.  Show the research evidence and verification statuses.
4.  Show the writer/critic revision history, including a draft that
    remains below threshold.
5.  Run the memory demo to show simulated feedback, fatigue/breakout
    signals, and how those signals inform a later strategy.

## Repository structure

``` text
app/          Streamlit interface
src/          Agents, models, workflow, analytics, and memory
tests/        Automated tests
scripts/      Demo and utility scripts
data/         Sample data
docs/         Architecture and project documentation
examples/     Sample strategy, script status, critique, and feedback outputs
loom/         Recording guide
```

## Limitations and next steps

-   Connect and validate real Instagram analytics only if authorized
    access becomes available.
-   Evaluate semantic similarity thresholds against a larger, real NAZAR
    topic history.
-   Improve source quality and claim-level verification, especially for
    time-sensitive facts.
-   Capture and review actual content performance before drawing
    conclusions about what works.
-   Record the Loom walkthrough and verify all example artifacts against
    the final repository state.

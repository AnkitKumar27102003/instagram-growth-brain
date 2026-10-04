# Guardrail Test Evidence

**Project:** NAZAR — Multi-Agent Instagram Growth Brain  
**Environment:** Windows 11 / PowerShell, Python 3.13.14, pytest 9.1.1  
**Repository:** `instagram-growth-brain`  
**Evidence basis:** Test output supplied from the project's local environment on 4 October 2026.

---

## 1. Summary

The project’s local test suite completed successfully.

| Test run | Result |
|---|---:|
| `tests/test_script_model.py` | **4 passed** |
| `tests/test_performance.py` + `tests/test_performance_memory.py` | **15 passed** |
| Full suite: `python -m pytest -q` | **115 passed** |
| Full-suite duration | 45.76 seconds |

The full-suite run reported no failures:

```text
...................................................................................
115 passed in 45.76s
```

The focused runs below provide visible evidence for key script-validation, metric-validation, performance-memory, fatigue, and breakout guardrails.

---

## 2. Guardrail: Reel segment word-count validation

**Purpose:** Keep generated voiceover segments within the project's target of 18–23 words per segment.

**Test file:** `tests/test_script_model.py`

| Test | Expected behavior | Result |
|---|---|---|
| `test_accepts_18_words` | Accept a segment containing 18 words | PASSED |
| `test_accepts_23_words` | Accept a segment containing 23 words | PASSED |
| `test_rejects_invalid_word_count[17]` | Reject a segment containing 17 words | PASSED |
| `test_rejects_invalid_word_count[24]` | Reject a segment containing 24 words | PASSED |

**Command run:**

```powershell
python -m pytest tests/test_script_model.py -v
```

**Observed result:**

```text
collected 4 items

tests/test_script_model.py::test_accepts_18_words PASSED
tests/test_script_model.py::test_accepts_23_words PASSED
tests/test_script_model.py::test_rejects_invalid_word_count[17] PASSED
tests/test_script_model.py::test_rejects_invalid_word_count[24] PASSED

4 passed in 0.05s
```

**What this demonstrates:** The script model accepts the lower and upper boundaries and rejects examples immediately outside the permitted range.

---

## 3. Guardrail: Performance metric validation

**Purpose:** Prevent invalid performance metrics from being accepted into the analytics and memory workflow.

**Test file:** `tests/test_performance.py`

| Test | Guardrail exercised | Result |
|---|---|---|
| `test_calculate_post_metrics` | Calculate post metrics for valid input | PASSED |
| `test_zero_reach_rejected` | Reject zero reach | PASSED |
| `test_negative_values_rejected` | Reject negative metric values | PASSED |

**Command run:**

```powershell
python -m pytest tests/test_performance.py tests/test_performance_memory.py -v
```

**Observed result:** All 3 performance-metric tests passed as part of the 15-test focused run.

**What this demonstrates:** Valid metric calculations work for the tested case, while zero reach and negative values are rejected by the tested validation paths.

---

## 4. Guardrail: Approved-script and feedback memory

**Purpose:** Verify that approved scripts and their performance feedback can be stored and retrieved, and that feedback is identified as simulated when recorded as such.

**Test file:** `tests/test_performance_memory.py`

| Test | Guardrail exercised | Result |
|---|---|---|
| `test_save_and_retrieve_approved_script` | Save and retrieve an approved script | PASSED |
| `test_feedback_is_stored_as_simulated` | Store feedback with simulated status | PASSED |
| `test_invalid_reach_is_rejected` | Reject feedback with invalid reach | PASSED |

**What this demonstrates:** The tested memory operations support saving/retrieving an approved script, preserving simulated-feedback status, and rejecting invalid reach.

---

## 5. Guardrail: Feedback fatigue detection

**Purpose:** Avoid treating weak or insufficient evidence as a reliable fatigue signal, and keep real and simulated performance data separate.

**Test file:** `tests/test_performance_memory.py`

| Test | Guardrail exercised | Result |
|---|---|---|
| `test_feedback_fatigue_detects_engagement_decline` | Detect an engagement decline in the tested feedback data | PASSED |
| `test_feedback_fatigue_keeps_real_and_simulated_separate` | Keep real and simulated feedback separate | PASSED |
| `test_feedback_fatigue_ignores_single_record` | Do not infer fatigue from a single record | PASSED |

**What this demonstrates:** The tested fatigue logic can detect a decline in the supplied scenario, separates real from simulated feedback, and ignores a single feedback record.

**Interpretation note:** Fatigue is a descriptive signal from available feedback; these tests do not establish that topic fatigue caused a decline in actual audience performance.

---

## 6. Guardrail: Breakout detection

**Purpose:** Identify unusually strong performance only when sufficient comparable feedback exists, while keeping simulated and real feedback separate.

**Test file:** `tests/test_performance_memory.py`

| Test | Guardrail exercised | Result |
|---|---|---|
| `test_breakout_detects_high_performing_script` | Detect a high-performing script in the tested scenario | PASSED |
| `test_breakout_keeps_real_and_simulated_feedback_separate` | Keep real and simulated feedback separate | PASSED |
| `test_breakout_requires_enough_distinct_scripts` | Require enough distinct scripts | PASSED |
| `test_breakout_rejects_invalid_parameters[kwargs0-account_id must not be empty]` | Reject empty account ID | PASSED |
| `test_breakout_rejects_invalid_parameters[kwargs1-min_feedback_records must be at least 2]` | Reject too-small feedback-record threshold | PASSED |
| `test_breakout_rejects_invalid_parameters[kwargs2-breakout_multiplier must be greater than 1]` | Reject invalid breakout multiplier | PASSED |

**What this demonstrates:** The tested breakout logic detects the supplied high-performance case, requires a minimum evidence threshold, separates real and simulated feedback, and validates key parameters.

**Interpretation note:** A detected breakout is a descriptive comparison against the available baseline. It is not proof of statistical significance or a guarantee that the same content pattern will perform similarly in the future.

---

## 7. Full test-suite evidence

**Command run:**

```powershell
python -m pytest -q
```

**Observed result:**

```text
...................................................................................
115 passed in 45.76s
```

**Result:** All 115 tests in the full suite passed in the supplied run.

This full-suite result complements the focused test runs. It should be described as a successful local test run, not as proof that every real-world behavior, external integration, or production deployment scenario has been tested.

---

## 8. Running the tests again

Run these commands from the repository root with the virtual environment activated:

```powershell
python -m pytest tests/test_script_model.py -v
python -m pytest tests/test_performance.py tests/test_performance_memory.py -v
python -m pytest -q
```

To produce a fresh result for a reviewer or recording, rerun the commands in the current checkout and show the terminal output.

---

## 9. Scope and limitations

The supplied test output directly supports the passing results and named test cases documented above. It does **not**, by itself, prove:

- that the tests cover every possible boundary or malformed input;
- that fatigue or breakout signals are causal or statistically significant;
- that simulated metrics represent actual Instagram performance;
- that generated research is always factually correct;
- that live Instagram analytics, external APIs, or production deployment have been validated.

For the submission, present this document as **automated test evidence for selected guardrails**, alongside the actual test files and the full-suite result. Do not describe the focused test names as complete coverage of the entire system.

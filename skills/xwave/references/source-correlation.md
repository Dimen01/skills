# Source and RTL Correlation Playbook

Use this when the user provides RTL, Chisel, SystemVerilog, emitted RTL, source roots, hierarchy ownership, or asks for root cause rather than waveform symptoms only.

## Evidence Order

1. Establish the waveform symptom first with xwave queries.
2. Use exact hierarchy or emitted RTL ownership when available to identify the module and local signal.
3. Use source code to explain why the observed signal did or did not transition.
4. Inspect generated SystemVerilog only when source-first analysis is blocked or the user specifically asks for it.

If no source or RTL root is available, label the result `waveform-only analysis`.

## Workflow

1. Collect optional context:
   - source root
   - emitted RTL root
   - top module
   - focus scope
   - human debug hint
2. From waveform evidence, choose a small set of anchor signals and timestamps.
3. Search source/RTL with anchors such as module name, local signal name, bus prefix, address decode signal, state name, valid/ready driver, or `pready` driver.
4. Prefer the highest-confidence match:
   - exact hierarchy or emitted RTL owner: high-confidence ownership
   - module/local signal name match: medium-confidence candidate
   - broad subsystem or rough name match: low-confidence hint
5. Explain source logic only when it directly connects to the waveform symptom.
6. If source and waveform disagree, report the disagreement as uncertainty instead of forcing a root cause.

## Root-Cause Categories

Use a category in the final report:

- backpressure stall
- missing response
- state machine deadlock
- data hazard
- flush/reset handling miss
- arbitration or starvation
- address decode/select miss
- unknown or insufficient evidence

## Rules

- Do not treat rough name matches as exact ownership.
- Do not claim root cause from waveform symptoms alone.
- Cite only source files and signals that materially support the conclusion.
- Avoid large generated-RTL excerpts and raw per-cycle dumps.
- Recommend a fix only when confidence is high; otherwise give the next probes.

---
name: xwave
description: Use when debugging xwave-supported local hardware waveforms, AXI/APB hangs or timeouts, RTL signal behavior, waveform traces, signal values, or simulation failures that require evidence from xwave.
---

# xwave

Use xwave to inspect local waveform data through structured MCP tools. Prefer MCP tools over shell commands when the xwave MCP server is available. Use CLI commands with `--json` only as a fallback.

Core approach:

- Use waveform queries as the primary evidence path.
- Keep queries narrow: signal search, point values, protocol summaries, then focused trace windows.
- Use RTL or source files, when provided, to explain ownership and intent after the waveform symptom is established.
- Label analysis as waveform-only when source or RTL evidence is unavailable.

## Required Inputs

- xwave-supported waveform path, including JSON fixtures and real `.fsdb` waveforms
- Suspected time range, if known
- Suspected signal, bus prefix, or failure symptom, if known
- Optional RTL/source root, emitted RTL root, top module, focus scope, or human debug hint

Notes:

- Real `.fsdb` support depends on `fsdb2vcd` being available in the runtime environment.
- xwave may cache converted VCD artifacts under `~/.cache/xwave/fsdb_cache/`.

If the path is missing, ask for it. If the time range is missing, start with signal search and protocol summaries; ask for a range only when the waveform is too large or the request is ambiguous.

## Basic Workflow

1. Load the waveform with `xwave.load_fsdb`.
2. Find relevant signals with `xwave.find_signals`.
3. Query exact values with `xwave.query_value`.
4. Use protocol summaries for AXI/APB symptoms before dumping raw traces.
5. Trace the smallest useful window with `xwave.trace_signals`, centered on the first stall, missing response, timeout, or suspicious transition.
6. If RTL/source roots are provided, correlate waveform paths back to source ownership before proposing root cause.
7. Report findings with timestamped evidence, symptom category, root-cause category when supported, and confidence.

## Playbook Selection

- AXI hang, timeout, valid/ready, write response, read data: read `references/axi-debug.md`.
- APB timeout, psel/penable/pready, peripheral access: read `references/apb-debug.md`.
- RTL, Chisel, SystemVerilog, ownership, hierarchy, source root, emitted RTL, root cause: read `references/source-correlation.md`.
- Final user-facing report: follow `references/report-template.md`.

## Reporting Rules

- Cite signal names and timestamps.
- Separate observed evidence from likely cause.
- Do not claim root cause if the current signals only show a symptom.
- State whether the analysis is waveform-only, waveform+RTL, or waveform+source.
- Use confidence labels: high only when waveform evidence and source/RTL logic agree; otherwise medium or low.
- In waveform-only reports, classify the symptom and use `unknown/insufficient evidence` for root-cause category unless the waveform alone proves the cause.
- Include next probes when evidence is incomplete.

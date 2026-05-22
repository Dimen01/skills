# xwave Debug Report Template

Use this structure for user-facing summaries.

```text
Summary:
  Phenomenon: Short statement of the observed failure.
  Symptom Category: backpressure stall | missing response | wait-state timeout | unexpected value | reset/flush anomaly | unknown.
  Root Cause Category: state machine deadlock | data hazard | flush/reset handling miss | decode/select miss | arbitration/starvation | unknown/insufficient evidence.
  Confidence: high | medium | low.
  Evidence Mode: waveform-only | waveform+RTL | waveform+source.

Evidence:
  - <timestamp>: <signal> = <value>, meaning <interpretation>.
  - <timestamp range>: <channel> had <count> handshakes and first stalled at <time>.

Source/RTL correlation:
  - <file or module>: <logic that supports or weakens the hypothesis>.

Likely cause:
  Interpretation supported by the evidence.

Uncertainty:
  What cannot be proven from the current waveform signals.

Next probes:
  - Specific signal or log to inspect next.
```

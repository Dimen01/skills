# AXI Debug Playbook

Use this when the symptom mentions AXI hang, timeout, valid/ready stall, missing response, or missing read data.

## Signals

For a bus prefix such as `top.u_dma.m_axi`, inspect:

- Write address: `awvalid`, `awready`
- Write data: `wvalid`, `wready`
- Write response: `bvalid`, `bready`
- Read address: `arvalid`, `arready`
- Read data: `rvalid`, `rready`

## Workflow

1. Run `xwave.find_signals` for the suspected hierarchy.
2. Run `xwave.axi_summary` over the requested window.
3. If a channel has a first stall, run `xwave.trace_signals` around that timestamp for the channel valid/ready pair.
4. Use `xwave.query_value` for point checks at the first stall, response deadline, or timeout timestamp.
5. For write hangs:
   - If AW and W handshakes complete but B never handshakes, suspect slave response generation or downstream write completion.
   - If AW stalls, inspect address path backpressure.
   - If W stalls, inspect data path backpressure and burst completion.
6. For read hangs:
   - If AR handshakes but R never returns, suspect slave read response/data path.
   - If AR stalls, inspect address path backpressure.
7. If RTL/source roots are available, use the stalled channel and signal names as source-search anchors before naming a root cause.

Keep trace windows small. Do not paste long per-cycle dumps unless the user explicitly asks; summarize the first stall, completed handshakes, and missing response evidence.

## Evidence

Always report:

- First stall timestamp
- Channel involved
- Valid/ready values at the stall
- Completed handshakes before the stall
- Missing response or data channel evidence, if applicable
- Root-cause category and confidence if source or RTL evidence is available

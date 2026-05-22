# APB Debug Playbook

Use this when the symptom mentions APB timeout, peripheral access hang, `psel`, `penable`, or `pready`.

## Signals

For a bus prefix such as `top.u_periph.apb`, inspect:

- `psel`
- `penable`
- `pready`
- `pwrite`
- `paddr`
- `pwdata`
- `prdata`
- `pslverr`

## Workflow

1. Run `xwave.find_signals` for the suspected APB hierarchy.
2. Run `xwave.apb_summary` over the requested window.
3. If `psel` and `penable` are high while `pready` stays low, report an APB wait-state stall.
4. Trace `paddr`, `pwrite`, and data signals near the stall if available.
5. If `pslverr` is present, query it at the transfer completion time.
6. If source or RTL roots are available, search for the peripheral select/decode path and the logic driving `pready` before naming a root cause.

Keep the waveform evidence compact: transfer start, first wait-state timestamp, eventual completion or timeout, and address/direction when visible.

## Evidence

Always report:

- Transfer start timestamp
- First wait-state timestamp
- Whether `pready` eventually asserted
- Address and direction if available
- Error response if available
- Root-cause category and confidence if source or RTL evidence is available

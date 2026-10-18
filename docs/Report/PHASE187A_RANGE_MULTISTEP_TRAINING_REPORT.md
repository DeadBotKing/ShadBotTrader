# PHASE187A — Protected Range Multistep WaveNet Training

## Summary

A training command now exists for a new multistep range WaveNet. It has not been executed on the gold dataset in this sandbox.

```text
No overwrite of gold_range_4h or gold_range_1d.
No Option B architecture.
No paper. No live.
No invented training result.
```

## Save ids

```text
gold_range_multistep_4h
gold_range_multistep_1d
```

Output contract:

```text
horizon=5
output width=10
layout=[high_1, low_1, ..., high_5, low_5]
architecture=existing range WaveNet seq2seq
window=150
layers x blocks=4 x 2
```

## Owner action

```text
AI → Train range multistep WaveNet
```

Then, only after that run finishes:

```text
AI → Audit range multistep accuracy
4H range model = gold_range_multistep_4h
1D range model = gold_range_multistep_1d
Requested future candles = 5
```

Send `run_logs\range_multistep_accuracy\latest.json` from that second run. Do not treat the old Phase186A result as the result of this new model.

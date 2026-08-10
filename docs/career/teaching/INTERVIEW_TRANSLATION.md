# Interview translation

> **Status: current module of teaching protocol v1.**

Use `problem -> locked variables -> hypothesis -> experiment -> metric/gate ->
negative result -> limitation -> next falsifiable gate`.

Likely questions:

- Why use task-family-disjoint splits instead of random rows?
- How did you prevent evaluation leakage during safety repair?
- Why is a decision compiler part of candidate identity?
- How did you isolate BF16/FP32 effects from attached/merged execution form?
- What does an exact hash establish, and what does it not establish?
- Why is the preferred offline candidate still not portable or Runtime eligible?

Strong answers identify the one controlled variable and the strongest conclusion
the evidence allows, then name the next experiment required to widen it.

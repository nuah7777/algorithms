# Implementation Plan

1. Read `SPEC.md` and translate its required boundary cases into tests before
   implementing the hash table or shortener. Keep the tests unchanged after
   the implementation begins; add any missed cases during this test-first
   review.
2. Implement the base62 helpers and a separate-chaining `HashTable` with
   linked-list nodes, Horner hashing, collision-safe updates, lookup, and
   immutable inspection output. Do not use `dict`, `set`, or built-in
   `hash()`.
3. Implement `Shortener` on the chaining table. Validate absolute HTTP(S)
   URLs, assign sequential base62 codes, reuse a URL's existing code, and
   report invalid or missing values explicitly.
4. Run `make test` and fix implementation defects without changing tests.
5. Add a load-factor experiment that uses the same keys and capacity for each
   strategy, records measured search costs, compares them with theoretical
   estimates, and writes a table and SVG graph.
6. Add the web service and `/table` inspection view. Display table contents,
   the Horner calculation, and the slots examined for a lookup. Keep network
   exposure and hosted-port operations as explicit manual steps.
7. Implement linear probing with the same public table operations. Test
   wraparound, collisions, updates, and full-table errors, then let the
   shortener select either strategy and run the shortener tests for both.
8. Produce a concise report (no more than two PDF pages) with the experiment
   setup, results, theory comparison, and interpretation.

## Constraints

- Tests for specified boundary cases precede hash-table and shortener code.
- Source code must not use `dict`, `set`, or Python's built-in `hash()`.
- A short code comes from a sequential integer encoded as base62, never from
  a hash value.
- Do not alter tests to accommodate implementation behavior; repair the
  implementation instead.

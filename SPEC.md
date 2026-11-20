# URL Shortener Specification

## 1. Scope

The project provides base62 conversion, a URL shortener backed by a
collision-resolving hash table, command-line tests, and a small inspection
web page. Hash table keys are strings. The initial implementation uses
separate chaining; a later implementation adds linear probing with the same
public operations.

## 2. Base62

- The alphabet is `0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz`.
- `encode(number)` accepts a non-negative integer and returns its base62 form.
- Zero is encoded as `"0"`.
- Negative numbers raise `ValueError`.
- `decode(value)` accepts a non-empty string containing only alphabet
  characters and returns the represented non-negative integer.
- An empty string or a character outside the alphabet raises `ValueError`.
- For every supported integer `n`, `decode(encode(n)) == n`.

## 3. Hash table

`HashTable(capacity=10)` requires a positive integer capacity. It exposes:

- `insert(key, value)`: add a string key, replacing the value when the key is
  already present.
- `get(key)`: return the value for a present key, otherwise `None`.
- `len(table)`: number of distinct keys.
- `hash_details(key)`: return the bucket index and the Horner-calculation
  steps for inspection.
- `inspect()`: return an immutable slot-ordered snapshot; each slot contains
  an immutable sequence of `(key, value)` pairs.

Hashing starts at zero and processes each Unicode code point `c` as
`h = (31 * h + ord(c)) % capacity`. The empty string hashes to bucket zero.
The first implementation stores colliding keys in a linked list per bucket.
The linear-probing implementation uses the same hash calculation and public
operations; insertion into a full table raises `OverflowError`. Both
implementations update an existing key instead of adding a duplicate.

The source implementation must not use `dict`, `set`, or Python's built-in
`hash()`.

## 4. URL shortener

`Shortener(table_kind="chaining", capacity=10)` uses the requested table
implementation (`"chaining"` or, when available, `"linear"`).

- `shorten(url)` accepts an absolute `http` or `https` URL with a host and
  returns a base62 code.
- Re-shortening the same URL returns its original code.
- Codes are assigned from a monotonically increasing integer sequence and
  encoded with base62; a hash value is never used as a code.
- `resolve(code)` returns the original URL.
- Invalid URLs raise `ValueError`; an unknown code raises `KeyError`.
- Exhausting a bounded table raises `OverflowError` rather than silently
  replacing an entry.

## 5. Inspection page and experiments

`/table` shows each slot and its stored chain or probe entry. For a queried
key, it shows the Horner hash steps and the slots examined to retrieve it.
The experiment compares measured average search costs at load factors 0.1
through 0.9 with theoretical estimates, using identical keys and capacities
for both collision strategies.

## 6. Required boundary cases

1. `encode(0)` is `"0"` and zero round-trips through decode.
2. Base62 conversion handles values larger than one digit and rejects
   negative input, empty encoded input, and invalid alphabet characters.
3. Hash-table capacity zero is rejected; capacity one works.
4. Empty string keys hash to zero and can be retrieved.
5. Two different keys that hash to the same bucket remain independently
   retrievable; inserting an existing key updates it without changing length.
6. Missing keys return `None`; inspecting an empty table returns empty slots.
7. A capacity-one linear-probing table accepts one entry, wraps from its last
   slot to slot zero when probing, and raises `OverflowError` when full.
8. URL validation rejects relative URLs, unsupported schemes, and missing
   hosts. Duplicate URLs reuse their code, and unknown codes raise `KeyError`.

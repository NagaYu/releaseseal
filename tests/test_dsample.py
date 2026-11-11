"""dsample/1 sampling rule: determinism, caps, text-field selection (SPEC.md §E1.2; D-28)."""
from releaseseal import DSAMPLE_RULE, DSAMPLE_SEED
from releaseseal.canonical import canonical_bytes
from releaseseal.snapshot.dsample import build_sample, row_text


def test_deterministic_bytes():
    rows = {"train": [{"text": f"row number {i} about science"} for i in range(5000)],
            "test": [{"text": f"eval line {i}"} for i in range(50)]}
    a = build_sample(rows, seed=DSAMPLE_SEED)
    b = build_sample(rows, seed=DSAMPLE_SEED)
    assert canonical_bytes(a) == canonical_bytes(b)
    assert a["rule"] == DSAMPLE_RULE and a["seed"] == DSAMPLE_SEED


def test_row_cap_enforced_and_sorted():
    rows = {"train": [{"text": f"line {i}"} for i in range(5000)]}
    s = build_sample(rows, seed=DSAMPLE_SEED, cap_rows=100)
    ps = s["per_split"][0]
    assert ps["rows_total"] == 5000 and ps["rows_sampled"] == 100
    idxs = [r["index"] for r in s["rows"]]
    assert idxs == sorted(idxs)                 # emitted ascending by index
    assert all(0 <= i < 5000 for i in idxs)


def test_byte_cap_enforced():
    rows = {"train": [{"text": "x" * 100} for _ in range(100)]}
    s = build_sample(rows, seed=DSAMPLE_SEED, cap_bytes=250)  # ~2 rows of 100 bytes
    assert s["per_split"][0]["bytes_read"] <= 250
    assert s["per_split"][0]["rows_sampled"] <= 3


def test_text_field_preference_order():
    assert row_text({"content": "c", "text": "t"}) == "t"       # text wins
    assert row_text({"content": "c", "prompt": "p"}) == "c"     # content before prompt
    assert row_text({"instruction": "i"}) == "i"
    # no designated field -> canonical JSON of the row
    assert row_text({"foo": 1, "bar": 2}) == '{"bar":2,"foo":1}'


def test_different_seed_differs():
    rows = {"train": [{"text": f"line {i}"} for i in range(500)]}
    a = build_sample(rows, seed=1, cap_rows=10)
    b = build_sample(rows, seed=2, cap_rows=10)
    assert [r["index"] for r in a["rows"]] != [r["index"] for r in b["rows"]]

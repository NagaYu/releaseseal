"""Thin CLI over the core (SPEC.md §8). stdlib argparse only."""
from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Optional

from . import APP_CODENAME, __version__


def _write_json(obj, path: Optional[str]):
    text = json.dumps(obj, indent=2, ensure_ascii=False)
    if path:
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text + "\n")
    else:
        sys.stdout.write(text + "\n")


def _load_json(path: str):
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def cmd_snapshot(args) -> int:
    from .snapshot.local_adapter import snapshot_from_dir
    if args.local:
        snap = snapshot_from_dir(args.local)
    elif args.hf_fixture:
        from .snapshot.hf_adapter import snapshot_from_fixture
        snap = snapshot_from_fixture(args.hf_fixture, args.hf or "unknown/repo", args.revision)
    elif args.hf:
        from .snapshot.hf_live import HttpFetcher
        from .snapshot.hf_adapter import build_snapshot
        snap = build_snapshot(args.hf, args.revision, HttpFetcher())
    else:
        print("error: one of --local / --hf / --hf-fixture is required", file=sys.stderr)
        return 2
    _write_json(snap, args.output)
    return 0


def cmd_verify(args) -> int:
    from .verify import verify
    snap = _load_json(args.snapshot)
    doc = verify(snap, as_of_now=args.as_of)
    _write_json(doc, args.output)
    counted = [f for f in doc["findings"] if not f.get("heuristic") and f["check"] != "V8"]
    if args.ci and counted:
        return 1
    return 0


def cmd_pack(args) -> int:
    from .verify import verify
    from .evidence import build_pack, render_report
    snap = _load_json(args.snapshot)
    doc = verify(snap, as_of_now=args.as_of)
    pack = build_pack(snap, doc)
    _write_json(pack, args.output)
    if args.report:
        with open(args.report, "w", encoding="utf-8") as fh:
            fh.write(render_report(pack))
    return 0


def cmd_verify_pack(args) -> int:
    from .evidence import verify_pack
    pack = _load_json(args.pack)
    snap = _load_json(args.snapshot) if args.snapshot else None
    result = verify_pack(pack, snap)
    _write_json(result, None)
    return 0 if result["ok"] else 1


def cmd_bench_generate(args) -> int:
    from .bench import generate, generate_ext
    os.makedirs(args.output, exist_ok=True)
    manifest = generate(seed=args.seed, per_class=args.per_class, n_clean=args.clean)
    with open(os.path.join(args.output, "manifest.json"), "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    print(f"generated {len(manifest['cases'])} cases (seed={manifest['seed']}, "
          f"cases_sha256={manifest['cases_sha256'][:16]}...) -> {args.output}/manifest.json")
    if args.ext:
        ext = generate_ext(seed=args.seed)
        with open(os.path.join(args.output, "manifest_ext.json"), "w", encoding="utf-8") as fh:
            json.dump(ext, fh, indent=2, ensure_ascii=False)
            fh.write("\n")
        print(f"generated {len(ext['cases'])} dev_ext lineage cases "
              f"(cases_sha256={ext['cases_sha256'][:16]}...) -> {args.output}/manifest_ext.json")
    return 0


def cmd_bench_score(args) -> int:
    from .bench import gate1, score
    manifest = _load_json(args.manifest)
    scored = score(manifest)
    gate = gate1(scored)
    print(f"{APP_CODENAME} bench score")
    print(f"  cases: {len(manifest.get('cases', []))}  seed: {manifest.get('seed')}")
    print("  per-class recall:")
    for c, r in scored["recall"].items():
        rr = "n/a" if r is None else f"{r:.3f}"
        print(f"    {c}: {rr}  ({scored['per_class_hit'][c]}/{scored['per_class_total'][c]})")
    print(f"  clean FP rate: {scored['clean_fp_rate']:.3f}  ({scored['clean_fp']}/{scored['clean_total']})")
    if scored.get("lineage_walk"):
        lw = scored["lineage_walk"]
        print(f"  lineage-walk accuracy: {lw['accuracy']:.3f}  ({lw['correct']}/{lw['total']})")
    print(f"  GATE 1 (recall>= {gate['recall_floor']}, FP<= {gate['fp_ceiling']}): "
          f"{'PASS' if gate['pass'] else 'FAIL'}")
    if args.json:
        _write_json({"score": scored, "gate1": gate}, args.json)
    return 0 if gate["pass"] else 1


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog=__package__ or "releaseseal",
                                description=f"{APP_CODENAME} — offline model-release evidence verifier.")
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = p.add_subparsers(dest="command", required=True)

    s = sub.add_parser("snapshot", help="build a release snapshot")
    s.add_argument("--local", help="local release directory")
    s.add_argument("--hf", help="HF repo id (repo for --hf-fixture, or live fetch)")
    s.add_argument("--hf-fixture", dest="hf_fixture", help="recorded HF API bundle JSON (no network)")
    s.add_argument("--revision", default=None)
    s.add_argument("-o", "--output")
    s.set_defaults(func=cmd_snapshot)

    v = sub.add_parser("verify", help="run V1-V8 over a snapshot")
    v.add_argument("snapshot")
    v.add_argument("-o", "--output")
    v.add_argument("--as-of", dest="as_of", default=None)
    v.add_argument("--ci", action="store_true", help="exit 1 if any V1-V7 finding")
    v.set_defaults(func=cmd_verify)

    k = sub.add_parser("pack", help="build an evidence pack (+ optional report)")
    k.add_argument("snapshot")
    k.add_argument("-o", "--output")
    k.add_argument("--as-of", dest="as_of", default=None)
    k.add_argument("--report", help="also write a Markdown report")
    k.set_defaults(func=cmd_pack)

    vp = sub.add_parser("verify-pack", help="recheck an evidence pack offline")
    vp.add_argument("pack")
    vp.add_argument("--snapshot", help="also recheck snapshot hash")
    vp.set_defaults(func=cmd_verify_pack)

    b = sub.add_parser("bench", help="synthetic bench (Part A)")
    bsub = b.add_subparsers(dest="bench_cmd", required=True)
    bg = bsub.add_parser("generate", help="generate the dev split")
    bg.add_argument("--seed", type=int, default=0)
    bg.add_argument("--per-class", dest="per_class", type=int, default=12)
    bg.add_argument("--clean", type=int, default=36)
    bg.add_argument("--ext", action="store_true", help="also emit the dev_ext multi-level lineage manifest")
    bg.add_argument("-o", "--output", default="out/bench")
    bg.set_defaults(func=cmd_bench_generate)
    bs = bsub.add_parser("score", help="score a manifest")
    bs.add_argument("--manifest", required=True)
    bs.add_argument("--json", help="write full score JSON here")
    bs.set_defaults(func=cmd_bench_score)

    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())

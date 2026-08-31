#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import re
import subprocess
from collections import Counter
from datetime import datetime
from pathlib import Path

TOKEN_RE = re.compile(r"[A-Za-z0-9]+")
DATE_RE = re.compile(
    r"(?P<y>20\d{2})[-_](?P<m>\d{2})[-_](?P<d>\d{2})"
    r"(?:[_T -](?P<h>\d{2})[-:](?P<mi>\d{2})(?:[-:](?P<s>\d{2}))?)?"
)
STOP = {
    "the","and","for","from","with","this","that","into","after","before","drift",
    "log","incident","record","records","assistant","failure","failed"
}

def clean(v: str | None, default: str = "") -> str:
    if v is None:
        return default
    v = v.strip()
    return v if v else default

def git(repo: Path, *args: str) -> str:
    p = subprocess.run(
        ["git", "-C", str(repo), *args],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, encoding="utf-8", errors="strict", check=False,
    )
    if p.returncode:
        raise RuntimeError(f"git {' '.join(args)} failed: {p.stderr.strip()}")
    return p.stdout.strip()

def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))

def write_csv(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)

def tok(*parts: str) -> set[str]:
    result: set[str] = set()
    for part in parts:
        for t in TOKEN_RE.findall(part.lower()):
            if len(t) >= 3 and t not in STOP and not t.isdigit():
                result.add(t)
    return result

def ts(*parts: str) -> tuple[datetime, str] | None:
    for part in parts:
        m = DATE_RE.search(part)
        if not m:
            continue
        g = m.groupdict()
        precision = "SECOND" if g["s"] else ("MINUTE" if g["h"] and g["mi"] else "DATE")
        try:
            value = datetime(
                int(g["y"]), int(g["m"]), int(g["d"]),
                int(g["h"] or 0), int(g["mi"] or 0), int(g["s"] or 0),
            )
            return value, precision
        except ValueError:
            pass
    return None

def temporal(
    current: tuple[datetime, str] | None,
    candidate: tuple[datetime, str] | None,
) -> str:
    if current is None or candidate is None:
        return "UNKNOWN"
    current_dt, current_precision = current
    candidate_dt, candidate_precision = candidate
    if current_dt.date() != candidate_dt.date():
        return "OLDER" if candidate_dt.date() < current_dt.date() else "NEWER"
    if current_precision == "DATE" or candidate_precision == "DATE":
        return "UNKNOWN"
    if candidate_dt < current_dt:
        return "OLDER"
    if candidate_dt == current_dt:
        return "SAME_TIME"
    return "NEWER"

def jac(a: set[str], b: set[str]) -> float:
    return 0.0 if not a or not b else len(a & b) / len(a | b)

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--private-repo", required=True)
    ap.add_argument("--expected-private-head", required=True)
    ap.add_argument("--context-limit", type=int, default=20)
    args = ap.parse_args()

    repo = Path(args.private_repo)
    if not (repo / ".git").is_dir():
        raise SystemExit(f"Private repository missing: {repo}")
    if git(repo, "status", "--porcelain=v1", "--untracked-files=all"):
        raise SystemExit("Private repository is dirty; build not started.")
    head = git(repo, "rev-parse", "HEAD")
    if head != args.expected_private_head:
        raise SystemExit(f"Unexpected private checkpoint: expected={args.expected_private_head} actual={head}")

    original_path = repo / "adjudication-working/suitability-screening/excel-import/2026-08-30-completed-review-decisions.csv"
    replacement_intake_path = repo / "adjudication-working/replacement-review/intake/2026-08-31-completed-replacement-review.json"
    replacement_set_path = repo / "adjudication-working/replacement-review/replacement-review-set.csv"
    inventory_path = repo / "source-index/comprehensive/combined-drift-evidence-candidates.csv"
    out = repo / "adjudication-working/historical-context"

    for p in (original_path, replacement_intake_path, replacement_set_path, inventory_path):
        if not p.is_file():
            raise SystemExit(f"Required input missing: {p}")
    if out.exists():
        raise SystemExit(f"Historical-context output already exists: {out}")

    original = read_csv(original_path)
    replacements = read_csv(replacement_set_path)
    inventory = read_csv(inventory_path)
    original_ok = [r for r in original if clean(r.get("record_suitability")) == "SUITABLE"]
    if len(original_ok) != 78:
        raise SystemExit(f"Expected 78 original suitable observations; found {len(original_ok)}")

    intake = json.loads(replacement_intake_path.read_text(encoding="utf-8"))
    decisions = intake.get("decisions", [])
    if len(decisions) != 22 or any(clean(d.get("record_suitability")) != "SUITABLE" for d in decisions):
        raise SystemExit("Replacement intake must contain exactly 22 SUITABLE decisions.")

    repl_by_id = {clean(r.get("combined_candidate_id")): r for r in replacements}
    pool: list[dict[str, str]] = []
    for r in original_ok:
        pool.append({
            "pool_origin":"CORE_ORIGINAL",
            "packet_id":clean(r.get("packet_id")),
            "combined_candidate_id":clean(r.get("combined_candidate_id")),
            "source_repository":clean(r.get("source_repository")),
            "source_relative_path":clean(r.get("source_relative_path")),
            "source_model":clean(r.get("source_model"),"UNKNOWN"),
            "template_family":clean(r.get("template_family"),"UNKNOWN"),
            "evidence_path":clean(r.get("evidence_path")),
        })
    for d in decisions:
        cid = clean(d.get("combined_candidate_id"))
        r = repl_by_id.get(cid)
        if r is None:
            raise SystemExit(f"Replacement decision missing from review set: {cid}")
        pool.append({
            "pool_origin":"REPLACEMENT",
            "packet_id":clean(r.get("packet_id")),
            "combined_candidate_id":cid,
            "source_repository":clean(r.get("source_repository")),
            "source_relative_path":clean(r.get("source_relative_path")),
            "source_model":clean(r.get("source_model"),"UNKNOWN"),
            "template_family":clean(r.get("template_family"),"UNKNOWN"),
            "evidence_path":str(repo / "adjudication-working/replacement-review" / clean(r.get("evidence_relative_path"))),
        })
    if len(pool) != 100 or len({r["combined_candidate_id"] for r in pool}) != 100:
        raise SystemExit("Final suitable pool must contain exactly 100 unique candidate IDs.")

    inv = {}
    prepared = []
    for r in inventory:
        cid = clean(r.get("combined_candidate_id"))
        if not cid or cid in inv:
            raise SystemExit(f"Invalid or duplicate candidate ID in inventory: {cid}")
        inv[cid] = r
        title = clean(r.get("title"))
        path = clean(r.get("source_relative_path"))
        drift_id = clean(r.get("drift_id_raw"))
        recurrence = clean(r.get("recurrence_raw"))
        prepared.append({
            "row":r, "id":cid,
            "repo":clean(r.get("source_repository")),
            "model":clean(r.get("source_model"),"UNKNOWN"),
            "template":clean(r.get("template_family"),"UNKNOWN"),
            "blob":clean(r.get("source_git_blob_sha")).lower(),
            "drift_id":drift_id,
            "time":ts(drift_id,path,title),
            "tokens":tok(title,path,drift_id,recurrence),
        })

    case_rows: list[dict[str, object]] = []
    context_rows: list[dict[str, object]] = []

    for case_index, p in enumerate(pool, start=1):
        cid = p["combined_candidate_id"]
        c = inv.get(cid)
        if c is None:
            raise SystemExit(f"Suitable candidate missing from inventory: {cid}")
        title = clean(c.get("title"))
        path = clean(c.get("source_relative_path"))
        drift_id = clean(c.get("drift_id_raw"))
        recurrence = clean(c.get("recurrence_raw"))
        ctime = ts(drift_id,path,title)
        ctokens = tok(title,path,drift_id,recurrence)
        crepo = clean(c.get("source_repository"))
        cmodel = clean(c.get("source_model"),"UNKNOWN")
        ctemplate = clean(c.get("template_family"),"UNKNOWN")
        cblob = clean(c.get("source_git_blob_sha")).lower()

        scored = []
        for item in prepared:
            if item["id"] == cid:
                continue
            rel = temporal(ctime, item["time"])
            if rel in {"NEWER","SAME_TIME"}:
                continue
            score = 0.0
            reasons = []
            if cblob and item["blob"] and cblob == item["blob"]:
                score += 100; reasons.append("EXACT_GIT_BLOB")
            if drift_id and item["drift_id"] and drift_id.lower() == str(item["drift_id"]).lower():
                score += 90; reasons.append("SAME_DRIFT_ID_RAW")
            sim = jac(ctokens, item["tokens"])
            if sim:
                score += sim * 40; reasons.append(f"TOKEN_JACCARD={sim:.3f}")
            if crepo == item["repo"]:
                score += 6; reasons.append("SAME_REPOSITORY")
            if cmodel == item["model"]:
                score += 2; reasons.append("SAME_MODEL_GROUP")
            if ctemplate == item["template"]:
                score += 1; reasons.append("SAME_TEMPLATE_FAMILY")
            if rel == "OLDER":
                score += 3; reasons.append("EXPLICITLY_OLDER")
            else:
                reasons.append("TEMPORAL_RELATION_UNKNOWN")
            if "EXACT_GIT_BLOB" in reasons or "SAME_DRIFT_ID_RAW" in reasons or sim >= 0.08:
                scored.append((score, str(item["id"]), item, rel, reasons))

        scored.sort(key=lambda x: (-x[0], x[1]))
        selected = scored[:args.context_limit]
        for rank, (score, context_id, item, rel, reasons) in enumerate(selected, start=1):
            r = item["row"]
            context_rows.append({
                "case_index":case_index,
                "case_candidate_id":cid,
                "case_packet_id":p["packet_id"],
                "context_rank":rank,
                "context_candidate_id":context_id,
                "context_source_repository":clean(r.get("source_repository")),
                "context_source_relative_path":clean(r.get("source_relative_path")),
                "context_source_model":clean(r.get("source_model"),"UNKNOWN"),
                "context_template_family":clean(r.get("template_family"),"UNKNOWN"),
                "context_title":clean(r.get("title")),
                "context_drift_id_raw":clean(r.get("drift_id_raw")),
                "context_recurrence_raw":clean(r.get("recurrence_raw")),
                "context_git_blob_sha":clean(r.get("source_git_blob_sha")),
                "temporal_relation":rel,
                "retrieval_score":f"{score:.6f}",
                "retrieval_reasons":";".join(reasons),
                "ground_truth_assigned":"NO",
            })

        case_rows.append({
            "case_index":case_index,
            **p,
            "explicit_timestamp_status":(
                "DATE_ONLY" if ctime and ctime[1] == "DATE"
                else ("TIME_AVAILABLE" if ctime else "UNKNOWN")
            ),
            "retrieved_context_candidates":len(selected),
            "historical_context_status":"CANDIDATES_RETRIEVED" if selected else "NO_METADATA_MATCHES",
            "ground_truth_assigned":"NO",
        })

    out.mkdir(parents=True, exist_ok=False)
    write_csv(out / "suitable-pool-100.csv", case_rows, [
        "case_index","pool_origin","packet_id","combined_candidate_id","source_repository",
        "source_relative_path","source_model","template_family","evidence_path",
        "explicit_timestamp_status","retrieved_context_candidates","historical_context_status",
        "ground_truth_assigned",
    ])
    write_csv(out / "historical-context-candidates.csv", context_rows, [
        "case_index","case_candidate_id","case_packet_id","context_rank","context_candidate_id",
        "context_source_repository","context_source_relative_path","context_source_model",
        "context_template_family","context_title","context_drift_id_raw","context_recurrence_raw",
        "context_git_blob_sha","temporal_relation","retrieval_score","retrieval_reasons",
        "ground_truth_assigned",
    ])

    cc = Counter(r["historical_context_status"] for r in case_rows)
    tc = Counter(r["explicit_timestamp_status"] for r in case_rows)
    summary = {
        "schema_version":1,
        "private_checkpoint":head,
        "suitable_pool":100,
        "original_suitable":78,
        "replacement_suitable":22,
        "candidate_universe":len(inventory),
        "context_limit_per_case":args.context_limit,
        "context_rows":len(context_rows),
        "cases_with_context_candidates":cc.get("CANDIDATES_RETRIEVED",0),
        "cases_without_metadata_matches":cc.get("NO_METADATA_MATCHES",0),
        "cases_with_time_available":tc.get("TIME_AVAILABLE",0),
        "cases_with_date_only":tc.get("DATE_ONLY",0),
        "cases_with_unknown_timestamp":tc.get("UNKNOWN",0),
        "ground_truth_assigned":0,
        "method":"Deterministic metadata retrieval only; retrieval similarity is not relationship ground truth.",
        "next_gate":"Materialize retrieved historical evidence, review context sufficiency, then perform human relationship adjudication.",
    }
    (out / "build-summary.json").write_text(
        json.dumps(summary,indent=2,ensure_ascii=False) + "\n", encoding="utf-8", newline="\n"
    )
    readme = (
        "# M2 Historical-Context Candidate Index\n\n"
        "This private staging directory freezes the 100 human-screened suitable observations "
        "(78 original + 22 replacement) and creates deterministic metadata-only retrieval hints.\n\n"
        "This stage does not assign NEW, DUPLICATE, RECURRENCE, RELATED_BUT_DISTINCT, or "
        "INSUFFICIENT_EVIDENCE. Similarity is not ground truth.\n\n"
        "Known newer or same-time records are excluded only when timestamp precision safely supports "
        "that ordering. Same-day records with date-only evidence remain temporally UNKNOWN.\n"
    )
    (out / "README.md").write_text(readme, encoding="utf-8", newline="\n")

    status = git(repo, "status", "--porcelain=v1", "--untracked-files=all")
    unexpected = [
        line for line in status.splitlines()
        if line and not line.startswith("?? adjudication-working/historical-context/")
    ]
    if unexpected:
        raise SystemExit("Unexpected repository changes: " + " | ".join(unexpected))

    print("M2_HISTORICAL_CONTEXT_INDEX=SUCCESS")
    print("SuitablePool=100")
    print(f"CandidateUniverse={len(inventory)}")
    print(f"ContextRows={len(context_rows)}")
    print(f"CasesWithContextCandidates={cc.get('CANDIDATES_RETRIEVED',0)}")
    print(f"CasesWithoutMetadataMatches={cc.get('NO_METADATA_MATCHES',0)}")
    print(f"CasesWithTimeAvailable={tc.get('TIME_AVAILABLE',0)}")
    print(f"CasesWithDateOnly={tc.get('DATE_ONLY',0)}")
    print(f"CasesWithUnknownTimestamp={tc.get('UNKNOWN',0)}")
    print("GroundTruthAssigned=0")
    print(f"Output={out}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())

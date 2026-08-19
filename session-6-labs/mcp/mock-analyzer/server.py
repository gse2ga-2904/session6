#!/usr/bin/env python3
# =============================================================================
# server.py — mock static analyzer for embedded Python (FastMCP server + CLI)
#
# What:     A training-grade static analyzer for the course's CAN-stack Python
#           code. It emits findings in the same JSON shape a qualified
#           analyzer's MCP server would feed Copilot Chat. stdlib-`ast`
#           heuristic engine — NOT a qualified tool. In production the
#           qualified analyzer (at Bosch: Klocwork/Coverity class) is the
#           source of truth (ISO 26262-8 Cl. 11); this server exists so the
#           labs and the capstone (project F) need no analyzer license.
#
# Used by:  Session 5 · Labs 5.1/5.3 (remediation loop) and Session 7 ·
#           capstone starter (mcp/mock-analyzer — same file, copied).
#
# Run:      python3 server.py --selftest              # no deps, no network
#           (selftest also analyzes the repo's seeded target when present —
#            src/can_scheduler.py here, src/can_gateway/can_gateway.py
#            in the capstone copy — and asserts >=4 findings, >=2 mandatory)
#           python3 server.py path/to/file.py         # engine only, JSON out
#           export ANALYZER_TOKEN=dev-placeholder     # see secrets-setup.md
#           python3 server.py                         # MCP over stdio (fastmcp)
#           python3 server.py --http                  # MCP over Streamable HTTP
#
# Checkers implemented (subset consistent with SEEDED_DEFECTS.md; rule refs
# use BAPS — the Bosch Automotive Python Standard, MISRA-style):
#   CONC.SHARED_UNPROTECTED   callback/task shared module state, no lock
#   ABV.TAINTED               struct.unpack length/buffer from unvalidated input
#   DISPATCH.NO_DEFAULT       frame-type if/elif chain without an else
#   EXC.SWALLOWED             bare except / broad except that passes
#   DYN.CODE                  eval/exec/dynamic import in production paths
#   LOOP.UNBOUNDED            while True over external input without a break
#   LV.UNUSED_RESULT.SUSPICIOUS  '(?)'-marked residue operations
#
# NOTE: All data synthetic. Auth via ${ANALYZER_TOKEN} env var — never a
#       literal in code or committed config (secrets discipline, Session 3).
# =============================================================================

import ast
import hashlib
import json
import os
import sys
import time

MANDATORY_SEVERITIES = ("critical", "error")

_CALLBACK_HINTS = ("callback", "on_", "_cb", "rx", "irq", "handler")
_MUTATORS = {"append", "extend", "insert", "pop", "remove", "clear", "update",
             "setdefault", "add", "discard", "popleft", "appendleft", "sort"}
_MUTABLE_CTORS = {"list", "dict", "set", "deque", "defaultdict",
                  "OrderedDict", "Counter", "bytearray"}


# -----------------------------------------------------------------------------
# Lightweight module model: functions, module-level mutables, lock regions
# -----------------------------------------------------------------------------
class PyFile:
    def __init__(self, path: str, text: str):
        self.path = path
        self.raw_lines = text.splitlines()
        self.tree = ast.parse(text, filename=path)
        self.functions = [
            (n.name, n.lineno, getattr(n, "end_lineno", n.lineno), n)
            for n in ast.walk(self.tree)
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
        self.globals = self._find_globals()      # {name: line}
        self.lock_regions = self._find_lock_regions()

    def _find_globals(self):
        globs = {}
        for node in self.tree.body:
            if isinstance(node, ast.Assign) and len(node.targets) == 1 \
                    and isinstance(node.targets[0], ast.Name):
                v = node.value
                mutable = isinstance(v, (ast.List, ast.Dict, ast.Set)) or (
                    isinstance(v, ast.Call) and isinstance(v.func, ast.Name)
                    and v.func.id in _MUTABLE_CTORS)
                scalar = isinstance(v, ast.Constant)
                if mutable or scalar:
                    globs[node.targets[0].id] = node.lineno
        return globs

    def _find_lock_regions(self):
        """Line ranges of `with <something lock-ish>:` blocks."""
        regions = []
        for node in ast.walk(self.tree):
            if isinstance(node, (ast.With, ast.AsyncWith)):
                ctx = " ".join(ast.unparse(i.context_expr).lower()
                               for i in node.items)
                if "lock" in ctx or "mutex" in ctx:
                    regions.append((node.lineno,
                                    getattr(node, "end_lineno", node.lineno)))
        return regions

    def protected(self, lineno: int) -> bool:
        return any(a <= lineno <= b for a, b in self.lock_regions)

    def function_of(self, lineno: int) -> str:
        best = "(module scope)"
        for name, start, end, _n in self.functions:
            if start <= lineno <= end:
                best = name
        return best

    def excerpt(self, lineno: int) -> str:
        if 1 <= lineno <= len(self.raw_lines):
            return self.raw_lines[lineno - 1].strip()[:120]
        return ""

    def writers_readers(self, name: str):
        """Functions that mutate / read a module-level name (unprotected)."""
        writers, readers = {}, set()
        for fname, _s, _e, fnode in self.functions:
            has_global = any(isinstance(n, ast.Global) and name in n.names
                             for n in ast.walk(fnode))
            for node in ast.walk(fnode):
                line = getattr(node, "lineno", 0)
                if isinstance(node, ast.Name) and node.id == name:
                    readers.add(fname)
                if self.protected(line):
                    continue
                if isinstance(node, ast.AugAssign):
                    t = node.target
                    if (isinstance(t, ast.Name) and t.id == name and has_global) or \
                       (isinstance(t, ast.Subscript)
                            and isinstance(t.value, ast.Name)
                            and t.value.id == name):
                        writers.setdefault(fname, line)
                elif isinstance(node, ast.Assign):
                    for t in node.targets:
                        if isinstance(t, ast.Subscript) and \
                                isinstance(t.value, ast.Name) and t.value.id == name:
                            writers.setdefault(fname, line)
                        elif has_global and isinstance(t, ast.Name) and t.id == name:
                            writers.setdefault(fname, line)
                elif (isinstance(node, ast.Call)
                      and isinstance(node.func, ast.Attribute)
                      and node.func.attr in _MUTATORS
                      and isinstance(node.func.value, ast.Name)
                      and node.func.value.id == name):
                    writers.setdefault(fname, line)
        return writers, readers


def _looks_like_callback(fname: str) -> bool:
    low = fname.lower()
    return any(h in low for h in _CALLBACK_HINTS)


# -----------------------------------------------------------------------------
# Checkers — each yields dicts: checker, rule_ref, severity, line, message, trace
# -----------------------------------------------------------------------------
def chk_shared_unprotected(pf: PyFile):
    for name, dline in pf.globals.items():
        writers, readers = pf.writers_readers(name)
        if not writers:
            continue
        cb_side = {f for f in writers if _looks_like_callback(f)}
        task_side = set(writers) - cb_side
        if len(writers) >= 2 and cb_side and (task_side or len(readers) > len(writers)):
            yield dict(checker="CONC.SHARED_UNPROTECTED",
                       rule_ref="BAPS-07/BAPS-02; CWE-362",
                       severity="critical", line=dline,
                       message=f"Unprotected read-modify-write of '{name}' "
                               f"shared between callback context "
                               f"({', '.join(sorted(cb_side))}) and task "
                               f"context ({', '.join(sorted(task_side)) or '(readers)'}). "
                               "Check-then-act sequences on it race.",
                       trace=[f"{f}() mutates {name} (line {ln})"
                              for f, ln in sorted(writers.items())]
                             + ["no lock held on either path"])
        else:
            yield dict(checker="CONC.SHARED_UNPROTECTED",
                       rule_ref="BAPS-02; CWE-362",
                       severity="warning", line=dline,
                       message=f"Module-global '{name}' is mutated after init "
                               f"(by {', '.join(sorted(writers))}) without a "
                               "lock; encapsulate the state or guard it.",
                       trace=[pf.excerpt(dline)])


def chk_tainted_unpack(pf: PyFile):
    for fname, _s, _e, fnode in pf.functions:
        for node in ast.walk(fnode):
            if not (isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Attribute)
                    and node.func.attr in ("unpack", "unpack_from")
                    and len(node.args) >= 2):
                continue
            buf = node.args[1]
            buf_dump = ast.dump(buf)
            validated = False
            for sub in ast.walk(fnode):
                if isinstance(sub, ast.Compare) and sub.lineno <= node.lineno:
                    for inner in ast.walk(sub):
                        if (isinstance(inner, ast.Call)
                                and isinstance(inner.func, ast.Name)
                                and inner.func.id == "len" and inner.args
                                and ast.dump(inner.args[0]) == buf_dump):
                            validated = True
            if not validated:
                buf_src = ast.unparse(buf)
                yield dict(checker="ABV.TAINTED",
                           rule_ref="BAPS-01; CWE-20",
                           severity="critical", line=node.lineno,
                           message=f"struct.{node.func.attr} reads from "
                                   f"'{buf_src}' in {fname}() without a "
                                   "length check; an undersized or oversized "
                                   "payload raises or reads stale bytes. "
                                   "Validate len() before unpacking.",
                           trace=[f"{buf_src}: no len() bound check on any "
                                  f"path before line {node.lineno}"])


def chk_dispatch_no_default(pf: PyFile):
    elifs = set()
    for node in ast.walk(pf.tree):
        if isinstance(node, ast.If) and len(node.orelse) == 1 \
                and isinstance(node.orelse[0], ast.If):
            elifs.add(id(node.orelse[0]))
    for node in ast.walk(pf.tree):
        if not isinstance(node, ast.If) or id(node) in elifs:
            continue
        chain = [node]
        while len(chain[-1].orelse) == 1 and isinstance(chain[-1].orelse[0], ast.If):
            chain.append(chain[-1].orelse[0])
        subjects = []
        for link in chain:
            t = link.test
            if isinstance(t, ast.Compare) and len(t.ops) == 1 \
                    and isinstance(t.ops[0], ast.Eq):
                subjects.append(ast.dump(t.left))
            else:
                subjects.append(None)
        if (len(chain) >= 2 and not chain[-1].orelse
                and None not in subjects and len(set(subjects)) == 1):
            subject = ast.unparse(chain[0].test.left)
            yield dict(checker="DISPATCH.NO_DEFAULT",
                       rule_ref="BAPS-03; CWE-478",
                       severity="error", line=node.lineno,
                       message=f"Dispatch over '{subject}' in "
                               f"{pf.function_of(node.lineno)}() has no "
                               "explicit unknown-value case; unexpected "
                               "values fall through silently. Add an else "
                               "that reports the fault.",
                       trace=[f"{len(chain)} branches, no else"])


def chk_swallowed_exceptions(pf: PyFile):
    for node in ast.walk(pf.tree):
        if not isinstance(node, ast.ExceptHandler):
            continue
        if node.type is None:
            yield dict(checker="EXC.SWALLOWED",
                       rule_ref="BAPS-05; CWE-703",
                       severity="error", line=node.lineno,
                       message=f"Bare `except:` in "
                               f"{pf.function_of(node.lineno)}() — safety "
                               "paths must re-raise or fail closed, never "
                               "continue on unknown errors.",
                       trace=[pf.excerpt(node.lineno)])
        elif (isinstance(node.type, ast.Name)
              and node.type.id in ("Exception", "BaseException")
              and all(isinstance(b, ast.Pass) for b in node.body)):
            yield dict(checker="EXC.SWALLOWED",
                       rule_ref="BAPS-05; CWE-703",
                       severity="warning", line=node.lineno,
                       message=f"`except {node.type.id}: pass` in "
                               f"{pf.function_of(node.lineno)}() swallows "
                               "every error — log and fail closed instead.",
                       trace=[pf.excerpt(node.lineno)])


def chk_dynamic_code(pf: PyFile):
    for node in ast.walk(pf.tree):
        if not isinstance(node, ast.Call):
            continue
        name = None
        if isinstance(node.func, ast.Name) and \
                node.func.id in ("eval", "exec", "__import__"):
            name = node.func.id
        elif isinstance(node.func, ast.Attribute) and \
                node.func.attr == "import_module":
            name = "importlib.import_module"
        if name:
            yield dict(checker="DYN.CODE",
                       rule_ref="BAPS-06; CWE-95",
                       severity="critical", line=node.lineno,
                       message=f"{name}() in {pf.function_of(node.lineno)}() "
                               "— dynamic code execution in a production "
                               "path is not allowed.",
                       trace=[pf.excerpt(node.lineno)])


def chk_unbounded_loop(pf: PyFile):
    for node in ast.walk(pf.tree):
        if not isinstance(node, ast.While):
            continue
        if not (isinstance(node.test, ast.Constant) and node.test.value is True):
            continue
        if any(isinstance(n, (ast.Break, ast.Return)) for n in ast.walk(node)):
            continue
        yield dict(checker="LOOP.UNBOUNDED",
                   rule_ref="BAPS-04; CWE-835",
                   severity="warning", line=node.lineno,
                   message=f"`while True` in {pf.function_of(node.lineno)}() "
                           "has no break/return; loops over external input "
                           "must be bounded.",
                   trace=[pf.excerpt(node.lineno)])


def chk_suspicious_residue(pf: PyFile):
    for i, raw in enumerate(pf.raw_lines, 1):
        if "(?)" in raw:
            yield dict(checker="LV.UNUSED_RESULT.SUSPICIOUS",
                       rule_ref="BAPS (residue); CWE-561",
                       severity="review", line=i,
                       message="Operation marked '(?)' in source; possibly "
                               "dead or unjustified — flag for the author, do "
                               "not auto-fix.",
                       trace=[pf.excerpt(i)])


CHECKERS = [chk_shared_unprotected, chk_tainted_unpack,
            chk_dispatch_no_default, chk_swallowed_exceptions,
            chk_dynamic_code, chk_unbounded_loop, chk_suspicious_residue]

CHECKER_DOCS = {
    "CONC.SHARED_UNPROTECTED": "callback/task shared module state, unprotected (BAPS-02/07)",
    "ABV.TAINTED": "struct.unpack buffer/length from unvalidated input (BAPS-01)",
    "DISPATCH.NO_DEFAULT": "frame-type if/elif chain without an else (BAPS-03)",
    "EXC.SWALLOWED": "bare except / broad except that passes (BAPS-05)",
    "DYN.CODE": "eval/exec/dynamic import in production paths (BAPS-06)",
    "LOOP.UNBOUNDED": "while True over external input without a break (BAPS-04)",
    "LV.UNUSED_RESULT.SUSPICIOUS": "'(?)'-marked residue operation",
}


# -----------------------------------------------------------------------------
# Engine entry point — fixture-shaped result
# -----------------------------------------------------------------------------
def analyze_text(path: str, text: str) -> dict:
    try:
        pf = PyFile(path, text)
        findings = []
        for checker in CHECKERS:
            findings.extend(checker(pf))
    except SyntaxError as e:
        pf = None
        findings = [dict(checker="PARSE.ERROR", rule_ref="BAPS (parse)",
                         severity="error", line=e.lineno or 0,
                         message=f"file does not parse: {e.msg}", trace=[])]
    findings.sort(key=lambda f: (f["line"], f["checker"]))
    build = hashlib.sha256(text.encode()).hexdigest()[:4]
    out = []
    for n, f in enumerate(findings, 1):
        out.append({
            "finding_id": f"MA-{build}-{n:03d}",
            "checker": f["checker"],
            "rule_ref": f["rule_ref"],
            "severity": f["severity"],
            "line": f["line"],
            "function": pf.function_of(f["line"]) if pf else "(module scope)",
            "message": f["message"],
            "code_excerpt": pf.excerpt(f["line"]) if pf else "",
            "trace": f["trace"],
        })
    return {
        "analysis": {
            "tool": "MockAnalyzer (qualified-analyzer-shaped, training)",
            "tool_version": "2026.1-mock",
            "project": os.environ.get("ANALYZER_PROJECT", "training"),
            "build_id": f"ma-build-{build}",
            "file": path,
            "taxonomy": ["BAPS", "CWE"],
            "generated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        },
        "findings": out,
        "summary": {
            "total": len(out),
            "mandatory": sum(1 for f in out
                             if f["severity"] in MANDATORY_SEVERITIES),
            "by_severity": {s: sum(1 for f in out if f["severity"] == s)
                            for s in ("critical", "error", "warning", "review")},
        },
    }


def analyze_path(path: str) -> dict:
    with open(path, encoding="utf-8", errors="replace") as fh:
        return analyze_text(path, fh.read())


# -----------------------------------------------------------------------------
# Self-test — embedded samples, no filesystem or network dependencies
# -----------------------------------------------------------------------------
_SEEDED_SAMPLE = '''
import struct

QUEUE_DEPTH = 16
rx_queue = []
stats = {"stored": 0}
fault_flag = 0

def rx_callback_store(raw_len, payload):
    if len(rx_queue) >= QUEUE_DEPTH:
        return
    first = struct.unpack_from(">H", payload, 0)[0]
    rx_queue.append(bytes(payload[:raw_len]))
    stats["stored"] += 1
    if first == 1:
        stats["a"] = stats.get("a", 0) + 1
    elif first == 2:
        stats["b"] = stats.get("b", 0) + 1

def pump_task(handler_name):
    global fault_flag
    handler = eval(handler_name)
    while True:
        try:
            handler(rx_queue.pop(0))
        except:
            fault_flag = 1          # keep pumping (?)

def fault_task():
    global fault_flag
    fault_flag = 0
'''

_CLEAN_SAMPLE = '''
import struct
import threading

LEN_MAX = 8
_lock = threading.Lock()
_level = 0

def set_level(payload):
    """Store the level signal after validating the payload length."""
    global _level
    if len(payload) < 2:
        raise ValueError("short payload")
    value = struct.unpack_from(">H", payload, 0)[0]
    with _lock:
        _level = min(value, LEN_MAX)
    return _level
'''

_EXPECTED_CHECKERS = {
    "CONC.SHARED_UNPROTECTED", "ABV.TAINTED", "DISPATCH.NO_DEFAULT",
    "EXC.SWALLOWED", "DYN.CODE", "LOOP.UNBOUNDED",
    "LV.UNUSED_RESULT.SUSPICIOUS",
}

# Seeded lab targets, relative to this file. The first one found is analyzed
# during --selftest (labs-repo layout first, then the Session 5 and
# capstone-starter layouts — the same file is deployed in all three places;
# keep the copies in sync).
_SEEDED_TARGETS = (
    os.path.join("..", "..", "src", "can_scheduler.py"),
    os.path.join("..", "review-target", "can_scheduler.py"),
    os.path.join("..", "..", "src", "can_gateway", "can_gateway.py"),
)


def _selftest_seeded_target() -> None:
    here = os.path.dirname(os.path.abspath(__file__))
    for rel in _SEEDED_TARGETS:
        path = os.path.normpath(os.path.join(here, rel))
        if not os.path.isfile(path):
            continue
        print(f"selftest: seeded repo target ({os.path.basename(path)}) ...",
              end=" ")
        r = analyze_path(path)
        total, mandatory = r["summary"]["total"], r["summary"]["mandatory"]
        assert total >= 4, f"expected >=4 findings on {path}, got {total}"
        assert mandatory >= 2, \
            f"expected >=2 mandatory findings on {path}, got {mandatory}"
        print(f"ok ({total} findings, {mandatory} mandatory)")
        return
    print("selftest: seeded repo target ... skipped (none of "
          f"{_SEEDED_TARGETS} found next to the server)")


def _selftest() -> int:
    print("selftest: seeded sample fires every checker ...", end=" ")
    r = analyze_text("seeded_sample.py", _SEEDED_SAMPLE)
    fired = {f["checker"] for f in r["findings"]}
    missing = _EXPECTED_CHECKERS - fired
    assert not missing, f"checkers did not fire: {missing}"
    print(f"ok ({r['summary']['total']} findings, "
          f"{r['summary']['mandatory']} mandatory)")

    print("selftest: clean sample yields no mandatory findings ...", end=" ")
    r = analyze_text("clean_sample.py", _CLEAN_SAMPLE)
    assert r["summary"]["mandatory"] == 0, r["findings"]
    print("ok")

    print("selftest: result matches the fixture schema ...", end=" ")
    for key in ("analysis", "findings", "summary"):
        assert key in r
    for key in ("tool", "tool_version", "project", "build_id", "file",
                "taxonomy", "generated"):
        assert key in r["analysis"]
    print("ok")

    _selftest_seeded_target()
    return 0


# -----------------------------------------------------------------------------
# MCP wrapper (optional — engine and selftest never need fastmcp)
# -----------------------------------------------------------------------------
def _serve(http: bool) -> int:
    try:
        from fastmcp import FastMCP
    except ImportError:
        print("fastmcp is not installed. Engine still works:\n"
              "  python3 server.py <file.py>       # direct analysis\n"
              "  python3 server.py --selftest      # sanity check\n"
              "Install for MCP serving: pip install fastmcp", file=sys.stderr)
        return 1

    token = os.environ.get("ANALYZER_TOKEN")
    if not token:
        print("Secret 'ANALYZER_TOKEN' not set. Follow secrets-setup.md — "
              "do not paste secrets into code or mcp.json.", file=sys.stderr)
        return 1

    mcp = FastMCP(
        "mock-analyzer",
        instructions=(
            "Training static analyzer for embedded CAN-stack Python. The "
            "analyzer is the SOURCE OF TRUTH for compliance findings: "
            "propose fixes for mechanical findings only, re-check every "
            "patch, and leave judgmental rules (residue markers, deviation "
            "requests) flagged for a human."
        ),
    )

    @mcp.tool(name="analyze_file")
    def analyze_file(path: str) -> dict:
        """Run the BAPS/CWE checker set over one Python source file.

        Returns analyzer-shaped JSON: analysis metadata, findings
        (checker, rule_ref, severity, line, message, trace), and a summary
        with the mandatory-violation count."""
        if not os.path.isfile(path):
            return {"error": f"no such file: {path}"}
        return analyze_path(path)

    @mcp.tool(name="analyze_source")
    def analyze_source(code: str, filename: str = "snippet.py") -> dict:
        """Run the BAPS/CWE checker set over Python source passed inline.

        Use this when the code is not on disk (a chat snippet, a proposed
        patch). Same analyzer-shaped result as analyze_file; `filename` is
        only used for reporting."""
        return analyze_text(filename, code)

    @mcp.tool(name="list_checkers")
    def list_checkers() -> dict:
        """List the implemented checkers and what each one detects."""
        return {"checkers": CHECKER_DOCS,
                "mandatory_severities": list(MANDATORY_SEVERITIES)}

    @mcp.resource("analyzer://ruleset")
    def ruleset() -> dict:
        """Checker catalog: id -> what it detects, plus which severities are
        mandatory (fail CI) and the taxonomies referenced."""
        return {
            "tool": "MockAnalyzer (qualified-analyzer-shaped, training)",
            "tool_version": "2026.1-mock",
            "taxonomy": ["BAPS", "CWE"],
            "checkers": CHECKER_DOCS,
            "mandatory_severities": list(MANDATORY_SEVERITIES),
            "note": ("Training-grade ast/heuristic engine — not a "
                     "qualified tool (ISO 26262-8 Cl. 11)."),
        }

    if http:
        mcp.run(transport="http", host="127.0.0.1", port=8391)
    else:
        mcp.run()  # stdio
    return 0


def main(argv) -> int:
    if "--selftest" in argv:
        return _selftest()
    files = [a for a in argv if not a.startswith("-")]
    if files:
        for f in files:
            print(json.dumps(analyze_path(f), indent=2))
        return 0
    return _serve("--http" in argv)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

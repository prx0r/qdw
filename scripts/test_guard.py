#!/usr/bin/env python3
from qdw.proof.test_guard import scan_test_tree

def main():
    findings=scan_test_tree("tests")
    for f in findings:
        print(f"{f.path}:{f.line} {f.code} {f.message}")
    print(f"test_guard_findings={len(findings)}")
    return 1 if findings else 0

if __name__=="__main__":
    raise SystemExit(main())

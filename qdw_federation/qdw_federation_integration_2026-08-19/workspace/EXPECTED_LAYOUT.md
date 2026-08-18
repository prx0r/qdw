# Expected agent workspace

```text
integration-workspace/
├── pack/              # this extracted ZIP
├── worktrees/
│   ├── qdw/
│   ├── qdw-forge/
│   ├── qdw-sandbox/
│   ├── gitgoblin/
│   └── dell/
├── .integration-venvs/
├── evidence/
│   ├── baseline/
│   ├── failing-contracts/
│   ├── passing-contracts/
│   ├── v10/
│   └── v11/
└── reports/
```

Do not nest external Git repositories inside QDW's Git repository.

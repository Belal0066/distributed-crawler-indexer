# Phase 1: Project Inception and Core Architecture (Weeks 1–2)

## Focus

- Establish project foundations
- Define and document core architecture
- Set up initial cloud infrastructure
- Plan tasks and timeline for the full development cycle

---

## Activities

### 1. Team Formation and Roles


  - Cloud and Testing: Omar `21`
  - Crawler: Ahemd `21`
  - Indexer: Salah `21`
  - Architect: Belal Anas `21P0072`
  

---


### 2. Technology Deep Dive



---

### 4. System Architecture Design

- System component interactions:
  - Client, Master, Crawler, Indexer, Task Queue, Storage

- Architecture diagrams
- Data flow charts
- API/interface designs
- Storage schemas
- Fault tolerance plans

---

### 5. Detailed Project Planning

- phases into sub-tasks (jira issues)
- tasks to team members
- Gantt chart:
  - Task durations
  - Dependencies
  - Milestones for each phase

---

### 6. Cloud Environment Setup (Basic)



---

### 7. Initial Code Repository Setup

```shell
├── .github/             # For GitHub Actions (CI/CD) later
│   └── workflows/
├── requirements.txt     # Python dependencies (or use Poetry/Pipenv)
├── config/              # Configuration files (non-secret)
│   └── settings.yaml    # Example config
├── src/                 # Main source code
│   ├── crawler/         # Code specific to crawler nodes
│   ├── indexer/         # Code specific to indexer nodes
│   ├── master/          # Code for the master/controller node
│   ├── common/          # Shared code (utils, data models)
│   └── main.py          # Entry point if needed (e.g., for master)
├── tests/               # Unit and integration tests
│   ├── test_x.py 
├── scripts/             # Helper scripts (deployment, setup, etc.)
│   └── start_x.py   # Example script 
└── docs/                # Project documentation (optional)
    └── architecture.md  # Detailed architecture description
```


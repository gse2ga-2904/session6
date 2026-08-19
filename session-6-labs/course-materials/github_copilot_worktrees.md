## What is Git Worktree?

**Git Worktree** is a Git feature that allows you to have **multiple working directories connected to the same Git repository**, with each directory checked out to a different branch.

Normally, when you work with Git, you have one working directory:

```text
my-project/
├── .git/
├── src/
├── tests/
└── README.md
```

If you want to work on another branch, you typically do:

```bash
git switch feature/login
```

This changes the files in your working directory to match that branch.

With **Git Worktree**, you can have several branches checked out **at the same time**:

```text
my-project/
    └── main branch

my-project-login/
    └── feature/login branch

my-project-security/
    └── feature/security branch
```

All three worktrees share the same underlying Git repository.

---

## Why is this useful?

Imagine you are developing a web application and currently working on:

```text
feature/payment
```

Suddenly, your team asks you to fix an urgent bug in:

```text
main
```

Without worktrees, you might have to:

```bash
git stash
git switch main
# fix bug
git switch feature/payment
git stash pop
```

With worktrees, you can simply create another directory:

```bash
git worktree add ../bugfix main
```

Now you have:

```text
projects/
├── my-project/       # feature/payment
└── bugfix/           # main
```

You can work on the bug in `bugfix/` while leaving your payment feature completely untouched.

---

## Basic Git Worktree commands

### 1. Create a worktree

Suppose your current repository is:

```text
my-project/
```

Create a worktree for the `develop` branch:

```bash
git worktree add ../my-project-develop develop
```

Git creates:

```text
my-project/
my-project-develop/
```

The original directory might contain:

```text
feature/payment
```

while the new directory contains:

```text
develop
```

---

### 2. Create a new branch and worktree

You can also create a **new branch at the same time**:

```bash
git worktree add -b feature/login ../my-project-login main
```

This means:

> Create a new branch called `feature/login`, starting from `main`, and check it out in `../my-project-login`.

You now have:

```text
my-project/          → existing branch
my-project-login/    → feature/login
```

---

### 3. See all worktrees

Use:

```bash
git worktree list
```

For example:

```text
C:/projects/my-project          abc1234 [feature/payment]
C:/projects/my-project-login    def5678 [feature/login]
C:/projects/my-project-hotfix   789abcd [main]
```

This is particularly useful when working on several tasks simultaneously.

---

### 4. Remove a worktree

When you finish the work:

```bash
git worktree remove ../my-project-login
```

This removes the worktree, but **does not automatically delete the branch**.

If you also want to delete the branch:

```bash
git branch -d feature/login
```

---

# Worktree vs. normal branch switching

Consider this situation:

| Approach                  | Working directories | Branches simultaneously checked out |
| ------------------------- | ------------------: | ----------------------------------: |
| Normal Git                |                   1 |                                   1 |
| Git Worktree              |            Multiple |                            Multiple |
| Git Worktree + 3 branches |                   3 |                                   3 |

### Without Worktree

```text
my-project/
     │
     └── feature/A
             ↓
        git switch feature/B
             ↓
        feature/B
```

The same directory changes between branches.

### With Worktree

```text
                 ┌── feature/A
                 │
Git repository ──┼── feature/B
                 │
                 └── feature/C
```

Each branch has its own working directory.

---

# An important concept: shared Git repository

A worktree is **not three independent Git repositories**.

Conceptually:

```text
                 Shared Git repository
                         │
          ┌──────────────┼──────────────┐
          │              │              │
       Worktree        Worktree       Worktree
          │              │              │
       branch A       branch B       branch C
```

The worktrees share Git's repository data, while each worktree has its own set of checked-out files.

This makes worktrees more efficient than simply cloning the repository multiple times.

---

# When should developers use Worktrees?

Worktrees are particularly useful when you need to work on **multiple branches simultaneously**.

### Example 1 — Feature + bug fix

```text
project/
├── feature-payment/
└── hotfix-production/
```

You can develop the payment feature while simultaneously fixing a production problem.

### Example 2 — Code review

Suppose you are reviewing:

```text
feature/security
```

You can create a worktree:

```bash
git worktree add ../review-security feature/security
```

Now you can compile and test that branch without disturbing your current development work.

### Example 3 — Multiple versions

You might need:

```text
project-main/       → main
project-release/    → release/2.0
project-feature/    → feature/new-api
```

Each directory can be opened independently in your IDE.

---

# Worktree and IDEs

Worktrees are particularly convenient with IDEs such as VS Code.

You could have:

```text
VS Code Window 1
    my-project/
    feature/payment

VS Code Window 2
    my-project-login/
    feature/login

VS Code Window 3
    my-project-hotfix/
    main
```

Each window works on a different branch without repeatedly switching branches.

---

# A practical beginner workflow

Imagine you start with:

```bash
git clone https://github.com/example/my-app.git
cd my-app
```

You are working on:

```text
main
```

Create a feature:

```bash
git worktree add -b feature/login ../my-app-login main
```

Now:

```text
my-app/              → main
my-app-login/        → feature/login
```

Work on the login feature:

```bash
cd ../my-app-login
```

Make changes:

```bash
git add .
git commit -m "Implement login"
```

Meanwhile, you can return to the original directory:

```bash
cd ../my-app
```

and work on `main`.

No `git stash` is required simply to move between these tasks.

---

## A useful mental model

For an introductory Git class, think of **branches as different versions of the project** and **worktrees as different physical folders where those versions can live simultaneously**.

```text
Branch                  Worktree
──────                  ────────
main          ───────→  folder A
feature/login ───────→  folder B
feature/api   ───────→  folder C
```

So the key idea is:

> **Git branch = version of the project.**
> **Git worktree = a working directory associated with a branch.**

Worktrees are especially valuable for developers who frequently need to **switch between features, review pull requests, investigate bugs, or maintain release branches** without constantly changing the state of their main working directory.

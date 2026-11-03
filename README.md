# library-loans-api
A small but complete lending service for a fictional community library, Maple Street Library. The API manages books, copies, members, loans, and fines. The lending rules live in the database and the service layer, not in the client, so a bad request cannot break them.

- **Repository:** `library-loans-api`
- **Weeks:** 1–4 of the 5-month programme (Mini-project 1)
- **Team:** 8 members, one chunk each per week. Chunk owners and their weekly builds are in the week tables below.
- **Plan:** `Harbour_5_Month_Plan.md` in the roadmap folder.

---

A small but complete lending service for a fictional community library, Maple Street Library. The API manages books, copies, members, loans, and fines. The lending rules live in the database and the service layer, not in the client, so a bad request cannot break them.

## What you are building

A web API that lets library staff:

- add books and copies, and search books by title or author;
- register members, and suspend or reactivate them;
- borrow a copy to a member, and return it;
- see each member's loans and unpaid fines, and record payments.

## Business rules

These rules are the specification. Write them into the README's rules table in Week 2, and test each one.

| Rule | Value (configurable) |
|---|---|
| Loan period | 14 days from the borrow date |
| Loan limit per member | 3 active loans |
| Late fine | 50 minor units (kobo) per late day |
| Fine cap per loan | 2,000 minor units (kobo) |
| Borrowing blocked when | the member is suspended, or has unpaid fines |
| Time zone | UTC (state this in the README, since it is a limit) |

Money is stored as integer minor units, never floats.

## Requirements and acceptance checks

1. **Books and copies.** Create a book with ISBN, title and authors. Add copies to it. ISBN is unique. Search is case-insensitive.
2. **Members.** Create, read and update a member. Status is `active` or `suspended`.
3. **Borrow.** Borrowing creates a loan with a due date. It fails with a clear error if no copy is free, the limit is reached, or the member is blocked.
4. **Return.** Returning closes the loan, frees the copy, and calculates any late fine using the rules above.
5. **Fines and payments.** List a member's unpaid fines. Accept partial payments. A fine is fully paid when the total paid equals the amount.
6. **Concurrency.** Two requests that borrow the last copy at the same time must not both succeed. A test must prove this against real PostgreSQL.
7. **Errors.** Unknown IDs return 404. Business-rule failures return 409. Invalid input returns 422. Every error body has a stable `code` field and a `message`.
8. **Schema.** Schema changes go through Alembic migrations. The database enforces unique ISBNs, foreign keys, and positive amounts with check constraints.
9. **Configuration.** Settings load through pydantic-settings from environment variables. `.env.example` lists every variable. No secret is committed.
10. **Tests.** pytest runs against a real PostgreSQL container. Every business rule has at least one test. Invalid input is tested too.
11. **Run from a clean clone.** `docker compose up` starts the API and PostgreSQL together. A health-check endpoint reports ready only when the database answers.
12. **Continuous integration.** GitHub Actions runs ruff, mypy and pytest on every pull request. A red build blocks the merge.
13. **Documentation.** The README gives run steps, the rules table, the endpoint list, the known limits, and the AI-use log.

## Libraries

Python 3.12, uv, FastAPI, Pydantic, pydantic-settings, SQLAlchemy 2.0, psycopg 3, Alembic, PostgreSQL, pytest, httpx (test client), uvicorn, Docker and Docker Compose, GitHub Actions, ruff, mypy.

## Not in this project

Login and roles, payments, email reminders, a web front end, and real member data. Each one is a limit to write down, not a gap to hide.

## Known limits to document

- Anyone who can reach the API can change loans. There is no login.
- Fines are a flat daily amount with a cap. There are no grace periods or tiers.
- Time is UTC only.
- Only one library branch exists in the data model.

## Done when

- A fresh clone runs with `docker compose up`, and `pytest` passes against PostgreSQL.
- CI is green on the pull request that merges to main.
- Each member can explain one borrow request from the HTTP input through the service layer to the database and back.
- The README lists the known limits.
- Harbour's core API skeleton (Week 4) is built in the Harbour repository, from the same pattern but with its own code.

## Weekly build plan

Each week, every member builds the piece for their chunk on Friday, 10:00–13:00, in this repository. The Harbour step for the same week runs 13:00–17:00 in the Harbour repository.

### Week 1: Python fundamentals and the problem-solving process

**Friday milestone:** Repository created and first pull request merged  
**Harbour step (Friday 13:00–17:00):** Harbour repository created with README, scope and known limits; first pull request merged.

| Member | Chunk | Friday build |
|---|---|---|
| Member 1 | Variables, types and the Python data model | Write a typed function that calculates loan due dates, with a docstring and three checks in a notebook |
| Member 2 | Functions, arguments and scope | Refactor a long fine-calculation function into small pure functions and explain each step |
| Member 3 | Lists and tuples: indexing, slicing and cost | Benchmark list vs set membership for checking book IDs across 100,000 items |
| Member 4 | Dicts and sets: lookups and hashing | Count title words across a catalogue of 500 books and explain the data structure |
| Member 5 | Loops, comprehensions and readability | Rewrite one loop as a comprehension that lists overdue loans; argue which is clearer |
| Member 6 | Exceptions and reading tracebacks | Raise a custom error for an unknown book ID and handle it |
| Member 7 | Problem-solving: restate, examples, plan, test, reflect | Write a problem-solving log for one exercise, step by step |
| Member 8 | Git basics: commits, branches and pull requests | Create the mini-project repository and open the first pull request |

### Week 2: HTTP, REST and core problem-solving patterns

**Friday milestone:** API contract agreed by the team  
**Harbour step (Friday 13:00–17:00):** Harbour API contract agreed and written as an OpenAPI file.

| Member | Chunk | Friday build |
|---|---|---|
| Member 1 | REST resources, methods and naming | Write the status-code table for every endpoint, with reasons |
| Member 2 | Status codes and error response design | Analyse the Big-O of the book search function and name the bottleneck |
| Member 3 | Safe and idempotent methods | Solve a sliding-window problem on daily loan counts |
| Member 4 | Big-O notation with worked examples | Detect duplicate loan IDs in one pass with a dictionary |
| Member 5 | Two pointers and sliding window | Check that a shelf-layout configuration has balanced brackets |
| Member 6 | Hashing patterns: frequency counts and two-sum | Simulate a returns desk with a queue and measure wait times |
| Member 7 | Stacks and queues: bracket checks and level-order processing | Write the API contract document and get it reviewed |
| Member 8 | Anatomy of an HTTP request and response | Draft the endpoints for books, members and loans, with methods |

### Week 3: SQL and PostgreSQL basics

**Friday milestone:** Schema v1 with migration script  
**Harbour step (Friday 13:00–17:00):** Harbour schema v1 with an Alembic migration.

| Member | Chunk | Friday build |
|---|---|---|
| Member 1 | SELECT, WHERE and NULL behaviour | Query books with no copies on the shelf |
| Member 2 | Joins: inner, left and anti-join | Write an anti-join: books never borrowed |
| Member 3 | Aggregates, GROUP BY and HAVING | Calculate fines per member; store money as integer cents and explain why |
| Member 4 | Indexes and reading EXPLAIN output | Add an index, run EXPLAIN before and after, and explain the change |
| Member 5 | Transactions and isolation basics | Show a rollback when a loan update fails mid-transaction |
| Member 6 | Designing the library schema: books, copies, members, loans, fines, versioned with Alembic | Write the first Alembic migration and apply it to Postgres |
| Member 7 | Tables, data types and primary keys | Create books and members tables with constraints; explain each |
| Member 8 | Constraints and normalisation with a library example | Add a foreign key and show a rejected bad insert |

### Week 4: FastAPI, validation, tests, Docker and CI (Mini-project 1)

**Friday milestone:** Mini-project 1 demo and Month 1 check.  
**Harbour step (Friday 13:00–17:00):** Harbour core API skeleton: FastAPI, SQL, tests and Docker.

| Member | Chunk | Friday build |
|---|---|---|
| Member 1 | Layering: routers, services and repositories | Move borrowing rules into the service layer |
| Member 2 | pytest fixtures, the FastAPI test client (httpx) and a test database | Write tests for the loan endpoints, including invalid input |
| Member 3 | Dockerfile and Docker Compose for API and Postgres | Write the Compose file with a health check and verify it runs |
| Member 4 | Configuration with pydantic-settings and environment variables | Load settings from environment variables and document them without secrets |
| Member 5 | GitHub Actions: ruff lint, mypy type-check and pytest on every pull request | Set up the CI workflow with ruff, mypy and pytest, and get a green build on a pull request |
| Member 6 | FastAPI routing, path and query parameters, served with uvicorn | Implement book and loan CRUD endpoints |
| Member 7 | Pydantic models and validation errors | Add Pydantic validation, including ISBN format and due-date rules |
| Member 8 | Database access: psycopg 3 driver and SQLAlchemy 2.0 sessions | Implement the loan repository with SQLAlchemy |

---

## How we work on this project

- Each member owns one chunk each week and writes that chunk's core logic by hand.
- Explain before merge: no pull request merges until its author explains it live to a reviewer, without the screen.
- Every pull request states what AI helped with and how the author checked it.
- Fictional data only. No real customer, student, or staff data enters this repository.
- This repository stands alone. No code is imported from another project's repository. Ideas that cross over are rewritten here, and the README says where they came from.
- Each Friday, 10:00–13:00 is this project's build. The Harbour step runs 13:00–17:00 in the Harbour repository.

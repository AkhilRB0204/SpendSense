# SpendSense – Development Progress Log

## Overview

This document is a personal development log for **SpendSense**, an AI-powered expense tracking backend I built step by step. I wrote this to honestly capture what I worked on, what broke, what confused me, how I fixed things, and what I learned along the way.

Each phase builds on the previous one, gradually adding complexity in a way that mirrors how real software evolves.

---

## Phase 1 – Core Backend Prototype

### Goal
My goal in Phase 1 was simple: get a backend working. I wanted to show that the core idea behind SpendSense made sense before worrying about databases, authentication, or scalability.

### What I Built
I started by setting up a FastAPI server running locally with Uvicorn. I added basic POST and GET endpoints that allowed me to create and retrieve expenses. Instead of a database, I stored everything in memory using Python lists and dictionaries.

FastAPI’s automatic Swagger UI became my main way of testing endpoints. I also kept the project in a Git repository and made small, incremental commits so I could track changes and mistakes as I went.

### Problems I Ran Into
At this stage, most of my issues came from inexperience rather than complexity. I was initially confused about how FastAPI generated Swagger documentation and how request models affected what showed up. I also kept forgetting that in-memory data disappears every time the server restarts, which led to a few “why is everything gone?” moments.

Endpoint naming was another issue. As I experimented, the API started to feel inconsistent.

### What I Learned
Phase 1 taught me some core backend fundamentals:
- How FastAPI request and response models actually work
- Why persistence matters, even for small applications
- How useful Swagger UI is for debugging and validating APIs

This phase gave me confidence that the idea was worth continuing, even though the implementation was still very rough.

---

## Phase 2 – Database & Persistence

### Goal
In Phase 2, I wanted to turn SpendSense into something more realistic by adding persistence and structure. This meant introducing a database, enforcing relationships, and cleaning up the project layout.

### Tech Stack Added
To do this, I added:
- SQLite for local development
- SQLAlchemy as the ORM
- Pydantic schemas for validation
- A more organized project structure (`models.py`, `database.py`, `schemas.py`, `crud.py`)

### Database Design
I designed a simple relational schema that made sense for expense tracking:
- Users store basic user information
- Categories represent spending categories
- Expenses link users to categories with amounts and timestamps

All relationships were explicitly defined using SQLAlchemy relationships so that the data model stayed clear and consistent.

### API Endpoints Implemented
I added endpoints to:
- Create users (with duplicate email checks)
- Create categories (with duplicate checks)
- Create expenses tied to valid users and categories

I also added a temporary `/debug` endpoint that returned all stored data, which helped a lot during development.

### Major Problems I Encountered (and Fixed)
Model and schema mismatches were one of the biggest pain points. I would reference fields like `username` in one place and `name` in another, or use `category_name` when the column was just `name`. These small inconsistencies caused confusing errors.

Fixing this meant standardizing naming across SQLAlchemy models, Pydantic schemas, and route logic. It made me realize how fragile backend systems become when naming isn’t consistent.

I also ran into repeated warnings about `orm_mode` being renamed to `from_attributes` in Pydantic v2. While this wasn’t breaking anything, I made sure to understand why the warning existed instead of ignoring it.

Another major learning moment came from HTTP errors. I saw a lot of 422, 404, and 500 responses, and at first they felt random. Over time, I learned how to trace each error back to schema validation, missing records, or logic bugs.

Import errors and circular dependencies forced me to actually understand Python’s module resolution system instead of guessing. Even small issues like messing up Uvicorn commands taught me how important precision is when working with backend tools.

---

## Phase 3 – Authentication, Multi-user Security & Expense Summaries

### Goal
The goal of Phase 3 was to make SpendSense usable by multiple users in a secure way. This meant adding authentication, protecting data, and generating meaningful summaries instead of just raw expense entries.

### What I Built
I implemented user authentication using OAuth2 password flow and JWT tokens. Users can log in, receive an access token, and use that token to access protected endpoints. I created a reusable `get_current_user` dependency so authentication logic wasn’t repeated everywhere.

Passwords are securely hashed using bcrypt via passlib, and plaintext passwords are never stored.

I also enforced multi-user security at the CRUD level. Users can only see and modify their own expenses, and all queries are scoped to the authenticated user.

On top of that, I built advanced monthly expense summaries that calculate total spending, average daily spending, total days in the month, and category-level breakdowns. All of this logic lives in `crud.py`, which allowed my route handlers to stay clean and readable.

### What I Learned
Phase 3 taught me:
- How OAuth2 password flow works in FastAPI
- How JWT-based authentication fits into backend design
- How to safely support multiple users
- Why centralizing business logic makes the codebase easier to maintain

---

## Phase 4 – AI Integration

### Goal
In Phase 4, I wanted to turn SpendSense into something more than a standard expense tracking app. The goal was to let users interact with their financial data using natural language and get meaningful insights back.

### What I Built
I started by building a query-to-intent mapping system that analyzes user input and determines what they are actually asking. I defined different intent types and mapped them to common phrases. For example, queries like “biggest expense” or “largest spending” map to a `highest_expense` intent.

Once the intent is identified, the request is passed to a processor function that runs the appropriate database queries. These functions handle things like monthly totals, category breakdowns, anomaly detection, and basic spending insights based on historical data.

### Challenges I Ran Into
One major challenge was date parsing. Users might enter dates in many formats, such as `12/15/2025` or `2025-12-15`. To handle this, I added validators that normalize input into standard datetime objects so the backend can process queries consistently.

Another issue was response quality. Early on, the AI would return technically correct numbers but not what the user actually wanted. For example, asking *“What was my biggest expense this month?”* would return a total instead of a category or specific insight.

I fixed this by refining how expenses are categorized and tailoring responses to match intent. A better response would be something like:

> “Your highest spending category in December 2025 was Housing at $1,099.00.”

Integrating this AI logic with the FastAPI backend also exposed subtle bugs around joins, filters, and missing records. Fixing these required careful debugging and testing across many different query scenarios.

### What I Learned
Phase 4 pushed me to think beyond basic backend development. I learned:
- How to connect AI-style logic with traditional backend systems
- Why intent interpretation is just as important as correct data
- How to design AI-driven features that are still predictable and debuggable

---

## Outcome
By the end of Phase 4, SpendSense felt like a smart application. Users can interact naturally with their data and get insights that go beyond simple tracking. This phase tied together everything I had learned about backend development, databases, security, and user experience.

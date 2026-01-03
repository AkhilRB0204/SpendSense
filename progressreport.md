SpendSense – Development Progress Log 
Overview

This document tracks my development progress on SpendSense, an AI-powered expense tracking backend. I’m writing it to honestly capture what I built, what broke, what I fixed, and what I learned along the way — not just the final outcome.

At this stage, I’ve completed Phase 1 (Core Backend Prototype) and Phase 2 (Database & Persistence). The backend is functional, persistent, and fully testable through Swagger UI.

Phase 1 – Core Backend Prototype (No Database)
Goal

Get a FastAPI backend up and running with basic expense-tracking functionality before introducing a database.

What I Built

FastAPI server running with Uvicorn

Basic POST and GET endpoints for expenses

In-memory data storage using lists and dictionaries

Swagger UI for manual endpoint testing

Git repository with consistent, incremental commits

Problems I Ran Into

Initial confusion around how FastAPI auto-generates Swagger documentation

Forgetting that in-memory data resets on every server restart

Inconsistent endpoint naming early on

What I Learned

How FastAPI request and response models work

Why persistence matters even for small applications

How valuable Swagger UI is for debugging and validating APIs

Phase 1 gave me confidence that the core idea was viable before adding additional complexity.

Phase 2 – Database & Persistence (Current Phase)
Goal

Make SpendSense persistent, scalable, and closer to a production-ready backend by introducing a relational database.

Tech Stack Added

SQLite (local development)

SQLAlchemy ORM

Pydantic schemas

Structured project layout (models.py, database.py, schemas.py)

Database Design
Tables Implemented

Users

user_id (PK)

name

email

Categories

category_id (PK)

name

Expenses

expense_id (PK)

user_id (FK)

category_id (FK)

amount

description

created_at

All relationships are explicitly defined using SQLAlchemy relationships.

API Endpoints Implemented
Users

POST /users – Create a new user (with duplicate email checks)

Categories

POST /categories – Create a new category (with duplicate checks)

Expenses

POST /expenses – Create an expense tied to a user and category

Validates user and category existence

Utility

GET / – Welcome route for sanity checks

GET /debug – Returns all users, categories, and expenses (temporary debugging tool)

All endpoints are tested through Swagger UI.

Major Problems I Encountered (and Fixed)
1. Attribute Errors Between Models and Schemas

Examples

Using username in endpoints when the model field was actually name

Referencing category_name when the column was simply name

Fix

Standardized naming across:

SQLAlchemy models

Pydantic schemas

FastAPI route logic

This reinforced how fragile backend systems become when naming is inconsistent.

2. Pydantic v2 Warnings (orm_mode)

I repeatedly encountered warnings about orm_mode being renamed to from_attributes.

Fix

Identified this as a Pydantic v2 change

Confirmed it was non-breaking for now and documented it for future cleanup

Lesson: Library warnings are signals, not noise.

3. HTTP Status Code Confusion (400 vs 404 vs 422 vs 500)

I frequently ran into:

422 Unprocessable Entity (schema mismatches)

404 Not Found (invalid user or category IDs)

500 Internal Server Error (logic bugs)

Fix

Traced each error back to:

Request payload structure

Schema definitions

ORM query logic

This significantly improved my debugging discipline and error-handling mindset.

4. Import Errors & Project Structure Issues

Examples

ImportError: cannot import name 'schemas' from 'database'

Circular imports between modules

Fix

Cleaned up the directory structure

Ensured __init__.py files were present

Used explicit imports (e.g., from database.database import engine)

This forced me to actually understand Python’s module resolution instead of guessing.

5. Uvicorn Command Mistakes

Common errors

Typos like mainmenu:a pp

Misplaced --reload flags

Breaking shell commands accidentally

Fix

Standardized on:

python -m uvicorn mainmenu:app --reload


A small issue, but it reinforced the importance of precision.

Phase 3 – Authentication, Multi-user Security & Advanced Expense Summaries

Goal:
Secure the backend, support multiple users, and improve expense summary functionality.

What I Built

1. Authentication & JWT Tokens

Implemented POST /users/login endpoint using OAuth2 password flow.

Generated JWT access tokens with a secret key and expiration.

Added a reusable get_current_user dependency to protect sensitive endpoints.

Authentication logic is centralized in crud.py:

verify_user_credentials checks email and password.

create_access_token generates signed tokens.

2. Password Security

Passwords are hashed securely with bcrypt via passlib.

Plaintext passwords are never stored.

Verification handled in crud.py for reuse across endpoints.

3. Multi-user Support & Security

Users can only access their own expenses and summaries.

Endpoints /users/{user_id}/expenses/summary and /expenses are protected using get_current_user.

CRUD operations enforce user-specific access:

get_user_by_id ensures the user exists.

create_expense links expenses to the correct user and category.

4. Advanced Expense Summaries

Monthly summaries include start and end dates.

Category breakdowns returned as dictionaries, calculated in crud.py.

Responses include all fields—no optional data.

Summary calculations handle:

Total spent

Average per day

Total days in month

Spending per category

5. Simplified mainmenu.py

Centralizing logic in crud.py allowed mainmenu.py endpoints to be cleaner and shorter.

Endpoints now focus only on request handling and response formatting, while crud.py handles the heavy lifting.

Problems I Ran Into

401 Unauthorized errors despite correct credentials.

Schema validation errors (lists vs dictionaries, missing fields).

Confusion around OAuth2PasswordRequestForm and JWT token logic.

Fixes & Improvements

Corrected handling of blank fields in OAuth2PasswordRequestForm.

Fixed JWT generation and decoding logic.

Created reusable get_current_user dependency for authentication.

Resolved schema validation issues in ExpenseSummaryResponse.

Enforced user-specific access in all CRUD functions.

What I Learned

How OAuth2 password flow works in FastAPI.

How to hash passwords securely and verify credentials.

How to protect endpoints using JWT tokens and dependencies.

How to implement multi-user functionality and secure data access.

How to structure response models to avoid optional fields.

How to centralize business logic in crud.py and simplify endpoint code.

Phase 4: AI Integration 

In Phase 4, my goal was to incorporate AI capabilities in SpendSense, allowing users to engage their expenses using natural language queries. This was aimed at creating an intelligent application, as opposed to just being a simple transactional tool.

In my first task, I worked on building a query-to-intent mapping function so that the AI is able to deduce the user’s intent, which could range from total spend for a given month to maximum spend, organizational spend details, and anomaly detection. This is done by defining a structure that defines different intents (IntentType) and associates them with typical patterns in user queries. This includes mapping sentences such as “largest spending” or “biggest expense” to the highest_expense intent.

After the intention has been determined, the related function in the processor behaves in the manner of conducting a database inquiry. These functions are diverse; some may be known as functions related to the determination of the monthly sum, formulation of the categories report, spending prediction indicators, and anomaly reports made on the basis of past data.

An important challenge was handling date parsing for queries. Users might input dates in different formats, like 12/15/2025 versus 2025-12-15. To make the AI robust, I implemented validators that convert user inputs to standardized datetime objects, ensuring the queries could be processed correctly.

Another difficulty was ensuring accurate responses. It wasn’t enough for the AI to return raw numbers- the responses needed context, clarity, and actionable insights. For example, when I first asked about my biggest expense of the month, the AI returned the total which is not what I was looking for. I created a function that would categorize  expenses and return the expense based on what the user would ask. For example, if the user were to ask "What is the bigest expense for the month", the AI would respond: “Your highest spending category in December 2025 was ‘Housing’ at $1,099.00.”

Finally, integrating this with the FastAPI backend revealed some subtle bugs, particularly around database joins and filters for deleted or missing records. Resolving these required careful debugging and testing of multiple query scenarios to ensure the AI consistently returns reliable and meaningful results.

Overall, Phase 4 made SpendSense into a more intelligent tool with improved functionality. Users can now interact, with their financial data, receiving instant insights that go beyond simple tracking such as giving suggestions and finding ways to help the users be more accountable and have better awareness of their expenses. This phase was both technically challenging and highly rewarding, pushing me to solve problems across AI logic, database querying, and user experience.
SpendSense – Development Progress Log (Up to Phase 2)
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

Goal
Secure the backend, support multiple users, and improve expense summary functionality.

What I Built

Authentication & JWT Tokens

POST /users/login endpoint

OAuth2 password flow for login

Access tokens signed with secret key and expiration

Dependency get_current_user to protect endpoints

Password Security

Password hashing with bcrypt via passlib

Passwords never stored in plain text

Multi-user Support & Security

Users can only access their own expenses and summaries

Protected endpoints: /users/{user_id}/expenses/summary, /expenses

Advanced Expense Summaries

Monthly summaries with start and end dates

Category breakdowns returned as dictionaries

No optional fields in responses

Validations for user existence

Problems I Ran Into

401 Unauthorized errors despite correct credentials

Validation errors in schemas (lists vs dicts, missing fields)

Confusion with OAuth2PasswordRequestForm and JWT token logic

Fixes & Improvements

Corrected OAuth2PasswordRequestForm usage and blank fields handling

Fixed JWT generation/decoding logic

Created reusable dependency get_current_user for authentication

Fixed schema validation errors (ExpenseSummaryResponse)

Ensured all endpoints enforce user-specific access

What I Learned

How OAuth2 password flow works in FastAPI

How to hash passwords securely and verify credentials

How to protect endpoints using JWT tokens and dependencies

How to implement multi-user functionality and secure data access

How to structure response models to avoid optional fields

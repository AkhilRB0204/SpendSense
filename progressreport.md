SpendSense 💸
An AI-powered expense tracking backend built with FastAPI. This project started as a simple API prototype and evolved into a secure, multi-user system with natural language expense insights.
This repository documents what I built, what broke, what I fixed, and what I learned—not just the final result.
🚀 Project Overview
SpendSense is a backend-first application designed to help users track expenses and gain insights from their financial data. Over multiple phases, the project grew from in-memory storage to a persistent, authenticated, AI-enhanced system.
Key goals of the project:
Build a real-world backend using modern Python tooling
Practice clean API design and data modeling
Implement authentication and user-level data security
Explore AI-driven, intent-based querying over structured data
🛠 Tech Stack
Backend Framework: FastAPI
Server: Uvicorn
Database: SQLite (local development)
ORM: SQLAlchemy
Validation: Pydantic (v2)
Auth: OAuth2 + JWT
Security: bcrypt / passlib
AI Logic: Intent-based natural language processing
📈 Development Phases
Phase 1 – Core Backend Prototype (No Database)
Goal: Validate the core idea quickly before adding complexity.
What I built:
FastAPI server with basic POST/GET endpoints
In-memory storage using lists and dictionaries
Swagger UI for manual testing
Git-based version control with incremental commits
What I learned:
How FastAPI request/response models shape API behavior
Why persistence matters (in-memory data resets fast)
How useful Swagger UI is for debugging early
Phase 2 – Database & Persistence
Goal: Introduce persistence, structure, and realistic data modeling.
Key additions:
SQLite database with SQLAlchemy ORM
Relational schema for users, categories, and expenses
Structured project layout (models, schemas, database)
Database schema:
Users: id, name, email
Categories: id, name
Expenses: id, user_id, category_id, amount, description, created_at
Lessons learned:
Importance of consistent naming between models and schemas
How ORM relationships enforce data integrity
How to debug common API errors (422, 404, 500)
Python import resolution and avoiding circular dependencies
Phase 3 – Authentication, Multi-user Security & Summaries
Goal: Secure the backend and safely support multiple users.
What I built:
OAuth2 password authentication with JWT tokens
Secure password hashing using bcrypt
Protected routes using FastAPI dependencies
User-scoped CRUD operations
Monthly expense summaries with category breakdowns
Concepts learned:
Authentication vs authorization
Token-based security and expiration
Separation of concerns (routing vs business logic)
Designing APIs that enforce user ownership
Phase 4 – AI Integration & Natural Language Queries
Goal: Enable users to interact with their expense data using natural language.
What I built:
Intent classification system for user queries
Query-to-function routing based on inferred intent
AI-driven insights (largest expense, category breakdowns, trends)
Date parsing and normalization for flexible input formats
Example query:
"What was my biggest expense in December 2025?"
Example response:
"Your highest spending category in December 2025 was Housing at $1,099.00."
Key takeaways:
Intent interpretation matters as much as correct data
AI features must be deterministic and debuggable
Good responses require context, not just numbers
🧠 Concepts Learned Along the Way
API Design & Validation: Enforcing clear data contracts with Pydantic
Persistence & Data Modeling: Designing relational schemas and ORM relationships
Authentication & Authorization: Securing data with JWTs and protected routes
Error Handling: Tracing HTTP errors back to root causes
Project Structure: Keeping business logic separate from routing
AI Integration: Bridging intent-based logic with traditional backends
📌 Why This Project Matters
SpendSense reflects how real backend systems evolve—starting simple, breaking often, and improving through iteration. It helped me develop practical backend instincts around security, scalability, debugging, and user-focused design.
🔮 Future Improvements
Replace SQLite with PostgreSQL
Add recurring expenses and budgeting goals
Improve AI anomaly detection and predictions
Build a frontend client
Add test coverage and CI

# Idempotent Payments System

A robust backend simulator designed to ensure financial transaction integrity. This project implements **API** Idempotency using FastAPI and SQLAlchemy, ensuring that duplicate payment requests (retries) do not result in multiple charges or inconsistent data states.

## Project Overview

In real-world payment processing, network timeouts often lead to clients retrying requests. This simulator provides a production-grade solution to:

### Identify Duplicates

Uses the Idempotency-Key **HTTP** header to uniquely identify and track requests.

### Prevent Double Charges

Leverages database-level unique constraints and atomic transactions to prevent concurrent requests from creating duplicate payments.

### Simulate Real-World Failure

Includes a configurable failure rate to test how the system handles declined transactions and processor timeouts.

### Individual Project Note

This repository represents my individual research and implementation into fault-tolerant distributed systems and financial data integrity.

# Key Features

### Header-Based Validation

Intercepts the Idempotency-Key header. If the key is missing or empty, the system rejects the request with a **400** Bad Request.

### Atomic Race Condition Handling

Instead of simple *check-then-insert* logic (which is prone to race conditions), this system uses a try-except block on IntegrityError. If two threads try to insert the same key simultaneously, the database enforces uniqueness, and the code gracefully recovers the existing record.

### State Persistence

Tracks the lifecycle of a payment from **PENDING** to **SUCCESS** or **FAILED**, ensuring the final status and error messages are permanently associated with the original idempotency key.

### Performance Optimized SQLite

Configured with Write-Ahead Logging (**WAL**) mode (**PRAGMA** journal_mode=**WAL**;) to improve concurrency and performance during high-frequency payment simulations.

# Key Technical Highlights

### Error Handling & Recovery

Implemented automated rollback on IntegrityError. If a duplicate key is detected during the commit phase, the system automatically fetches and returns the existing transaction state.

### Deterministic Simulator

The simulate_processor function mimics a banking gateway with a configurable FAILURE_RATE environment variable, allowing for stress testing of failure scenarios.

### Pydantic Data Validation

Strict schema enforcement for request payloads (amount, currency codes) and structured **JSON** responses using FastAPI's Pydantic integration.

# Tech Stack

### Backend

Language: Python 3.9+

Framework: FastAPI

Validation: Pydantic

### Database

**ORM**: SQLAlchemy

Engine: SQLite (default) / PostgreSQL compatible

Mode: **WAL** (Write-Ahead Logging) for concurrent access

# Logic Flow

Header Check: Extract Idempotency-Key.

Initial Lookup: Check if the key already exists in the payments table.

If found: Return the stored record immediately (Idempotent response).

Pending Record: Create a new payment record with **PENDING** status.

Atomic Commit: Attempt to save to DB.

If an IntegrityError occurs (race condition): Roll back and return the record created by the winning thread.

Process Simulation: Execute simulate_processor() (the *Bank Gateway*).

Final Update: Update the record with **SUCCESS** or **FAILED**, save the result code, and return the final response.

# Project Limitations

### SQLite Lock Contention

While **WAL** mode is enabled, SQLite may still face locking issues under extreme concurrent write stress compared to a distributed system like Postgres + Redis.

### Key Randomness

The system relies on the client providing a unique string (e.g., **UUID**). It does not currently validate the entropy of the provided key.

# Setup and Installation

### Prerequisites

Python 3.9+

Virtual Environment tool (venv)

# Installation

### Clone the repository

git clone https://github.com/Avantiikaa16/idempotent-payment-system.git

cd idempotent-payment-system

### Create and activate virtual environment

python -m venv .venv source .venv/bin/activate  # macOS/Linux # OR .venv\Scripts\activate     # Windows

### Install dependencies

pip install fastapi sqlalchemy uvicorn pydantic

### Configuration

You can customize the simulator using environment variables:

DB_URL: Database connection string (defaults to sqlite:///./payments.db).

FAILURE_RATE: Probability of payment failure (default: 0.30).

# Running the App

### Start the server using Uvicorn

uvicorn main:app --reload

The **API** will be available at [http://**127**.0.0.1:**8000**.](http://**127**.0.0.1:**8000**.) You can view the interactive documentation at /docs.

## Author

Avantika Ramesh Chapegadikar


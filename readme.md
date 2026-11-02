# Project Context: LibraryHub

I am building **LibraryHub**, a simple multi-tenant Library Management SaaS application. Read and understand the following project requirements. Use this as persistent context for future questions, implementation requests, architecture decisions, and code changes.

**Important:** Do not start implementing everything immediately. First understand the requirements and existing project structure. I will ask you to work on specific parts when needed. Do not overengineer anything.

## 1. Technology Stack

- Frontend: React + Vite + Tailwind CSS
- Backend: Python + FastAPI
- Database: PostgreSQL
- Authentication: JWT, Google OAuth, Facebook OAuth
- Payment gateway: Stripe (test mode during development)
- Profile image storage: Storj
- Address autocomplete and maps: Google Maps API
- Background jobs: A simple scheduled job for subscription expiration

Use a straightforward, maintainable architecture. Avoid microservices, unnecessary abstractions, complex design patterns, and additional technologies unless genuinely required.

## 2. Application Architecture

LibraryHub is a multi-tenant application where multiple library owners use the same platform.

There are two main roles:

### Superadmin
The Superadmin manages the entire platform and can:
- View and manage all registered libraries.
- View library owners and their subscription status.
- Search, filter, and paginate library records.
- Manage subscription plans.
- View payment and subscription information.
- Manage library account status.

### Library Owner
A library owner registers, creates a library, and manages its operations.

The owner dashboard has two primary modules:

**Manage Students**
- Add, view, edit, and delete student records.
- Search and list students.
- Maintain relevant student details.

**Manage Books**
- Add, view, edit, and remove book records.
- Maintain book titles, authors, ISBNs, quantities, and availability.
- Assign books to particular students.
- Record issue dates and return deadlines.
- Record book returns and maintain borrowing history.
- Track overdue books.

Keep the core application focused on these two modules. Do not add unnecessary features such as chat, AI assistants, complex analytics, or unrelated modules.

## 3. Multi-Tenant Data Isolation

Use a shared PostgreSQL database with shared tables.

Each library has its own records, and every library-specific entity must be associated with the appropriate library.

The backend must ensure that:
- Library owners can access only their authorized library data.
- One library cannot view or modify another library's students, books, or borrowing records.
- Tenant authorization is enforced server-side.
- The frontend cannot bypass authorization by changing a library ID.
- Superadmin access is separate from normal library-owner access.

Design the data model so one owner can potentially manage multiple libraries, but keep the initial UI and workflows simple.

## 4. Authentication and Account Management

Implement the following requirements:

- Standard signup using email and password.
- Login using email and password.
- Google OAuth login/signup.
- Facebook OAuth login/signup.
- Email verification through a verification link.
- Only verified accounts can access protected dashboards, except for the verification flow itself.
- Safe account linking when a social account uses an email already associated with an existing account. Verify ownership before linking identities.
- JWT-based authentication and role-based authorization.

Never store passwords in plain text. Use secure password hashing, validate tokens properly, and protect secrets through environment variables.

## 5. Library Owner Profile

Library owners should be able to:
- View and update their profile information.
- Upload a profile picture using Storj.
- Enter an address with Google Maps autocomplete.
- View the selected address on a map.
- Download their profile information as a PDF.

Keep this separate from the student records.

## 6. Subscription Plans and Payments

The application supports three plans: Free, Silver, and Gold.

Requirements:
- Display available plans to library owners.
- Allow an owner to select a plan for a particular library.
- Integrate Stripe in test mode.
- Activate paid access only after the backend verifies successful payment.
- Store the selected plan, payment status, activation time, and expiration time.
- Support the specified plan durations of 1 hour, 6 hours, and 12 hours.
- Expire subscriptions automatically.
- Revoke premium access when a subscription expires.
- Display subscription status in the Superadmin panel.

A subscription belongs to a specific library, not globally to every library owned by the same user.

Use Stripe Checkout if appropriate. Verify webhook signatures and handle duplicate payment events safely. Never trust a frontend success redirect as proof of payment.

The exact benefits and resource limits of Free, Silver, and Gold can be configured separately. Do not invent complicated plan features without asking.

## 7. Subscription Expiration

Implement a simple scheduled background job that:
- Finds subscriptions whose expiration time has passed.
- Marks them as expired.
- Ensures premium functionality is no longer available.
- Keeps existing library, student, book, and borrowing data intact.
- Reflects the updated status in the Superadmin panel.

Subscription checks must also happen in the backend API. Do not rely only on a scheduled job or frontend visibility to enforce expiration.

## 8. Superadmin Search and Pagination

The Superadmin must be able to:
- Search libraries and owners.
- Filter by relevant fields and subscription status.
- Navigate through paginated results.
- Retain search, filter, and pagination state after refreshing the page.

Use URL query parameters for persistent listing state where appropriate. Implement pagination on the backend.

## 9. General Development Guidelines

- Keep the frontend and backend as separate applications.
- Use clear FastAPI routers, service functions, database models, and Pydantic schemas without excessive abstraction.
- Use SQLAlchemy and database migrations where appropriate.
- Keep API responses and errors consistent.
- Validate input on the backend.
- Use database transactions for operations that must succeed or fail together, particularly book issuing, returns, and subscription updates.
- Prevent issuing unavailable book copies and maintaining incorrect inventory counts.
- Protect all privileged endpoints with authentication and authorization.
- Never commit API keys, passwords, tokens, or other secrets.
- Use environment variables for configuration.
- Add only the dependencies required for the requested feature.
- Prefer simple, readable, working code over elaborate architecture.

## 10. How to Work With This Context

Treat this document as the project's requirements and reference it whenever I ask about LibraryHub.

When I ask a question, explain the relevant concepts in the context of this project.

When I request an implementation:
1. Inspect the relevant existing code before changing anything.
2. Understand the current structure and reuse it where reasonable.
3. Make only the changes required for the requested feature.
4. Avoid rewriting unrelated code.
5. Explain important files changed, dependencies added, and configuration needed.
6. Mention any assumptions or missing credentials that prevent completion.

Do not generate the entire application at once. Do not implement additional features unless I request them.

**Current objective:** Maintain a clear understanding of LibraryHub's architecture and requirements so I can develop it incrementally, asking for one feature or technical decision at a time.
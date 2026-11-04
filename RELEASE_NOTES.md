# LibraryHub — Release Notes

## v0.1.0 — November 4, 2026

This is the initial development release of LibraryHub, a multi-tenant library management platform with a FastAPI backend and an AI-assisted library workflow.

### Highlights

- **Library and student management:** Backend foundation for library-owner workflows, including student records and library-scoped data.
- **Book catalog and circulation:** Added AI-agent tools to create books, look up books by title or ID, list the catalog, browse by category, retrieve descriptions for recommendations, and issue books to students.
- **AI assistant architecture:** Introduced a LibraryHub root assistant with dedicated student and book agents, routing requests to the relevant specialist.
- **Authentication and account flows:** Backend support for JWT-based access and social sign-in flows, including Google and Facebook OAuth. Magic-link and email-related flows are also present in the backend.
- **Chat improvements:** Chat titles are generated asynchronously in the background, avoiding a hardcoded localhost service loopback in the chat request path.
- **Configuration and deployment:** Added Render deployment configuration, Docker support, runtime/dependency setup, frontend-origin CORS configuration, and environment-driven frontend redirects.
- **Code organization:** Structured the backend into focused areas for authentication, connections, controllers, routers, schemas, services, agents, tools, and skills.

### Technical notes

- **Backend:** Python 3.13, FastAPI, SQLAlchemy, PostgreSQL.
- **AI orchestration:** Google ADK with specialized student and book agents.
- **Configuration:** Runtime configuration is managed through environment variables. Set the required database, authentication, OAuth, email, and AI-provider credentials in the deployment environment. Do not commit secrets.
- **Frontend:** Maintained separately in the `miniproject-frontend-` repository.

### Notes

This is an early development release. Configure the required environment variables and database schema before deployment. Verify OAuth providers, email delivery, payment configuration, and production database permissions in the target environment before enabling those flows for end users.

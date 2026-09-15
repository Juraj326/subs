# Subs

A personal, single-user web app I built to track my subscriptions and recurring expenses.

Subs provides a simple dashboard for tracking active and cancelled subscriptions, monitoring monthly and yearly spending, visualizing expenses by category, and keeping track of upcoming payments through an iCalendar feed.

## Development

### Requirements

- Python 3.14+ and uv
- Node.js and npm
- PostgreSQL

### Setup

Clone the repository and install the dependencies:

```bash
git clone https://github.com/Juraj326/subs.git
cd subs

uv sync
npm install
```

Create your local environment file:

```bash
cp .env.example .env
```

Configure the values in `.env`, including your PostgreSQL connection URL, secret key, passphrase hash, and calendar feed token.

Run the database migrations:

```bash
uv run flask --app app db upgrade
```

Start the frontend development server:

```bash
npm run dev
```

Then start Flask in another terminal:

```bash
uv run flask run --debug
```

## Tests

Run the test suite with:

```bash
uv run pytest
```

Run the linter with:

```bash
uv run ruff check .
```

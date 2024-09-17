# temfetch

Fetches Jira's tempo plugin daily work log to make a summary

Interacts with Jira rest API and Tempo Timesheets rest API. It fetches issue details from Jira and detailed information for a specific worklog ID from Tempo Timesheets.

## Getting Started

These instructions will get you a copy of the project up and running on your local machine for development and testing purposes.

### Prerequisites

- Docker
- Docker Compose

#### Creating Jira app

1) You need to connect to jira developer console: https://developer.atlassian.com/console/myapps and create two apps:
    - temfetch.dev
    - temfetch.prod
2) Give them both permissions:
    - read:jira-work
    - read:jira-user
3) Setup the redirect url for OAuth:
    - for `temfetch.dev`: `https://localhost:your_port/oauth/callback/jira`
    - for `temfetch.prod`: `https://your_host:your_port/oauth/callback/jira`
4) Retrieve the `Client ID` and set it to `JIRA_CLIENT_ID` in `.env.dev` or `.env.prod` for `temfetch.dev` and `temfetch.prod` respectively
5) Same for `Secret` to put in `JIRA_CLIENT_SECRET`

#### Get Tempo USER API Token

1) Go to your tempo and generate an `API Integration`
2) Generate a key, you only need to give it read permission on worklogs
2) Keep this generated key safely as you will need it in the login process

### Environment Variables

The application uses the following environment variables:

- `FLASK_SECRET_KEY`: The secret key for Flask. This is used for session management.
- `TEMPO_USER_TOKEN`: The user token for Tempo Timesheets.
- `JIRA_CLIENT_ID`: The client ID for Jira.
- `JIRA_CLIENT_SECRET`: The client secret for Jira.
- `JIRA_REDIRECT_URI`: The redirect URI for Jira.
- `JIRA_CLOUD_NAME`: The cloud name for Jira.

### Running the Application

#### Development

To run the application in development mode, use the following command:

```bash
docker-compose --env-file .env.dev -f docker-compose-dev.yml up
```

#### Production

To run the application in production mode, use the following command:

```bash
docker-compose -f docker-compose-production.yml up
```

### Application Routes

The application has the following routes:

- `/login/tempo`: The login route for Tempo Timesheets.
- `/oauth/callback/jira`: The OAuth callback route for Jira.
- `/login/jira`: The login route for Jira.
- `/login_failure`: The login failure route.
- `/dailysum`: The daily summary route.
- `/logout`: The logout route.
- `/`: The homepage route.

### License

This project is licensed under the MIT License - see the LICENSE.md file for details.
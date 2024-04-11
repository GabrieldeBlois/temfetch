import os
from datetime import datetime, timedelta

import humanize
import requests
from flask import Flask, redirect, render_template, request, session, url_for
from werkzeug import Response

# Initialize Flask app
app = Flask(__name__)

# Load environment variables
app.secret_key = os.getenv("FLASK_SECRET_KEY", "your_secret_key")
TEMPO_USER_TOKEN = os.getenv("TEMPO_USER_TOKEN")
JIRA_CLIENT_ID = os.getenv("JIRA_CLIENT_ID")
JIRA_CLIENT_SECRET = os.getenv("JIRA_CLIENT_SECRET")
JIRA_REDIRECT_URI = os.getenv("JIRA_REDIRECT_URI")
JIRA_CLOUD_NAME = os.getenv("JIRA_CLOUD_NAME")

# Define routes that do not require authentication
UNAUTHENTICATED_ROUTES = [
    "oauth_callback_jira",
    "login_failure",
    "static",
    "login_jira",
    "login_tempo",
    None,
]


@app.before_request
def ensure_logged_in():
    """Ensure the user is logged in for all routes except those in UNAUTHENTICATED_ROUTES."""
    if request.endpoint in UNAUTHENTICATED_ROUTES:
        return
    if not user_is_authenticated():
        return redirect(url_for("login_tempo"))


def get_auth_token():
    """Get the authentication token from the session if it exists and is not expired."""
    if (
        "token_jira" not in session
        or "cloud_id" not in session
        or "tempo_user_api_key" not in session
        or "expiry_token_jira" not in session
    ):
        return None  # No token found
    try:
        expiry = datetime.fromtimestamp(session["expiry_token_jira"])
        if datetime.utcnow() > expiry:
            return None  # Token is expired
        return session
    except Exception:
        return None  # Invalid token or other error


def fetch_issue_uri_from_worklog(issue_uri: str) -> dict:
    """
    Fetches issue details from Jira.

    :param issue_uri: The URI of the issue to fetch details for.
    :return: A dictionary with issue details, or None if not found/error.
    """
    issue_uri = issue_uri.replace(
        f"https://{JIRA_CLOUD_NAME}.atlassian.net", f"https://api.atlassian.com/ex/jira/{session['cloud_id']}"
    )
    headers = {"Authorization": f"Bearer {session['token_jira']}", "Accept": "application/json"}
    interesting_fields = [
        "timespent",
        "creator",
        "priority",
        "progress",
        "status",
        "summary",
        "issuetype",
    ]
    response = requests.get(
        issue_uri,
        params={
            "fields": ",".join(interesting_fields),
        },
        headers=headers,
        timeout=10,
    )
    return response.json()


@app.route("/login/tempo", methods=["GET", "POST"])
def login_tempo():
    if request.method == "POST":
        api_key = request.form["api_key"]
        # Here, you can use the API key for authentication purposes, store it, etc.
        # Redirect to another page or handle login success
        session["tempo_user_api_key"] = api_key
        return redirect(url_for("login_jira"))
    return render_template("tempologin.html")


@app.route("/oauth/callback/jira")
def oauth_callback_jira():
    """
    Handle OAuth callback from Jira. If there is an error, redirect to the login failure page.
    """
    error = request.args.get("error")
    if error:
        return redirect(url_for("login_failure"))

    code = request.args.get("code")
    token_response = requests.post(
        "https://auth.atlassian.com/oauth/token",
        json={
            "grant_type": "authorization_code",
            "client_id": JIRA_CLIENT_ID,
            "client_secret": JIRA_CLIENT_SECRET,
            "code": code,
            "redirect_uri": JIRA_REDIRECT_URI,
        },
        headers={"Content-Type": "application/json"},
        timeout=10,
    )
    if token_response.status_code != 200:
        return redirect(url_for("login_failure"))

    access_token = token_response.json().get("access_token")
    expires_in = token_response.json().get("expires_in")
    expiry = datetime.utcnow() + timedelta(seconds=expires_in)
    acc_srcs = requests.get(
        "https://api.atlassian.com/oauth/token/accessible-resources",
        headers={"Authorization": f"Bearer {access_token}", "Accept": "application/json"},
        timeout=10,
    )
    if acc_srcs.status_code != 200:
        return redirect(url_for("login_failure"))
    cloud_id = acc_srcs.json()[0].get("id")
    session["token_jira"] = access_token
    session["cloud_id"] = cloud_id
    session["expiry_token_jira"] = expiry.timestamp()
    return redirect(url_for("dailysum"))


@app.route("/login/jira")
def login_jira():
    """
    If the user is not authenticated, redirect to the login process.
    """
    auth_url = (
        "https://auth.atlassian.com/authorize?"
        "audience=api.atlassian.com&"
        f"client_id={JIRA_CLIENT_ID}&"
        "scope=read:jira-work%20read:jira-user%20read:issue-worklog:jira%20read:issue-worklog.property:jira&"
        f"redirect_uri={JIRA_REDIRECT_URI}&"
        "state=awdjkjrjk2134awd&"
        "response_type=code&"
        "prompt=consent"
    )
    return redirect(auth_url)


def user_is_authenticated():
    """Check if the current user has a valid, non-expired authentication token."""
    return get_auth_token() is not None


@app.route("/login_failure")
def login_failure():
    return "Login failed. Please try again.", 400


def fetch_user_worklogs(user_id):
    """
    Fetches detailed information for a specific worklog ID from Tempo Timesheets.

    :param jira_base_url: Base URL of your Jira instance.
    :param worklog_id: The ID of the worklog to fetch details for.
    :param api_token: Your API token for Tempo Timesheets.
    :return: A dictionary with worklog details, or None if not found/error.
    """
    # user_data = get_auth_token()
    # Example usage
    uri = f"https://api.tempo.io/4/worklogs/user/{user_id}"
    headers = {"Authorization": f"Bearer {session['tempo_user_api_key']}"}
    # headers = {"Authorization": f"Bearer {user_data['token']}"}
    today = datetime.now().strftime("%Y-%m-%d")
    response = requests.get(uri, params={"from": today, "to": today}, headers=headers, timeout=10)

    if response.status_code == 200:
        return response.json()
    else:
        print(f"Failed to fetch worklog for user: {user_id}: {response.text}")
        return None


def fetch_myself():
    url = f"https://api.atlassian.com/ex/jira/{session['cloud_id']}/rest/api/3/myself"
    headers = {"Authorization": f"Bearer {session['token_jira']}"}

    response = requests.get(url, headers=headers, timeout=10)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Failed to fetch myself: {response.text}")
        return None


def fetch_open_issues_for_user(account_id):
    # Construct the API request URL
    jql_query = f"assignee = {account_id} AND status in ('Review', 'In Progress')"
    api_url = f"https://api.atlassian.com/ex/jira/{session['cloud_id']}/rest/api/3/search"

    interesting_fields = [
        "assignee",
        "priority",
        "status",
        "summary",
    ]
    query_params = {
        "jql": jql_query,
        "fields": ",".join(interesting_fields),
        "maxResults": "1000",
    }  # Adjust based on your needs
    headers = {"Authorization": f"Bearer {session['token_jira']}", "Accept": "application/json"}
    # Make the request to the Jira API
    response = requests.get(api_url, headers=headers, params=query_params, timeout=10)
    if response.status_code == 200:
        issues = response.json().get("issues", [])
        # Process and return the issues data as needed
        return issues
    else:
        return f"Failed to fetch tasks: {response.text}", response.status_code


@app.route("/dailysum")
def dailysum() -> str:
    myself = fetch_myself()
    account_id = myself.get("accountId")
    open_issues_resp = fetch_open_issues_for_user(account_id)
    # worklogs = fetch_tempo()
    # worklogs = fetch_worklog_by_issue_id("29995")
    worklogs = fetch_user_worklogs(account_id)
    today_worklogs = []
    for wl in worklogs["results"]:
        wl_content = fetch_issue_uri_from_worklog(wl.get("issue").get("self"))
        # today_worklogs.append({**wl_content, "description": wl.get("description"), "timeSpentSeconds": wl.get("timeSpentSeconds")})
        humanized = humanize.naturaldelta(wl["timeSpentSeconds"])
        today_worklogs.append(
            {
                "issue_summary": wl_content["fields"]["summary"],
                "details": wl.get("description"),
                "url": f"https://{JIRA_CLOUD_NAME}.atlassian.net/browse/{wl_content['key']}",
                "id": wl_content["key"],
                "status": wl_content["fields"]["status"]["name"],
                "time_spent": humanized,
            }
        )

    open_issues = []
    for open_issue in open_issues_resp:
        open_issues.append(
            {
                "issue_summary": open_issue["fields"]["summary"],
                "url": f"https://{JIRA_CLOUD_NAME}.atlassian.net/browse/{open_issue['key']}",
                "id": open_issue["key"],
                "status": open_issue["fields"]["status"]["name"],
            }
        )

    return render_template("dailysum.html", today_worklogs=today_worklogs, open_issues=open_issues)


@app.route("/logout")
def logout() -> Response:
    # Clear the authentication cookie by setting its expiration to a past date
    session.clear()
    return redirect(url_for("login_tempo"))


@app.route("/")
def homepage() -> Response:
    """landing point"""
    return redirect(url_for("logout"))
    return redirect(url_for("dailysum"))


if __name__ == "__main__":
    app.run(host="localhost")

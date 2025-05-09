# ai-social-backend

## Overview

This project provides a backend API integrating FastAPI with various social login providers (Google, Facebook, Instagram Basic Display) and AI services (like text summarization using LangChain and OpenAI). It uses MongoDB as the database.

## Features

*   User authentication via Google, Facebook, Instagram.
*   JWT-based session management.
*   AI-powered text summarization endpoint.
*   MongoDB integration using Motor.
*   Configuration management via `.env` file and Pydantic.
*   Asynchronous design using FastAPI and async/await.

## Setup and Installation

1.  **Clone the Repository:**
    ```bash
    git clone <repository-url>
    cd ai-social-backend
    ```

2.  **Create a Virtual Environment:**
    ```bash
    python -m venv venv
    source venv/bin/activate # On Windows use `venv\Scripts\activate`
    ```

3.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure Environment Variables:**
    *   Copy the example environment file:
        ```bash
        cp .env.example .env
        ```
    *   Edit the `.env` file and fill in the required values. See sections below for details on obtaining credentials.

### Database Setup (MongoDB)

*   Ensure you have a MongoDB instance running (local or cloud-based like MongoDB Atlas).
*   Update the `MONGO_URI` in your `.env` file with the connection string for your database. Example: `mongodb://localhost:27017/ai_social_app`

### JWT Configuration

*   Generate strong secret keys for `JWT_SECRET_KEY` and `APP_SECRET_KEY` in your `.env` file. You can use `openssl rand -hex 32` to generate secure keys.
*   Set `ALGORITHM` (default is `HS256`) and `ACCESS_TOKEN_EXPIRE_MINUTES` (default is `30`).

### AI Service Setup (OpenAI)

*   Obtain an API key from [OpenAI](https://platform.openai.com/api-keys).
*   Add the key to your `.env` file as `OPENAI_API_KEY`.

### Social Login Setup (Google)

*   Go to the [Google Cloud Console](https://console.cloud.google.com/).
*   Create a new project or select an existing one.
*   Navigate to "APIs & Services" > "Credentials".
*   Create an "OAuth client ID":
    *   Select "Web application" as the application type.
    *   Add your frontend URI (e.g., `http://localhost:3000`) to "Authorized JavaScript origins".
    *   Add your backend callback URI (e.g., `http://localhost:8000/api/v1/auth/google/callback`) to "Authorized redirect URIs". Make sure this matches `GOOGLE_REDIRECT_URI` in your `.env` file.
*   Copy the generated `Client ID` and `Client Secret`. Add them to your `.env` file as `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET`.
*   Ensure the "Google People API" is enabled for your project under "APIs & Services" > "Library".

### Social Login Setup (Facebook & Instagram)

In addition to Google OAuth, this application supports login via Facebook and Instagram (using the Basic Display API).

1.  **Facebook Developer App:**
    *   Go to [Meta for Developers](https://developers.facebook.com/).
    *   Create a new App or use an existing one. Select "Consumer" or "Business" type as appropriate.
    *   Under "App settings" > "Basic", find your `App ID` and `App Secret`. Add these to your `.env` file as `FACEBOOK_CLIENT_ID` and `FACEBOOK_CLIENT_SECRET`.
    *   Navigate to "Products" (+) and add the "Facebook Login" product.
    *   Under "Facebook Login" > "Settings":
        *   Enable "Web OAuth Login".
        *   Add your callback URI (e.g., `http://localhost:8000/api/v1/auth/facebook/callback`) to the "Valid OAuth Redirect URIs" list. Make sure it matches `FACEBOOK_REDIRECT_URI` in your `.env` file.
        *   Ensure "Client OAuth Login" and "Web OAuth Login" are enabled.
    *   Your app might need to undergo App Review by Facebook to allow logins from non-developer/tester accounts, especially if requesting permissions beyond basic profile/email.

2.  **Instagram Basic Display API App:**
    *   Go to [Meta for Developers](https://developers.facebook.com/) (Instagram Basic Display is managed through Facebook apps).
    *   Use the *same Facebook App* you created/used for Facebook Login, or create a new one if preferred.
    *   Under "Products" (+), add the "Instagram Basic Display" product.
    *   Configure the Instagram Basic Display product:
        *   Provide a "Privacy Policy URL" and "User Data Deletion" callback/URL (required by Meta).
        *   Under "Client OAuth Settings", add your Instagram callback URI (e.g., `http://localhost:8000/api/v1/auth/instagram/callback`) to the "Valid OAuth Redirect URIs" list. It must match `INSTAGRAM_REDIRECT_URI` in your `.env` file.
        *   Note your `Instagram App ID` and `Instagram App Secret` shown here. Add them to your `.env` file as `INSTAGRAM_CLIENT_ID` and `INSTAGRAM_CLIENT_SECRET`.
    *   **Important:** Instagram Basic Display API requires explicit user authorization for scopes (`user_profile`, `user_media`). It provides limited information (ID, username) and does not provide email addresses. The app requires App Review for public use. You may need to add test users within the Facebook App dashboard for testing during development.

3.  **Update `.env` File:**
    *   Ensure you have copied the `FACEBOOK_CLIENT_ID`, `FACEBOOK_CLIENT_SECRET`, `FACEBOOK_REDIRECT_URI`, `INSTAGRAM_CLIENT_ID`, `INSTAGRAM_CLIENT_SECRET`, and `INSTAGRAM_REDIRECT_URI` variables into your active `.env` file and filled them with the correct values obtained from the Meta developer dashboard.


## Running the Application

1.  **Start the Server:**
    ```bash
    uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    ```
    Alternatively, if you have the `if __name__ == "__main__":` block in `app/main.py`:
    ```bash
    python app/main.py
    ```

2.  **Access the API:**
    *   The API will be available at `http://localhost:8000`.
    *   Interactive documentation (Swagger UI) is usually at `http://localhost:8000/docs`.
    *   Alternative documentation (ReDoc) is usually at `http://localhost:8000/redoc`.

## API Endpoints

*   `GET /`: Root endpoint for basic health check.
*   `GET /docs`: Swagger UI documentation.
*   `GET /redoc`: ReDoc documentation.

### Authentication (`/api/v1/auth`)

*   `GET /api/v1/auth/login/google`: Initiates the Google OAuth login flow.
*   `GET /api/v1/auth/google/callback`: Handles the callback from Google.
*   `GET /api/v1/auth/login/facebook`: Initiates the Facebook OAuth login flow.
*   `GET /api/v1/auth/facebook/callback`: Handles the callback from Facebook.
*   `GET /api/v1/auth/login/instagram`: Initiates the Instagram OAuth login flow.
*   `GET /api/v1/auth/instagram/callback`: Handles the callback from Instagram.
*   **(Protected)** `GET /api/v1/auth/users/me`: (Example - Requires Authentication) Gets the current logged-in user's details. _(Note: Requires implementing `get_current_user` dependency)_

### AI Services (`/api/v1/ai`)

*   **(Protected)** `POST /api/v1/ai/summarize`: Summarizes the provided text. Requires authentication.
    *   **Request Body:** `{ "text": "Your long text here..." }`
    *   **Response:** `{ "summary": "The summarized text." }`

## Running Tests

*   Ensure `pytest` and `httpx` are installed (they are in `requirements.txt`).
*   Run tests from the project root directory:
    ```bash
    pytest
    ```

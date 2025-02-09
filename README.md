# WCA Registration Crawler

This script automates the process of registering for WCA (World Cube Association) competitions on the Cubing-TW website. It automatically fills in your WCA ID, birthday, email, and phone number (optional), selects all events, and clicks the "Preview" and "Send" buttons.  It also supports sending a notification to a Discord channel upon completion.  This project also provides GitHub Actions workflows to run the script in the cloud.

**Disclaimer:** This script is intended to save time and effort during WCA competition registration. Use responsibly and ensure you review all information before submitting the final registration. The author is not responsible for any errors or consequences resulting from the use of this script.

## Features

*   **Automated Information Filling:** Automatically enters WCA ID, birthday, email, and phone number.
*   **Event Selection:** Automatically selects all available event options.
*   **Button Clicking:** Automatically clicks the "Preview" and "Send" buttons.
*   **Error Handling:** Includes basic error handling and prompts for manual intervention if necessary.
*   **Environment Variable Support:** Uses environment variables for sensitive information (WCA ID, birthday, contact info, Discord tokens) for better security.
*   **Informative Output:** Provides colored output to indicate the script's progress and potential issues.
*   **Discord Notification:** Sends a notification to a specified Discord channel upon successful completion of the registration.
*   **GitHub Actions Workflows:** Includes workflows to easily run the script in a GitHub Actions environment.

## Requirements

*   Python 3.6+
*   Chrome browser (if running locally with `NO_UI=false`)
*   ChromeDriver (matching your Chrome browser version - if running locally with `NO_UI=false`). The script uses `webdriver-manager` to handle this automatically. However, if you encounter issues, ensure you have the correct ChromeDriver installed.  This is not necessary when running via GitHub Actions.
*   Required Python libraries:
    ```
    selenium
    webdriver-manager
    python-dotenv
    discord
    ```

## Installation

1.  **Clone the repository:**
    ```bash
    git clone git@github.com:wulukewu/wca-registration-crawler.git
    cd wca-registration-crawler
    ```

2.  **Create a virtual environment (recommended):**
    ```bash
    python3 -m venv venv
    source venv/bin/activate  # On Linux/macOS
    venv\Scripts\activate.bat  # On Windows
    ```

3.  **Install the required libraries:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Set up environment variables (recommended):**

    This is the preferred and most secure way to configure the script and avoid hardcoding your personal information. Create a `.env` file in the project root directory with the following content (replace with your actual values):

    ```properties
    EVENT_URL=the_competition_registration_url
    WCA_ID=your_wca_id
    BIRTHDAY_YEAR=your_birth_year
    BIRTHDAY_MONTH=your_birth_month
    BIRTHDAY_DAY=your_birth_day
    EMAIL=your_email@example.com
    PHONE=your_phone_number (optional)
    DISCORD_TOKEN=your_discord_bot_token (optional, for Discord notifications)
    DISCORD_GUILD_ID=your_discord_guild_id (optional, for Discord notifications)
    DISCORD_CHANNEL_ID=your_discord_channel_id (optional, for Discord notifications)
    NO_UI=true # Set to false if you want to see the browser window (not recommended for automated runs)
    ```

    **Important:** Storing your credentials in environment variables is generally more secure than hardcoding them in the script.  If you don't set these environment variables and `NO_UI` is set to `false`, the script will prompt you for the information when it runs. Setting `NO_UI` to `true` without setting the required environment variables will cause the script to fail.

## Usage

1.  **Configure the script (if not using environment variables):**

    If you choose not to use environment variables and `NO_UI` is set to `false`, the script will prompt you to enter your WCA ID, birthday, email, and phone number when you run it.

2.  **Run the script locally:**

    ```bash
    python main.py
    ```

3.  **Monitor the output:**

    The script will print information about its progress to the console.  It will also pause and prompt you for input if it encounters any issues (e.g., if it fails to find an element on the page) when `NO_UI` is set to `false`.

4.  **Manual Intervention:**

    The script is designed to automate the process as much as possible, but manual intervention may be required in some cases. Pay attention to the console output and follow the instructions provided if the script encounters an error or needs your input.  Specifically, **always review the information on the "Preview" page before submitting the final registration.** This applies only when running locally with `NO_UI` set to `false`.

## Running with GitHub Actions

This repository includes GitHub Actions workflows to automate the registration process.  You will need to configure secrets in your repository settings to provide the necessary information.

1.  **Set up repository secrets:**

    Go to your repository on GitHub, then navigate to "Settings" -> "Security" -> "Secrets and variables" -> "Actions". Add the following secrets:

    *   `EVENT_URL`: The URL of the WCA competition registration page.
    *   `WCA_ID`: Your WCA ID.
    *   `BIRTHDAY_YEAR`: Your birth year (e.g., 2000).
    *   `BIRTHDAY_MONTH`: Your birth month (e.g., 1).
    *   `BIRTHDAY_DAY`: Your birth day (e.g., 1).
    *   `EMAIL`: Your email address.
    *   `PHONE` (Optional): Your phone number.
    *   `DISCORD_TOKEN` (Optional): Your Discord bot token. Required for Discord notifications.
    *   `DISCORD_GUILD_ID` (Optional): Your Discord guild ID. Required for Discord notifications.
    *   `DISCORD_CHANNEL_ID` (Optional): Your Discord channel ID. Required for Discord notifications.
    *   `PAT`: Personal Access Token with `write:packages` and `repo` access. Required for pulling docker image.

2.  **Trigger the workflow:**

    Go to the "Actions" tab in your repository and select the desired workflow (`WCA Runner` or `WCA Runner Multiple`). Click the "Run workflow" button.

    *   `WCA Runner`: Runs a single instance of the registration script.
    *   `WCA Runner Multiple`: Runs multiple instances of the registration script in parallel.  This is useful for attempting to register multiple people at the same time, however, may violate Cubing-TW's terms of service.  Use with caution.

## Troubleshooting

*   **ChromeDriver issues (Local Runs with `NO_UI=false`):**
    *   Ensure that your ChromeDriver version is compatible with your Chrome browser version. `webdriver-manager` should handle this automatically.
    *   If you still have problems, try manually downloading the correct ChromeDriver from the [ChromeDriver website](https://chromedriver.chromium.org/downloads) and placing it in a directory accessible to the script.  Make sure the driver is added to your PATH environment variable.
*   **Element Not Found Issues:**
    *   The website structure may have changed. If the script fails to find certain elements (buttons, input fields, etc.), the website's HTML structure might be different. In that case, you might need to update the selectors (e.g., IDs, CSS classes) used by the script to locate these elements. Inspect the page in your browser's developer tools and update the `main.py` accordingly.
*   **Registration Link Not Found:**
    * The script relies on finding a register link in the main page of Cubing-TW. If the link is unavailable, the script will continue to refresh the page until it finds it.
*   **Environment Variables Not Set:**
    * When running the script with `NO_UI=true`, ensure all required environment variables (`EVENT_URL`, `WCA_ID`, `BIRTHDAY_YEAR`, `BIRTHDAY_MONTH`, `BIRTHDAY_DAY`, `EMAIL`) are set. The script will exit if they are missing.
*   **Discord Notification Issues:**
    * Ensure that the `DISCORD_TOKEN`, `DISCORD_GUILD_ID`, and `DISCORD_CHANNEL_ID` environment variables are set correctly. Also, ensure your Discord bot has the necessary permissions to send messages to the specified channel.

## Contributing

Contributions are welcome! If you find any bugs or have any suggestions for improvement, please open an issue or submit a pull request.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
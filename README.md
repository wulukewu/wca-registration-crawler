# WCA Registration Crawler

This script automates the process of registering for WCA (World Cube Association) competitions on the Cubing-TW website. It automatically fills in your WCA ID, birthday, email, and phone number (optional), selects all events, and clicks the "Preview" and "Send" buttons.

**Disclaimer:** This script is intended to save time and effort during WCA competition registration. Use responsibly and ensure you review all information before submitting the final registration. The author is not responsible for any errors or consequences resulting from the use of this script.

## Features

*   **Automated Information Filling:** Automatically enters WCA ID, birthday, email, and phone number.
*   **Event Selection:** Automatically selects all available event options.
*   **Button Clicking:** Automatically clicks the "Preview" and "Send" buttons.
*   **Error Handling:** Includes basic error handling and prompts for manual intervention if necessary.
*   **Environment Variable Support:**  Uses environment variables for sensitive information (WCA ID, birthday, contact info) for better security.
*   **Informative Output:** Provides colored output to indicate the script's progress and potential issues.

## Requirements

*   Python 3.6+
*   Chrome browser
*   ChromeDriver (matching your Chrome browser version) - The script uses `webdriver-manager` to handle this automatically. However, if you encounter issues, ensure you have the correct ChromeDriver installed.
*   Required Python libraries:

    ```
    selenium
    webdriver-manager
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
    Create a file named `requirements.txt` with the following content:
    ```
    selenium
    webdriver-manager
    ```

4.  **Set up environment variables (recommended):**

    This is the preferred way to configure the script and avoid hardcoding your personal information. Create a `.env` file in the project root directory with the following content (replace with your actual values):

    ```properties
    WCA_ID=your_wca_id
    BIRTHDAY_YEAR=your_birth_year
    BIRTHDAY_MONTH=your_birth_month
    BIRTHDAY_DAY=your_birth_day
    EMAIL=your_email@example.com
    PHONE=your_phone_number (optional)
    ```

    **Important:** Storing your credentials in environment variables is generally more secure than hardcoding them in the script.  If you don't set these environment variables, the script will prompt you for the information when it runs.

## Usage

1.  **Configure the script (if not using environment variables):**

    If you choose not to use environment variables, the script will prompt you to enter your WCA ID, birthday, email, and phone number when you run it.

2.  **Run the script:**

    ```bash
    python main.py
    ```

3.  **Monitor the output:**

    The script will print information about its progress to the console.  It will also pause and prompt you for input if it encounters any issues (e.g., if it fails to find an element on the page).

4.  **Manual Intervention:**

    The script is designed to automate the process as much as possible, but manual intervention may be required in some cases. Pay attention to the console output and follow the instructions provided if the script encounters an error or needs your input.  Specifically, **always review the information on the "Preview" page before submitting the final registration.**

## Troubleshooting

*   **ChromeDriver issues:**

    *   Ensure that your ChromeDriver version is compatible with your Chrome browser version. `webdriver-manager` should handle this automatically.
    *   If you still have problems, try manually downloading the correct ChromeDriver from the [ChromeDriver website](https://chromedriver.chromium.org/downloads) and placing it in a directory accessible to the script.  Make sure the driver is added to your PATH environment variable.

*   **Element Not Found Issues:**

    *   The website structure may have changed. If the script fails to find certain elements (buttons, input fields, etc.), the website's HTML structure might be different. In that case, you might need to update the selectors (e.g., IDs, CSS classes) used by the script to locate these elements. Inspect the page in your browser's developer tools and update the `main.py` accordingly.

*   **Registration Link Not Found:**
    * The script relies on finding a register link in the main page of Cubing-TW. If the link is unavailable, the script will continue to refresh the page until it finds it.

## Contributing

Contributions are welcome! If you find any bugs or have any suggestions for improvement, please open an issue or submit a pull request.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
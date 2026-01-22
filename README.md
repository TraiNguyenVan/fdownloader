# Facebook Batch Image Downloader

A Dockerized tool to bulk download high-resolution images from Facebook posts (Theater Mode) using Playwright and a simple Web GUI.

## Features

-   **bulk Download**: Scrapes all images from a Facebook post (album/gallery) in high quality.
-   **Web GUI**: Clean, modern interface to input URLs and download results as a ZIP file.
-   **Public Access**: Integrated Ngrok tunnel to share the tool with friends securely.
-   **Robust Navigation**: Handles "Theater Mode" navigation automatically, with fallback strategies for different UI variations.
-   **Cycle Detection**: Automatically stops when the gallery loops back to the first image.

## Prerequisites

-   [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running.
-   A Facebook account (for cookies to access content).

## Setup

### 1. Export Facebook Cookies
Since the tool runs in a headless browser (Docker), it needs your session cookies to see the posts.

1.  Install a browser extension like **"Get cookies.txt LOCALLY"** (Chrome/Firefox).
2.  Login to Facebook.
3.  Open the extension and export cookies for `facebook.com`.
4.  Save the file as `cookies.txt` in this project folder.
5.  Run the helper script (optional, usually handled automatically if configured, but for the first time you might need to convert netscape format to json):
    *(Note: The tool expects `facebook_cookies.json`. You can verify if `cookies_helper.py` or the app handles the conversion, or simply map the txt file if the code supports it. Based on current code, it loads from json. You might need to run a conversion step if you only have txt.)*

    **Recommended**: Ensure you have a valid `facebook_cookies.json` in the root directory. If you only have `cookies.txt`, you can run:
    ```bash
    # (Inside the container or locally if python is installed)
    python cookies_helper.py
    ```

### 2. Start the Application

Run the following command to build and start the services:

```bash
docker-compose up -d --build
```

## Usage

### Method 1: Web GUI (Local)
1.  Open your browser to: [http://localhost:5000](http://localhost:5000)
2.  Paste a **Facebook Theater Link** (e.g., `https://www.facebook.com/photo/?fbid=...`).
3.  Click **Download**.
4.  Wait for the process to complete (can take a minute depending on the number of images).
5.  Click **Download ZIP**.

### Method 2: Public Access (Ngrok)
If you want to access this from your phone or share it with a friend:
1.  Go to [http://localhost:4040](http://localhost:4040) (Ngrok Dashboard).
2.  Copy the URL ending in `.ngrok-free.app`.
3.  Open that URL on any device to access the Web GUI.

### Method 3: Command Line
You can also run the script directly for a single link without the GUI:

```bash
docker-compose run --rm fdownloader "https://www.facebook.com/photo/?fbid=YOUR_ID"
```
Images will be saved to the `downloads/` folder.

## Troubleshooting

-   **Login Wall**: If the logs show "Login Required", your cookies are likely expired. Re-export `cookies.txt` and restart the container.
-   **No Images Found**: Ensure the link is valid and publicly visible (or visible to the account the cookies belong to). Use the direct `/photo/?fbid=...` link format for best results.
-   **Stuck?**: The container runs in detached mode. View logs with:
    ```bash
    docker-compose logs -f fdownloader
    ```

## License
MIT

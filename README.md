# ScrapeBeast
An automated news scraper built for archival and local reading. Originally 
meant to rip articles from behind a paywall, but as luck would have it
they just made it free to view anyway. 

## Setup
This project uses a Python virtual environment to manage dependencies.

1. **Create and Activate Environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Use activate.fish if on Fish shell

2. ** Install Dependencies **
   ```bash
   pip install -r requirements.txt

3. **Prerequisites:

    Firefox: Required for Selenium (GeckoDriver).

    LXML Headers: 
    Arch/Arch-based: sudo pacman -S libxml2 libxslt

    Debian/Ubuntu: sudo apt-get install libxml2-dev libxslt1-dev python3-dev
                   
                   pip install lxml



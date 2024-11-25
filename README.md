# QR Code Generator

This is a simple web application that generates QR codes from user input.

## Features

- Generate QR codes from text or URLs
- Web interface for easy interaction
- API endpoint for programmatic access

## Installation

1. Clone this repository
2. Install the required packages:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

1. Run the application:
   ```bash
   python3 app.py
   ```
2. Open a web browser and navigate to `http://localhost:5000`
3. Enter the text or URL you want to encode in the QR code and click "Generate QR Code"

## API Documentation

The API documentation is available at `http://localhost:5000/apidocs/` when the application is running.

## Dependencies

- Flask
- flasgger
- qrcode
- Pillow

For specific versions, see `requirements.txt`.

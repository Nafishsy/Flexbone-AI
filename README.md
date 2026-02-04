# OCR Image Text Extraction API

A serverless OCR API built with FastAPI and deployed on Google Cloud Run. Extracts text from images using the Google Cloud Vision API.

## Endpoints

### `GET /`
Health check endpoint.

### `POST /extract-text`
Extract text from a single image.

**Request:**
- Content-Type: `multipart/form-data`
- Body: `image` - Image file (JPG, PNG, or GIF, max 10MB)
- Query param: `include_metadata` (optional, boolean) - Include image metadata in response

**Success Response (200):**
```json
{
  "success": true,
  "text": "extracted text content",
  "confidence": 0.98,
  "processing_time_ms": 1234
}
```

**With metadata:**
```json
{
  "success": true,
  "text": "extracted text content",
  "confidence": 0.98,
  "processing_time_ms": 1234,
  "metadata": {
    "format": "JPEG",
    "mode": "RGB",
    "width": 1920,
    "height": 1080,
    "exif": {
      "Make": "Canon",
      "Model": "EOS 5D"
    }
  }
}
```

**Cached response** (when identical image is processed again):
```json
{
  "success": true,
  "text": "extracted text content",
  "confidence": 0.98,
  "processing_time_ms": 5,
  "cached": true
}
```

**No text found:**
```json
{
  "success": true,
  "text": "",
  "confidence": 0.0,
  "processing_time_ms": 800,
  "message": "No text found in image"
}
```

### `POST /extract-text/batch`
Process multiple images in a single request (max 10 images).

**Request:**
- Content-Type: `multipart/form-data`
- Body: `images` - Multiple image files
- Query param: `include_metadata` (optional, boolean)

**Response:**
```json
{
  "success": true,
  "total": 3,
  "processed": 2,
  "results": [
    {
      "index": 0,
      "filename": "doc1.jpg",
      "success": true,
      "text": "extracted text",
      "confidence": 0.95
    },
    {
      "index": 1,
      "filename": "doc2.png",
      "success": true,
      "text": "more text",
      "confidence": 0.92
    },
    {
      "index": 2,
      "filename": "invalid.txt",
      "success": false,
      "error": "Invalid file type. Supported formats: JPG, PNG, GIF"
    }
  ],
  "processing_time_ms": 3500
}
```

### Error Responses

| Status | Description |
|--------|-------------|
| 400 | Empty file, corrupted image, or batch size exceeded |
| 413 | File too large (max 10MB) |
| 415 | Unsupported file type or invalid image signature |
| 429 | Rate limit exceeded |
| 500 | OCR processing failed |

```json
{
  "success": false,
  "error": "Error description",
  "status_code": 400
}
```

## Features

- **Multi-format support**: JPG, PNG, GIF
- **Confidence scores**: Block-level confidence from Vision API
- **Text preprocessing**: Normalizes whitespace and line breaks
- **Rate limiting**: 30 requests/min for single, 10 requests/min for batch
- **Caching**: SHA-256 based caching for identical images
- **Batch processing**: Process up to 10 images per request
- **Image metadata**: Optional EXIF and dimension extraction

## Example Usage

**Single image:**
```bash
curl -X POST -F "image=@document.jpg" https://your-service.run.app/extract-text
```

**With metadata:**
```bash
curl -X POST -F "image=@photo.jpg" "https://your-service.run.app/extract-text?include_metadata=true"
```

**Batch processing:**
```bash
curl -X POST \
  -F "images=@doc1.jpg" \
  -F "images=@doc2.png" \
  -F "images=@doc3.gif" \
  https://your-service.run.app/extract-text/batch
```

**Python:**
```python
import requests

# Single image
with open("document.jpg", "rb") as f:
    response = requests.post(
        "https://your-service.run.app/extract-text",
        files={"image": f}
    )
print(response.json())

# Batch processing
files = [
    ("images", open("doc1.jpg", "rb")),
    ("images", open("doc2.png", "rb"))
]
response = requests.post(
    "https://your-service.run.app/extract-text/batch",
    files=files
)
print(response.json())
```

## Implementation

Uses **Google Cloud Vision API** (`document_text_detection`) for OCR. The API validates uploaded files before processing and calculates confidence scores from block-level annotations.

**Text preprocessing** normalizes whitespace and line breaks for cleaner output.

**Caching** uses SHA-256 hashing of image content to avoid redundant API calls for identical images.

**Rate limiting** prevents abuse (30 req/min single, 10 req/min batch).

## Local Development

### Prerequisites
- Python 3.11+
- Google Cloud SDK
- Vision API access

### Setup

1. Clone the repository and navigate to it.

2. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up credentials:
```bash
gcloud auth application-default login
```

5. Run locally:
```bash
python main.py
```

The API will be available at `http://localhost:8080`

## Deployment

### Deploy from source
```bash
gcloud services enable vision.googleapis.com run.googleapis.com artifactregistry.googleapis.com cloudbuild.googleapis.com

gcloud run deploy ocr-api \
  --source . \
  --region us-central1 \
  --allow-unauthenticated
```

## Project Structure

```
ocr-api/
├── main.py              # FastAPI application
├── requirements.txt     # Python dependencies
├── Dockerfile           # Container configuration
├── README.md
└── test_images/         # Sample images for testing
```

## Testing

```bash
# Health check
curl http://localhost:8080/

# Single image OCR
curl -X POST -F "image=@test_images/sample.jpg" http://localhost:8080/extract-text

# With metadata
curl -X POST -F "image=@test_images/sample.jpg" "http://localhost:8080/extract-text?include_metadata=true"
```

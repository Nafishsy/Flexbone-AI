# Flexbone AI - OCR API Challenge Deliverables

## 1. Public Cloud Run URL

```
https://[YOUR-CLOUD-RUN-URL]
```

### Endpoints
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Health check |
| `/docs` | GET | Swagger UI (Interactive API Testing) |
| `/extract-text` | POST | Single image OCR |
| `/extract-text/batch` | POST | Batch OCR (max 10 images) |

---

## 2. API Documentation

### Single Image OCR

**Endpoint:** `POST /extract-text`

**Request:**
```bash
curl -X POST -F "image=@document.jpg" https://[URL]/extract-text
```

**With Metadata:**
```bash
curl -X POST -F "image=@document.jpg" "https://[URL]/extract-text?include_metadata=true"
```

**Response:**
```json
{
  "success": true,
  "text": "Extracted text content...",
  "confidence": 0.9823,
  "processing_time_ms": 1456
}
```

### Batch Processing

**Endpoint:** `POST /extract-text/batch`

**Request:**
```bash
curl -X POST \
  -F "images=@doc1.jpg" \
  -F "images=@doc2.png" \
  https://[URL]/extract-text/batch
```

**Response:**
```json
{
  "success": true,
  "total": 2,
  "processed": 2,
  "results": [
    {"index": 0, "filename": "doc1.jpg", "success": true, "text": "...", "confidence": 0.95},
    {"index": 1, "filename": "doc2.png", "success": true, "text": "...", "confidence": 0.92}
  ],
  "processing_time_ms": 2800
}
```

### Error Codes

| Code | Description |
|------|-------------|
| 200 | Success |
| 400 | Empty file, corrupted image, batch exceeded |
| 413 | File too large (max 10MB) |
| 415 | Unsupported file type |
| 429 | Rate limit exceeded |
| 500 | OCR processing failed |

---

## 3. Implementation Details

### OCR Service
- **Google Cloud Vision API** using `document_text_detection`
- Provides block-level confidence scores
- Handles various image qualities and text orientations

### File Upload & Validation
1. Content-Type check (image/jpeg, image/png, image/gif)
2. File extension check (.jpg, .jpeg, .png, .gif)
3. Magic bytes validation (actual file content)
4. PIL integrity check (not corrupted)
5. Size limit: 10MB maximum

### Deployment Strategy
- Containerized with Docker (python:3.11-slim)
- Deployed to Google Cloud Run
- Serverless auto-scaling
- Public unauthenticated access

---

## 4. Bonus Features Implemented

| Feature | Status | Implementation |
|---------|--------|----------------|
| Multi-format (PNG, GIF) | ✅ | `app/config.py` - SUPPORTED_FORMATS |
| Confidence scores | ✅ | `app/services/ocr.py` - block-level average |
| Text preprocessing | ✅ | `app/utils/image.py` - whitespace normalization |
| Rate limiting | ✅ | `app/routers/ocr.py` - 30/min, 10/min batch |
| Caching | ✅ | `app/services/cache.py` - SHA-256 hash |
| Batch processing | ✅ | `/extract-text/batch` endpoint |
| Image metadata | ✅ | `app/utils/image.py` - EXIF extraction |

---

## 5. Project Structure

```
ocr-api/
├── main.py                 # Entry point
├── Dockerfile              # Container configuration
├── requirements.txt        # Python dependencies
├── README.md               # API documentation
├── DELIVERABLES.md         # This file
├── test_images/
│   └── sample.jpg          # Test image
└── app/
    ├── main.py             # FastAPI initialization
    ├── config.py           # Constants
    ├── dependencies.py     # Shared limiter
    ├── models.py           # Pydantic models
    ├── routers/
    │   └── ocr.py          # API endpoints
    ├── services/
    │   ├── ocr.py          # Vision API logic
    │   └── cache.py        # Caching service
    └── utils/
        ├── validation.py   # File validation
        └── image.py        # Image processing
```

---

## 6. Testing Instructions

### Using Swagger UI (Recommended)
1. Open `https://[URL]/docs` in browser
2. Click on `POST /extract-text`
3. Click "Try it out"
4. Upload an image file
5. Click "Execute"

### Using curl
```bash
# Health check
curl https://[URL]/

# Single image
curl -X POST -F "image=@test.jpg" https://[URL]/extract-text

# With metadata
curl -X POST -F "image=@test.jpg" "https://[URL]/extract-text?include_metadata=true"

# Batch
curl -X POST -F "images=@img1.jpg" -F "images=@img2.jpg" https://[URL]/extract-text/batch
```

### Using Python
```python
import requests

# Single image
with open("document.jpg", "rb") as f:
    response = requests.post(
        "https://[URL]/extract-text",
        files={"image": f}
    )
print(response.json())
```

---

## 7. Tech Stack

- **Framework:** FastAPI (Python 3.11)
- **OCR:** Google Cloud Vision API
- **Deployment:** Google Cloud Run
- **Container:** Docker
- **Rate Limiting:** slowapi
- **Image Processing:** Pillow

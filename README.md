# Social Media Image Captioning API

Welcome to the Social Media Image Captioning API repository. This API, built with FastAPI and Azure Cognitive Services, generates creative captions for images based on user prompts.

## Features

- **Image Analysis:** Utilizes Azure Cognitive Services for image analysis.
- **Caption Generation:** Employs OpenAI for generating creative captions.
- **Cloudinary Integration:** Manages image storage using Cloudinary.

## Getting Started

### Usage
The api requires two parameters
- image: The image in JPG, PNG, or JPEG
- prompt: An additional prompt describing the image (optional)

**API endpoint: https://generative-image-caption.vercel.app/analyze**


### Prerequisites

- Python 3.7+
- Azure Cognitive Services API Key
- OpenAI API Key
- Cloudinary Credentials

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/EddyEjembi/GenerativeImageCaption.git
2. Install Dependencies
   ```
   pip install -r requirements.txt
   ```
3. Run program
   ```
   flask run
   ```

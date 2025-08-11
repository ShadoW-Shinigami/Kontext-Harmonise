# 🎨 Kontext-Harmonise

A modern Gradio web application that uses Kontext LoRA to harmonize images with consistent colors, lighting, and shadows.

## ✨ Features

- **Single Image Processing**: Upload and harmonize individual images
- **Batch Processing**: Process multiple images by uploading a ZIP file
- **Gallery View**: Browse all processed images with metadata
- **Configurable Parameters**: Easily modify processing settings in `config.py`
- **Modern UI**: Clean and intuitive Gradio interface

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Set Up Environment

1. Copy the environment template:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` and configure your settings:
   ```env
   # Required: FAL.AI API Key
   FAL_KEY=your_fal_api_key_here
   
   # Optional: Server Configuration
   GRADIO_SERVER_NAME=0.0.0.0
   GRADIO_SERVER_PORT=7860
   GRADIO_SHARE=false
   GRADIO_DEBUG=false
   
   # Optional: Authentication
   # GRADIO_AUTH_USERNAME=admin
   # GRADIO_AUTH_PASSWORD=your_secure_password
   ```

   Get your API key from: https://fal.ai/dashboard/keys

### 3. Run the Application

```bash
python main.py
```

The application will be available at the configured address (default: http://localhost:7860)

## 📁 Project Structure

```
Kontext-Harmonise/
├── main.py              # Main application file
├── config.py            # Configuration parameters
├── requirements.txt     # Python dependencies
├── .env.example         # Environment variables template
├── .env                 # Your environment variables (create this)
├── output/              # Generated images (auto-created)
│   ├── 00001.png
│   ├── 00002.png
│   └── metadata.json    # Image metadata
└── README.md           # This file
```

## 🔧 Configuration

Edit `config.py` to customize the image processing:

### API Parameters
- `NUM_INFERENCE_STEPS`: Quality vs speed (10-50, default: 30)
- `GUIDANCE_SCALE`: How closely to follow prompt (0-20, default: 2.5)
- `OUTPUT_FORMAT`: Image format ("png" or "jpeg")
- `RESOLUTION_MODE`: Output resolution handling

### LoRA Settings
- `LORA_URL`: Kontext LoRA model URL
- `LORA_WEIGHT`: LoRA influence strength (default: 1.0)
- `DEFAULT_PROMPT`: Default harmonization prompt

### File Management
- `OUTPUT_DIR`: Where to save processed images
- `MAX_BATCH_SIZE`: Maximum images per batch (default: 50)
- `SUPPORTED_FORMATS`: Accepted image formats

## 🖼️ Usage

### Single Image Processing
1. Go to the "Single Image" tab
2. Upload an image (JPG, PNG, WebP, BMP)
3. Optionally customize the prompt
4. Click "Harmonize Image"
5. Download or view the result

### Batch Processing
1. Go to the "Batch Processing" tab
2. Create a ZIP file with your images
3. Upload the ZIP file
4. Optionally customize the prompt
5. Click "Process Batch"
6. Download the ZIP file with processed images

### Gallery
1. Go to the "Gallery" tab
2. View all processed images
3. Click on any image to see its metadata
4. Use "Refresh Gallery" to update the view

## 🔑 API Information

This application uses the FAL.AI Flux Kontext LoRA API:
- **Endpoint**: https://fal.run/fal-ai/flux-kontext-lora
- **Model**: FLUX.1 Kontext [dev] with LoRA support
- **LoRA**: Custom harmonization model for consistent lighting and colors

## 📝 Default Prompt

The default prompt is optimized for harmonization:
```
"harmonize with consistent colours and lighting and shadows"
```

You can customize this in the interface or modify the default in `config.py`.

## 🛠️ Troubleshooting

### Common Issues

1. **"FAL_KEY not found" error**
   - Make sure you've created a `.env` file
   - Check that your API key is correctly set in `.env`

2. **Import errors**
   - Run `pip install -r requirements.txt`
   - Make sure you're using Python 3.8+

3. **API errors**
   - Verify your FAL.AI API key is valid
   - Check your internet connection
   - Ensure uploaded images are in supported formats

4. **Large file issues**
   - Check the file size limits in `config.py`
   - Reduce image resolution if needed
   - For batch processing, ensure ZIP file isn't too large

### File Formats

Supported image formats:
- JPG/JPEG
- PNG
- WebP
- BMP

### Environment Variables

#### Required Variables
- `FAL_KEY`: Your FAL.AI API key from https://fal.ai/dashboard/keys

#### Server Configuration
- `GRADIO_SERVER_NAME`: Server host (default: `0.0.0.0`)
- `GRADIO_SERVER_PORT`: Server port (default: `7860`)
- `GRADIO_SHARE`: Enable Gradio public sharing (default: `false`)
- `GRADIO_DEBUG`: Enable debug mode (default: `false`)

#### Optional Authentication
- `GRADIO_AUTH_USERNAME`: Username for basic auth (optional)
- `GRADIO_AUTH_PASSWORD`: Password for basic auth (optional)

#### Other Configuration
- `OUTPUT_DIR`: Custom output directory (default: `output`)
- `GALLERY_COLUMNS`: Gallery columns (default: `3`)
- `GALLERY_HEIGHT`: Gallery height (default: `400px`)
- `MAX_FILE_SIZE`: Max upload size (default: `50MB`)

### Performance Tips

- For faster processing, reduce `NUM_INFERENCE_STEPS` in `config.py`
- Use `ACCELERATION = "high"` for speed (may reduce quality)
- Process smaller images for faster results

## 📄 License

This project is open source. The Kontext LoRA model is provided by ShadoWxShinigamI.

## 🤝 Contributing

Feel free to submit issues and enhancement requests!
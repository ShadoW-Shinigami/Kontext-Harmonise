"""
Configuration file for Kontext-Harmonise application.
Users can modify these parameters to customize the image processing behavior.
"""

class Config:
    """Configuration class containing all API-modifiable parameters."""
    
    # API Configuration
    API_ENDPOINT = "https://fal.run/fal-ai/flux-kontext-lora"
    LORA_URL = "https://huggingface.co/ShadoWxShinigamI/harmonize/resolve/main/harmonize.safetensors"
    LORA_WEIGHT = 1.3
    
    # Default Processing Parameters
    DEFAULT_PROMPT = "harmonize with consistent colours and lighting and shadows"
    NUM_INFERENCE_STEPS = 30  # Range: 10-50
    GUIDANCE_SCALE = 2.5      # Range: 0-20
    NUM_IMAGES = 1            # Range: 1-4
    
    # Output Configuration
    OUTPUT_FORMAT = "png"     # Options: "jpeg", "png"
    RESOLUTION_MODE = "match_input"  # Options: "auto", "match_input", aspect ratios
    ENABLE_SAFETY_CHECKER = False
    SYNC_MODE = False          # False: Returns URL, True: Returns base64 data directly
    
    # Acceleration Settings
    ACCELERATION = "none"     # Options: "none", "regular", "high"
    
    # File Management
    OUTPUT_DIR = "output"
    MAX_BATCH_SIZE = 50       # Maximum number of images in batch processing
    SUPPORTED_FORMATS = [".jpg", ".jpeg", ".png", ".webp", ".bmp"]
    
    # UI Configuration
    GALLERY_COLUMNS = 3
    GALLERY_HEIGHT = "400px"
    MAX_FILE_SIZE = "50MB"
    
    @classmethod
    def get_api_payload(cls, image_b64, prompt=None):
        """Generate API payload with current configuration."""
        return {
            "image_url": f"data:image/png;base64,{image_b64}",
            "prompt": prompt or cls.DEFAULT_PROMPT,
            "num_inference_steps": cls.NUM_INFERENCE_STEPS,
            "guidance_scale": cls.GUIDANCE_SCALE,
            "num_images": cls.NUM_IMAGES,
            "output_format": cls.OUTPUT_FORMAT,
            "resolution_mode": cls.RESOLUTION_MODE,
            "enable_safety_checker": cls.ENABLE_SAFETY_CHECKER,
            "sync_mode": cls.SYNC_MODE,
            "acceleration": cls.ACCELERATION,
            "loras": [
                {
                    "path": cls.LORA_URL,
                    "scale": cls.LORA_WEIGHT
                }
            ]
        }

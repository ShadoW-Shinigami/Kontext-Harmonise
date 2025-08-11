"""
Kontext-Harmonise: A Gradio application for image harmonization using Kontext LoRA.
"""

import os
import json
import base64
import zipfile
import tempfile
import requests
import io
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any, Union
from PIL import Image
import gradio as gr
from dotenv import load_dotenv

from config import Config

load_dotenv()

class KontextHarmonise:
    def __init__(self):
        self.api_key = os.getenv("FAL_KEY")
        if not self.api_key:
            raise ValueError("FAL_KEY not found in environment variables. Please check your .env file.")
        
        self.output_dir = Path(os.getenv("OUTPUT_DIR", Config.OUTPUT_DIR))
        self.output_dir.mkdir(exist_ok=True)
        
        self.metadata_file = self.output_dir / "metadata.json"
        self.metadata = self._load_metadata()
        
        # Create zip downloads directory
        self.zip_dir = self.output_dir / "zip_downloads"
        self.zip_dir.mkdir(exist_ok=True)
        
    def _load_metadata(self) -> Dict:
        """Load existing metadata or create new."""
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, 'r') as f:
                    return json.load(f)
            except:
                return {"images": [], "next_id": 1, "zip_downloads": []}
        return {"images": [], "next_id": 1, "zip_downloads": []}
    
    def _save_metadata(self):
        """Save metadata to file."""
        with open(self.metadata_file, 'w') as f:
            json.dump(self.metadata, f, indent=2)
    
    def _get_next_filename(self) -> str:
        """Generate next sequential filename."""
        filename = f"{self.metadata['next_id']:05d}.{Config.OUTPUT_FORMAT}"
        self.metadata['next_id'] += 1
        return filename
    
    def _compress_image_quality(self, pil_image: Image.Image, quality: int) -> str:
        """Compress PIL image to base64 with specified quality."""
        # Convert to RGB if necessary (for JPEG compression)
        if pil_image.mode in ('RGBA', 'LA', 'P'):
            # Create white background
            background = Image.new('RGB', pil_image.size, (255, 255, 255))
            if pil_image.mode == 'P':
                pil_image = pil_image.convert('RGBA')
            background.paste(pil_image, mask=pil_image.split()[-1] if pil_image.mode == 'RGBA' else None)
            pil_image = background
        
        # Compress to JPEG with specified quality
        buffer = io.BytesIO()
        pil_image.save(buffer, format='JPEG', quality=quality, optimize=True)
        buffer.seek(0)
        
        return base64.b64encode(buffer.getvalue()).decode('utf-8')
    
    
    def _image_to_base64(self, image_input: Union[str, Image.Image]) -> Tuple[str, Image.Image]:
        """Convert image file or PIL Image to base64, return both base64 and PIL Image."""
        if isinstance(image_input, str):
            # Load from file path
            pil_image = Image.open(image_input)
        else:
            # Already a PIL Image
            pil_image = image_input
        
        # Start with high quality (95%)
        base64_data = self._compress_image_quality(pil_image, 95)
        return base64_data, pil_image
    
    def _is_size_error(self, error: Exception) -> bool:
        """Check if error is related to image size/payload limits."""
        error_str = str(error).lower()
        size_indicators = [
            'payload too large', 'request entity too large', '413', 'content-length',
            'image too large', 'size limit', 'timeout', 'request timeout', 
            'file size', 'maximum size', 'too big'
        ]
        return any(indicator in error_str for indicator in size_indicators)
    
    def _call_api_with_fallback(self, pil_image: Image.Image, prompt: Optional[str] = None) -> Tuple[Dict[Any, Any], str]:
        """Make API call with intelligent compression fallback."""
        headers = {
            "Authorization": f"Key {self.api_key}",
            "Content-Type": "application/json"
        }
        
        quality_levels = [95, 85, 75, 65, 50]  # Progressive compression
        compression_applied = ""
        
        for i, quality in enumerate(quality_levels):
            try:
                # Compress image at current quality level
                image_b64 = self._compress_image_quality(pil_image, quality)
                payload = Config.get_api_payload(image_b64, prompt)
                
                # Track compression for user notification
                if i > 0:  # Only notify if compression was applied
                    compression_applied = f"⚠️ Image compressed to {quality}% quality due to size limits"
                
                response = requests.post(Config.API_ENDPOINT, json=payload, headers=headers, timeout=120)
                response.raise_for_status()
                
                result = response.json()
                return result, compression_applied
                
            except Exception as e:
                if self._is_size_error(e) and i < len(quality_levels) - 1:
                    # Size error and more compression levels to try
                    continue
                else:
                    # Not a size error or no more compression levels
                    if i > 0:
                        raise Exception(f"API failed even with maximum compression: {str(e)}")
                    else:
                        raise Exception(f"API request failed: {str(e)}")
        
        raise Exception("Failed to process image even with maximum compression")
    
    def _result_to_pil_image(self, image_data: str) -> Image.Image:
        """Convert API result to PIL Image (memory-safe)."""
        try:
            if image_data.startswith('http'):
                # URL mode (async) - download from URL
                response = requests.get(image_data, timeout=30)
                response.raise_for_status()
                image_content = response.content
            elif image_data.startswith('data:image'):
                # Base64 data URL mode (sync) - decode base64
                # Format: data:image/jpeg;base64,{base64_data}
                base64_data = image_data.split(',', 1)[1]
                image_content = base64.b64decode(base64_data)
            else:
                # Raw base64 mode (sync) - decode directly
                image_content = base64.b64decode(image_data)
            
            # Load as PIL Image from memory
            image_buffer = io.BytesIO(image_content)
            pil_image = Image.open(image_buffer)
            
            # Ensure image is loaded into memory
            pil_image.load()
            
            return pil_image
            
        except Exception as e:
            raise Exception(f"Failed to load result image: {str(e)}")
    
    def _save_image_atomically(self, pil_image: Image.Image, filename: str, original_filename: str, prompt: str, compression_note: str = "") -> str:
        """Atomically save PIL image to disk with metadata."""
        output_path = self.output_dir / filename
        
        try:
            # Create temporary file for atomic operation
            with tempfile.NamedTemporaryFile(
                suffix=f'.{Config.OUTPUT_FORMAT}', 
                dir=self.output_dir, 
                delete=False
            ) as temp_file:
                pil_image.save(temp_file, format=Config.OUTPUT_FORMAT.upper(), quality=95, optimize=True)
                temp_path = temp_file.name
            
            # Atomic move to final location
            Path(temp_path).replace(output_path)
            
            # Verify file was saved correctly
            if not output_path.exists() or output_path.stat().st_size == 0:
                raise Exception("File save verification failed")
            
        except Exception as e:
            # Cleanup temporary file if it exists
            if 'temp_path' in locals() and Path(temp_path).exists():
                Path(temp_path).unlink(missing_ok=True)
            raise Exception(f"Failed to save image atomically: {str(e)}")
        
        # Save metadata
        metadata_entry = {
            "filename": filename,
            "original_filename": original_filename,
            "prompt": prompt,
            "timestamp": datetime.now().isoformat(),
            "output_path": str(output_path),
            "compression_note": compression_note
        }
        
        self.metadata["images"].append(metadata_entry)
        self._save_metadata()
        
        return str(output_path)
    
    def process_single_image(self, image_file, custom_prompt: str = "") -> Tuple[Image.Image, str, str]:
        """Process a single image with bulletproof error handling."""
        if image_file is None:
            return None, "No image uploaded.", ""
        
        try:
            # Handle image_file as filepath string (from gr.Image with type="filepath")
            image_path = image_file if isinstance(image_file, str) else image_file.name
            
            # Load image into memory
            _, pil_image = self._image_to_base64(image_path)
            
            # Use custom prompt or default
            prompt = custom_prompt.strip() or Config.DEFAULT_PROMPT
            
            # Make API call with intelligent compression fallback
            result, compression_note = self._call_api_with_fallback(pil_image, prompt)
            
            if not result.get("images"):
                return None, "No images returned from API.", ""
            
            # Convert result to PIL Image (memory-safe)
            result_image_data = result["images"][0]["url"]
            result_pil_image = self._result_to_pil_image(result_image_data)
            
            # Save to disk for gallery (atomic operation)
            original_filename = os.path.basename(image_path)
            output_filename = self._get_next_filename()
            
            self._save_image_atomically(
                result_pil_image, 
                output_filename, 
                original_filename, 
                prompt, 
                compression_note
            )
            
            # Build success message
            success_msg = f"✅ Image processed successfully!\nSaved as: {output_filename}"
            if compression_note:
                success_msg = f"{compression_note}\n{success_msg}"
            
            # Return PIL Image directly to Gradio (no file path issues)
            return result_pil_image, success_msg, self._get_gallery_data()
            
        except Exception as e:
            error_msg = f"❌ Error processing image: {str(e)}"
            return None, error_msg, ""
    
    def process_batch_images(self, zip_file, custom_prompt: str = "", progress=gr.Progress()) -> Tuple[str, str]:
        """Process a batch of images from a zip file with progress tracking."""
        if zip_file is None:
            return None, "No zip file uploaded."
        
        try:
            prompt = custom_prompt.strip() or Config.DEFAULT_PROMPT
            processed_files = []
            
            with tempfile.TemporaryDirectory() as temp_dir:
                # Handle zip_file as filepath string or file object
                zip_path = zip_file if isinstance(zip_file, str) else zip_file.name
                
                # Extract zip
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(temp_dir)
                
                # Find image files
                image_files = []
                for root, dirs, files in os.walk(temp_dir):
                    for file in files:
                        if any(file.lower().endswith(ext) for ext in Config.SUPPORTED_FORMATS):
                            image_files.append(os.path.join(root, file))
                
                if not image_files:
                    return None, "No supported image files found in zip."
                
                if len(image_files) > Config.MAX_BATCH_SIZE:
                    return None, f"Too many images. Maximum allowed: {Config.MAX_BATCH_SIZE}"
                
                # Process each image with bulletproof handling and progress tracking
                total_images = len(image_files)
                progress(0, desc=f"Starting batch processing of {total_images} images...")
                
                for i, image_path in enumerate(image_files):
                    try:
                        # Update progress
                        current_progress = (i / total_images)
                        progress(current_progress, desc=f"Processing image {i+1}/{total_images}: {os.path.basename(image_path)}")
                        
                        # Load image into memory
                        _, pil_image = self._image_to_base64(image_path)
                        
                        # Make API call with compression fallback
                        result, compression_note = self._call_api_with_fallback(pil_image, prompt)
                        
                        if result.get("images"):
                            # Convert result to PIL Image
                            result_image_data = result["images"][0]["url"]
                            result_pil_image = self._result_to_pil_image(result_image_data)
                            
                            # Save atomically
                            original_filename = os.path.basename(image_path)
                            output_filename = self._get_next_filename()
                            
                            output_path = self._save_image_atomically(
                                result_pil_image, 
                                output_filename, 
                                original_filename, 
                                prompt, 
                                compression_note
                            )
                            processed_files.append(output_path)
                            
                    except Exception as e:
                        progress(i / total_images, desc=f"Error processing {os.path.basename(image_path)}: {str(e)}")
                        continue
                
                if not processed_files:
                    return None, "No images were successfully processed."
                
                # Update progress for zip creation
                progress(0.95, desc="Creating ZIP file...")
                
                # Create output zip in zip downloads directory
                zip_filename = f"batch_output_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
                output_zip_path = self.zip_dir / zip_filename
                
                with zipfile.ZipFile(output_zip_path, 'w') as zip_out:
                    for file_path in processed_files:
                        zip_out.write(file_path, os.path.basename(file_path))
                
                # Save zip metadata
                zip_metadata = {
                    "filename": zip_filename,
                    "timestamp": datetime.now().isoformat(),
                    "file_path": str(output_zip_path),
                    "image_count": len(processed_files),
                    "prompt": prompt,
                    "original_zip": os.path.basename(zip_path)
                }
                
                if "zip_downloads" not in self.metadata:
                    self.metadata["zip_downloads"] = []
                self.metadata["zip_downloads"].append(zip_metadata)
                self._save_metadata()
                
                progress(1.0, desc="Batch processing completed!")
                
                success_msg = f"✅ Batch processing complete!\nProcessed {len(processed_files)} images.\nDownload: {zip_filename}"
                return str(output_zip_path), success_msg
                
        except Exception as e:
            error_msg = f"❌ Error processing batch: {str(e)}"
            return None, error_msg
    
    def _get_gallery_data(self) -> List[Tuple[str, str]]:
        """Get gallery data for display."""
        gallery_items = []
        for item in reversed(self.metadata["images"][-20:]):  # Show last 20 images
            if os.path.exists(item["output_path"]):
                caption = f"{item['filename']}\n{item['timestamp'][:19]}"
                if item.get('compression_note'):
                    caption += f"\n{item['compression_note']}"
                gallery_items.append((item["output_path"], caption))
        return gallery_items
    
    def _get_zip_downloads_data(self) -> List[Tuple[str, str]]:
        """Get zip downloads data for display."""
        zip_items = []
        zip_downloads = self.metadata.get("zip_downloads", [])
        
        for item in reversed(zip_downloads[-10:]):  # Show last 10 zip files
            if os.path.exists(item["file_path"]):
                caption = f"{item['filename']}\n{item['timestamp'][:19]}\n{item['image_count']} images"
                zip_items.append((item["file_path"], caption))
        
        return zip_items
    
    def get_image_metadata(self, evt: gr.SelectData) -> str:
        """Get metadata for selected gallery image."""
        try:
            # Get the selected image index
            selected_images = list(reversed(self.metadata["images"][-20:]))
            if evt.index < len(selected_images):
                item = selected_images[evt.index]
                metadata_text = f"""
**Filename:** {item['filename']}
**Original:** {item['original_filename']}  
**Prompt:** {item['prompt']}
**Timestamp:** {item['timestamp']}
**Path:** {item['output_path']}"""
                
                if item.get('compression_note'):
                    metadata_text += f"\n**Compression:** {item['compression_note']}"
                
                return metadata_text.strip()
        except:
            pass
        return "No metadata available"

def create_interface():
    """Create the Gradio interface."""
    app = KontextHarmonise()
    
    with gr.Blocks(title="Kontext-Harmonise", theme=gr.themes.Soft()) as demo:
        gr.Markdown("""
        # 🎨 Kontext-Harmonise
        
        Transform your images with **consistent colors, lighting, and shadows** using Kontext LoRA technology.
        """)
        
        with gr.Tabs():
            # Single Image Processing Tab
            with gr.Tab("🖼️ Single Image", id="single"):
                with gr.Row():
                    with gr.Column(scale=1):
                        single_input = gr.Image(
                            label="Upload Image",
                            type="filepath",
                            height=400
                        )
                        single_prompt = gr.Textbox(
                            label="Custom Prompt (optional)",
                            placeholder=Config.DEFAULT_PROMPT,
                            lines=2
                        )
                        single_process_btn = gr.Button("🎨 Harmonize Image", variant="primary")
                    
                    with gr.Column(scale=1):
                        single_output = gr.Image(label="Harmonized Image", height=400)
                        single_status = gr.Textbox(label="Status", lines=3)
                
                def handle_single_image(image_file, custom_prompt):
                    result_image, status_msg, _ = app.process_single_image(image_file, custom_prompt)
                    gallery_data = app._get_gallery_data()
                    return result_image, status_msg, gallery_data
                
                single_process_btn.click(
                    fn=handle_single_image,
                    inputs=[single_input, single_prompt],
                    outputs=[single_output, single_status, gr.State()]
                )
            
            # Batch Processing Tab
            with gr.Tab("📦 Batch Processing", id="batch"):
                with gr.Row():
                    with gr.Column():
                        batch_input = gr.File(
                            label="Upload ZIP file with images",
                            file_types=[".zip"]
                        )
                        batch_prompt = gr.Textbox(
                            label="Custom Prompt (optional)",
                            placeholder=Config.DEFAULT_PROMPT,
                            lines=2
                        )
                        batch_process_btn = gr.Button("🎨 Process Batch", variant="primary")
                    
                    with gr.Column():
                        batch_output = gr.File(label="Download Processed ZIP")
                        batch_status = gr.Textbox(label="Status", lines=5)
                
                batch_process_btn.click(
                    fn=app.process_batch_images,
                    inputs=[batch_input, batch_prompt],
                    outputs=[batch_output, batch_status]
                )
            
            # Gallery Tab
            with gr.Tab("🖼️ Gallery", id="gallery"):
                with gr.Tabs():
                    # Images Gallery
                    with gr.Tab("📷 Images", id="images_gallery"):
                        gr.Markdown("### Recently Processed Images")
                        
                        with gr.Row():
                            images_refresh_btn = gr.Button("🔄 Refresh Images")
                        
                        images_gallery = gr.Gallery(
                            label="Processed Images",
                            columns=4,
                            rows=2,
                            height="400px",
                            interactive=True,
                            allow_preview=True,
                            object_fit="contain"
                        )
                        
                        image_metadata = gr.Markdown("Select an image to view its metadata")
                        
                        images_refresh_btn.click(
                            fn=lambda: app._get_gallery_data(),
                            outputs=images_gallery
                        )
                        
                        images_gallery.select(
                            fn=app.get_image_metadata,
                            outputs=image_metadata
                        )
                    
                    # Zip Downloads Gallery  
                    with gr.Tab("📦 ZIP Downloads", id="zip_gallery"):
                        gr.Markdown("### Batch Processing Downloads")
                        
                        with gr.Row():
                            zip_refresh_btn = gr.Button("🔄 Refresh Downloads")
                        
                        zip_gallery = gr.Gallery(
                            label="ZIP Downloads",
                            columns=3,
                            rows=2,
                            height="300px",
                            interactive=True,
                            allow_preview=False,
                            object_fit="contain"
                        )
                        
                        zip_info = gr.Markdown("Select a ZIP file to see details")
                        
                        zip_refresh_btn.click(
                            fn=lambda: app._get_zip_downloads_data(),
                            outputs=zip_gallery
                        )
                
                # Load galleries on startup
                def load_galleries():
                    return app._get_gallery_data(), app._get_zip_downloads_data()
                
                demo.load(
                    fn=load_galleries,
                    outputs=[images_gallery, zip_gallery]
                )
        
        gr.Markdown("""
        ---
        **Configuration:** Check `config.py` to modify processing parameters.  
        **API Key:** Set your FAL_KEY in the `.env` file.
        """)
    
    return demo

if __name__ == "__main__":
    try:
        # Get Gradio server configuration from environment
        server_name = os.getenv("GRADIO_SERVER_NAME", "0.0.0.0")
        server_port = int(os.getenv("GRADIO_SERVER_PORT", "7860"))
        share = os.getenv("GRADIO_SHARE", "false").lower() == "true"
        debug = os.getenv("GRADIO_DEBUG", "false").lower() == "true"
        
        # Optional authentication
        auth = None
        username = os.getenv("GRADIO_AUTH_USERNAME")
        password = os.getenv("GRADIO_AUTH_PASSWORD")
        if username and password:
            auth = (username, password)
        
        demo = create_interface()
        
        print(f"🚀 Starting Kontext-Harmonise on {server_name}:{server_port}")
        if auth:
            print("🔒 Authentication enabled")
        if share:
            print("🌐 Gradio sharing enabled")
        
        demo.launch(
            server_name=server_name,
            server_port=server_port,
            share=share,
            debug=debug,
            auth=auth,
            max_file_size=Config.MAX_FILE_SIZE
        )
    except ValueError as e:
        print(f"Configuration Error: {e}")
        print("Please create a .env file with your FAL_KEY. See .env.example for template.")
    except Exception as e:
        print(f"Error starting application: {e}")
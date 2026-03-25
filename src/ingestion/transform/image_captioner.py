"""Image captioner for generating descriptions of medical images."""

import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.core.types import Chunk
from src.ingestion.transform.base_transform import BaseTransform


class ImageCaptioner(BaseTransform):
    """Generates captions for medical images referenced in chunks.

    Uses Vision LLM to describe lab reports, X-rays, and other medical images.
    """

    # Pattern to match image references in text
    IMAGE_REF_PATTERN = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)|\[image:([^\]]+)\]")

    def __init__(self, vision_llm=None):
        """Initialize the image captioner.

        Args:
            vision_llm: Vision LLM instance for image captioning.
                       If None, marks chunks for manual processing.
        """
        self.vision_llm = vision_llm

    def transform(
        self, chunks: List[Chunk], trace: Optional[Dict[str, Any]] = None
    ) -> List[Chunk]:
        """Process chunks and generate image captions.

        Args:
            chunks: List of chunks to process.
            trace: Optional trace context.

        Returns:
            List of chunks with updated image metadata.
        """
        processed_chunks = []

        for chunk in chunks:
            image_refs = self._extract_image_refs(chunk.text)

            if not image_refs:
                # No images in this chunk
                processed_chunks.append(chunk)
                continue

            if self.vision_llm:
                # Generate captions using Vision LLM
                captions = self._generate_captions(image_refs)
                chunk.metadata["image_captions"] = captions
                chunk.metadata["has_unprocessed_images"] = False
                self._update_trace(trace, "image_caption", f"captioned {len(image_refs)} images")
            else:
                # No Vision LLM, mark for manual processing
                chunk.metadata["image_refs"] = image_refs
                chunk.metadata["has_unprocessed_images"] = True
                self._update_trace(trace, "image_caption", f"marked {len(image_refs)} for manual")

            processed_chunks.append(chunk)

        return processed_chunks

    def _extract_image_refs(self, text: str) -> List[str]:
        """Extract image references from text.

        Args:
            text: Chunk text.

        Returns:
            List of image paths/URLs.
        """
        refs = []

        # Match markdown image syntax ![alt](path)
        for match in self.IMAGE_REF_PATTERN.finditer(text):
            path = match.group(2) or match.group(3)
            if path:
                refs.append(path)

        return refs

    def _generate_captions(self, image_refs: List[str]) -> Dict[str, str]:
        """Generate captions for images using Vision LLM.

        Args:
            image_refs: List of image paths.

        Returns:
            Dict mapping image path to caption.
        """
        captions = {}

        for ref in image_refs:
            try:
                # Check if it's a file path or URL
                if Path(ref).exists():
                    caption = self._caption_from_file(ref)
                else:
                    caption = self._caption_from_url(ref)

                captions[ref] = caption
            except Exception as e:
                captions[ref] = f"[Caption generation failed: {str(e)}]"

        return captions

    def _caption_from_file(self, path: str) -> str:
        """Generate caption from image file.

        Args:
            path: Path to image file.

        Returns:
            Caption string.
        """
        prompt = "请描述这张医学图像的内容，包括任何可见的异常或重要发现。"

        response = self.vision_llm.chat_with_image(text=prompt, image=path)

        return response if response else "[No caption generated]"

    def _caption_from_url(self, url: str) -> str:
        """Generate caption from image URL.

        Args:
            url: Image URL.

        Returns:
            Caption string.
        """
        prompt = "请描述这张医学图像的内容。"

        response = self.vision_llm.chat_with_image(text=prompt, image=url)

        return response if response else "[No caption generated]"

from __future__ import annotations

from PIL import Image
import hashlib
from typing import Self
import pathlib


class ImageShingle:
    """
    Image shingles are a way to compare two images for similarity. The idea is to break the image
    into chunks, compute a hash for each chunk, and then compare the hashes between images.
    This technique ignores the position of each chunk in the image.

    See https://www.usenix.org/legacy/events/sec07/tech/full_papers/anderson/anderson.pdf.
    """

    def __init__(self, image_path: str | pathlib.Path, chunk_size: int = 40):
        """
        Args:
            image_path: Path to the image.
            chunk_size: Width and height of each chunk. Default is 40.
        """
        self.chunk_size = chunk_size
        self.image = Image.open(image_path).convert("RGBA")  # Convert to RGBA mode (since we are using .png files)
        self.width, self.height = self.image.size
        self.num_chunks_x = self.width // self.chunk_size
        self.num_chunks_y = self.height // self.chunk_size

        self.chunks = self.get_chunks()
        self.shingles = self.get_shingles(self.chunks)
        self.shingle_count = self.get_shingle_count(self.shingles)

    def get_chunks(self) -> list[Image.Image]:
        """
        Return list of chunks of the image.

        Each chunk is a square of size `self.chunk_size` by `self.chunk_size`
        except possibly at the bottom and right edges.

        Returns:
            List of chunks of the image.
        """
        chunks = []

        # All full-sized chunks
        for y in range(self.num_chunks_y):
            for x in range(self.num_chunks_x):
                left = x * self.chunk_size
                upper = y * self.chunk_size
                right = left + self.chunk_size
                lower = upper + self.chunk_size

                chunk = self.image.crop((left, upper, right, lower))
                chunks.append(chunk)

        # Right side remainder
        if self.width % self.chunk_size != 0:
            for y in range(self.num_chunks_y):
                left = self.num_chunks_x * self.chunk_size
                upper = y * self.chunk_size
                right = self.width
                lower = upper + self.chunk_size
                chunk = self.image.crop((left, upper, right, lower))
                chunks.append(chunk)

        # Bottom side remainder
        if self.height % self.chunk_size != 0:
            for x in range(self.num_chunks_x):
                left = x * self.chunk_size
                upper = self.num_chunks_y * self.chunk_size
                right = left + self.chunk_size
                lower = self.height
                chunk = self.image.crop((left, upper, right, lower))
                chunks.append(chunk)

        # Bottom-right corner remainder
        if self.width % self.chunk_size != 0 and self.height % self.chunk_size != 0:
            left = self.num_chunks_x * self.chunk_size
            upper = self.num_chunks_y * self.chunk_size
            right = self.width
            lower = self.height
            chunk = self.image.crop((left, upper, right, lower))
            chunks.append(chunk)

        return chunks

    @staticmethod
    def get_shingles(chunks: list[Image.Image]) -> list[str]:
        """
        Return list of shingles of the image.

        Each shingle is the MD5 hash of a chunk.

        Args:
            chunks: Chunks of the image.

        Returns:
            Shingles of the image.
        """
        hashes = []

        for chunk in chunks:
            # Convert chunk to bytes
            chunk_bytes = chunk.tobytes()

            # Compute MD5 hash
            md5_hash = hashlib.md5()
            md5_hash.update(chunk_bytes)
            hash_value = md5_hash.hexdigest()

            hashes.append(hash_value)

        return hashes

    @staticmethod
    def get_shingle_count(shingles: list[str]) -> dict[str, int]:
        """
        Return map of shingles to counts.

        Args:
            shingles: Shingles of the image.

        Returns:
            Map of shingles to counts.
        """
        map_ = {}
        for shingle in shingles:
            if shingle not in map_:
                map_[shingle] = 0
            map_[shingle] += 1

        return map_


    @staticmethod
    def compare_with_control(baseline: ImageShingle, control: ImageShingle, experimental: ImageShingle) -> float | None:
        """
        Compare ordered shingles between baseline and experimental excluding all differences between baseline and control.

        If baseline and control are the same, then we simply return the difference between baseline and experimental.
        However, suppose baseline and control only differ in the first chunk. Then, we only compare shingles after the first
        between baseline and experimental. This way, we exclude all naturally occurring differences and only measure
        differences due to the experimental condition.

        NOTE: This is no longer a image shingle comparison since the position of each chunk matters.

        Args:
            baseline: Image without treatment.
            control: Another image without treatment.
            experimental: Image with treatment.

        Raises:
            ValueError: If the shingles do not have the same chunk size.
            ValueError: If the images are not the same size.

        Returns:
            float: Percentage difference between baseline and experimental excluding all differences between baseline and control.
            None: if there are no shingles to compare (i.e., baseline and control are completely different).
        """
        if baseline.chunk_size != control.chunk_size or baseline.chunk_size != experimental.chunk_size:
            raise ValueError("Shingles must have the same chunk size.")

        if len(baseline.image.size) != len(control.image.size) or len(baseline.image.size) != len(experimental.image.size):
            raise ValueError("Images must have the same size.")

        if len(baseline.shingles) != len(control.shingles) or len(baseline.shingles) != len(experimental.shingles):
            raise ValueError("Images must have the same number of shingles.")

        matches = 0
        total = 0

        for baseline_shingle, control_shingle, experimental_shingle in zip(baseline.shingles, control.shingles, experimental.shingles):
            if baseline_shingle == control_shingle:
                total += 1
                if baseline_shingle == experimental_shingle:
                    matches += 1

        # Baseline and control are completely different
        if total == 0:
            raise ValueError("No comparisons can be made.")

        similarity = matches / total
        return 1 - similarity

    @staticmethod
    def compare_with_controls(baseline: ImageShingle, controls: list[ImageShingle], experimental: ImageShingle) -> float | None:
        """
        Implements compare_with_control for multiple controls.

        The union of differences between each control with the baseline is excluded from the comparison between baseline and experimental.

        Args:
            baseline: Image without treatment.
            controls: More images without treatment.
            experimental: Image with treatment.

        Raises:
            ValueError: If the shingles do not have the same chunk size.
            ValueError: If the images are not the same size.

        Returns:
            float: Percentage difference between baseline and experimental excluding all (unioned) differences 
            between baseline and the controls. -1 if there are no shingles to compare 
            None: if there are no shingles to compare
        """
        if baseline.chunk_size != experimental.chunk_size:
            raise ValueError("Shingles must have the same chunk size.")

        if len(baseline.image.size) != len(experimental.image.size):
            raise ValueError("Images must have the same size.")

        matches = 0
        total = 0

        excluded_indices = set()
        for control in controls:
            if baseline.chunk_size != control.chunk_size:
                raise ValueError("Shingles must have the same chunk size.")
            if len(baseline.image.size) != len(control.image.size):
                raise ValueError("Images must have the same size.")
            
            for i, baseline_shingle in enumerate(baseline.shingles):
                if baseline_shingle != control.shingles[i]:
                    excluded_indices.add(i)
        
        for i, baseline_shingle in enumerate(baseline.shingles):
            if i in excluded_indices:
                continue

            total += 1
            if baseline_shingle == experimental.shingles[i]:
                matches += 1

        # Baseline and control are completely different
        if total == 0:
            return None

        similarity = matches / total
        return 1 - similarity

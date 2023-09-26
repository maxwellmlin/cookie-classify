from __future__ import annotations

from PIL import Image
import hashlib
from typing import Self


class ImageShingle:
    """
    Image shingles are a way to compare two images for similarity. The idea is to break the image
    into chunks, compute a hash for each chunk, and then compare the hashes between images.

    See https://www.usenix.org/legacy/events/sec07/tech/full_papers/anderson/anderson.pdf.
    """

    def __init__(self, image_path: str, chunk_size: int):
        """
        Args:
            image_path: Path to the image.
            chunk_size: Width and height of each chunk.
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

    def compare(self, other_shingles: Self) -> float:
        """
        Compare two shingles and return the percentage of matches.

        Args:
            other_shingles: Another set of shingles.

        Raises:
            ValueError: If the images are not the same size.
            ValueError: If the shingles do not have the same chunk size.

        Returns:
            Percentage of shingles that match.
        """
        if self.chunk_size != other_shingles.chunk_size:
            raise ValueError("Shingles must have the same chunk size.")

        matches = 0

        for shingle, count in self.shingle_count.items():
            if shingle in other_shingles.shingle_count:
                matches += min(count, other_shingles.shingle_count[shingle])  # Add the number of matches

        return matches / max(len(self.shingles), len(other_shingles.shingles))  # Return the percentage of matches

    @staticmethod
    def compare_with_control(baseline: ImageShingle, control: ImageShingle, experimental: ImageShingle) -> float:
        """
        Compare shingles between baseline and experimental excluding all differences between baseline and control.

        I.e., if baseline and control are the same, then we simply return the similarity between baseline and experimental.
        However, suppose baseline and control differ in the first shingle. Then, we only compare all shingles > 1 between
        baseline and experimental.
        NOTE: This is no longer a true Image Shingle comparison since the position of each shingle matters.

        Args:
            baseline: Image baseline.
            control: Image without treatement.
            experimental: Image with treatment.

        Raises:
            ValueError: If the shingles do not have the same chunk size.
            ValueError: If the images are not the same size.

        Returns:
            float: Percentage similarity between baseline and experimental excluding all differences between baseline and control.
            -1 if there are no shingles to compare (i.e., baseline and control are completely different)
        """
        if baseline.chunk_size != control.chunk_size or baseline.chunk_size != experimental.chunk_size:
            raise ValueError("Shingles must have the same chunk size.")

        if len(baseline.image.size) != len(control.image.size) or len(baseline.image.size) != len(experimental.image.size):
            raise ValueError("Images must have the same size.")

        matches = 0
        total = 0

        for i, baseline_shingle in enumerate(baseline.shingles):
            if baseline_shingle == control.shingles[i]:
                total += 1
                if baseline_shingle == experimental.shingles[i]:
                    matches += 1

        # Baseline and control are completely different
        if total == 0:
            return -1

        similarity = matches / total
        return similarity

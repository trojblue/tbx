import os
import math
import shutil
from PIL import Image
from pathlib import Path
from tqdm.auto import tqdm

import unibox
from unibox import UniLoader, UniLogger

from concurrent.futures import ProcessPoolExecutor, as_completed
from typing import List, Tuple


class ImageResizer:

    TRUNCATE_MULTIPLIER = 32  # the shorter side will be a multiple of 32 after scaling
    WEBP_QUALITY = 98  # quality of the output image (max:100)
    EXTENSION = ".webp"  # file extension (.webp)

    def __init__(self, root_dir: str, dst_dir: str,
                 min_dim: int = None, max_dim: int = None, target_pixels: int = None,
                 keep_hierarchy: bool = True, exist_ok: bool = True, logger: UniLogger = None):
        """
        Initialize an instance of ImageResizer.

        :param root_dir: root directory containing the images to be resized
        :param dst_dir: destination directory to save the resized images
        :param min_dim: minimum dimension of the shorter side
        :param max_dim: maximum dimension of the longer side (higher priority than min_dim)
        :param target_pixels: target number of pixels (higher priority than max_dim), will be truncated
        :param keep_hierarchy: if True, keep the original directory hierarchy; otherwise, flatten the directory
        """
        self.root_dir = root_dir
        self.dst_dir = dst_dir

        self.min_dim = min_dim
        self.max_dim = max_dim
        self.target_pixels = target_pixels

        self.keep_hierarchy = keep_hierarchy
        self.exist_ok = exist_ok

        self.logger = logger if logger is not None else UniLogger()

    @staticmethod
    def _get_new_dimensions(width: int, height: int, target_side: int, resize_by_longer_side: bool = False) -> tuple:
        """
        Calculates new dimensions based on the target,
        for either the shorter or longer side while maintaining aspect ratio.

        :param width: original width of the image
        :param height: original height of the image
        :param target_side: target dimension for the side specified
        :param resize_by_longer_side: if True, resize by longer side; otherwise, by shorter side
        :return: tuple containing new dimensions (new_width, new_height)
        """
        if target_side == -1:
            return int(width), int(height)

        if any(x <= 0 or type(x) != int for x in [width, height, target_side]):
            raise ValueError("width, height and target_side must be positive integers")

        # Determine shorter and longer side
        shorter_side, longer_side = min(width, height), max(width, height)

        if resize_by_longer_side:
            target_longer_side = target_side
            new_longer_side = target_longer_side
            new_shorter_side = round(new_longer_side * (shorter_side / longer_side))
        else:
            target_shorter_side = target_side
            new_shorter_side = target_shorter_side
            new_longer_side = round(new_shorter_side * (longer_side / shorter_side))

        # Assign new dimensions based on original orientation (portrait or landscape)
        if width > height:
            return new_longer_side, new_shorter_side
        else:
            return new_shorter_side, new_longer_side

    def _get_dst_path(self, og_rel_image_path: str) -> str:
        """
        :param og_rel_image_path: original relative image path
        """
        assert self.EXTENSION.startswith(".") and self.EXTENSION != ".", "extension must start with a dot"

        og_rel_path = Path(og_rel_image_path)
        rel_resized_path = og_rel_path.with_name(f"{og_rel_path.stem}_resized{self.EXTENSION}")

        if self.keep_hierarchy:
            dst_file_path = Path(self.dst_dir) / rel_resized_path

        else:
            dst_file_path = Path(self.dst_dir) / rel_resized_path.name

        return str(dst_file_path)

    def _create_dst_dir(self, dst_file_path: str) -> None:
        Path(dst_file_path).parent.mkdir(parents=True, exist_ok=True)

    def _resize_image(self, image: Image.Image) -> Image.Image:
        """
        输入PIL Image对象，输出resize之后的 PIL Image

        :param image: PIL.Image.Image object to be resized
        :return: PIL.Image.Image object after resizing
        """

        width, height = image.size
        new_width, new_height = width, height

        # Define the need_resize variable
        need_resize = (self.min_dim is not None and min(width, height) < self.min_dim) or \
                      (self.max_dim is not None and max(width, height) > self.max_dim)

        # Priority 1: Resize based on target_pixels
        if self.target_pixels is not None:
            scale_factor = math.sqrt(self.target_pixels / (width * height))
            target_shorter_side = round(
                (min(width, height) * scale_factor) // self.TRUNCATE_MULTIPLIER) * self.TRUNCATE_MULTIPLIER
            new_width, new_height = self._get_new_dimensions(width, height, target_shorter_side)

        # Priority 2: Resize based on max_dim
        elif self.max_dim is not None and need_resize:
            new_width, new_height = self._get_new_dimensions(width, height, self.max_dim, resize_by_longer_side=True)

        # Priority 3: Resize based on min_dim
        elif self.min_dim is not None and need_resize:
            new_width, new_height = self._get_new_dimensions(width, height, self.min_dim)

        # If resizing is not needed, return the original image
        elif not need_resize:
            return image

        # Perform the resize operation
        return image.resize((new_width, new_height), Image.LANCZOS)

    def _resize_single_image_task(self, og_rel_image_path: str) -> None:
        """
        Resize a single image and save the result.

        :param og_rel_image_path: original image path relative to self.root_dir
        """
        loader = UniLoader(debug_print=False)
        image = loader.loads(os.path.join(self.root_dir, og_rel_image_path))
        image = self._resize_image(image)

        # Handle save path
        dst_file_path = self._get_dst_path(og_rel_image_path)

        # Create destination directory
        if self.keep_hierarchy:
            self._create_dst_dir(dst_file_path)

        # Save
        try:
            with open(dst_file_path, "wb") as f:
                image.save(f, "webp", quality=self.WEBP_QUALITY)
        except OSError:
            print(f"Error saving image {dst_file_path}. Skipping...")

    @staticmethod
    def _execute_resize_tasks(tasks: List[Tuple]):
        """
        Execute tasks using ProcessPoolExecutor
        """
        with ProcessPoolExecutor() as executor:
            futures = [executor.submit(task, *args) for task, *args in tasks]
            list(tqdm(as_completed(futures), total=len(tasks), desc="Resizing images"))

    def resizer_sketch(self):

        image_files = unibox.traverses(self.root_dir, include_extensions=unibox.constants.IMG_FILES, relative_unix=True)

        if self.exist_ok:
            existing_files = unibox.traverses(self.dst_dir, include_extensions=unibox.constants.IMG_FILES, relative_unix=False)
            expected_files = [self._get_dst_path(og_rel_image_path) for og_rel_image_path in image_files]
            image_files = list(set(expected_files) - set(existing_files))

        tasks = [(self._resize_single_image_task, og_rel_image_path) for og_rel_image_path in image_files]

        self._execute_resize_tasks(tasks)


if __name__ == '__main__':
    root_dir = r"E:\_benchmark\1k"
    dst_dir = r"E:\_benchmark\1k_resized"

    min_dim = 512
    max_dim = int(1024 * 3)
    target_pixels = int(1024 * 1024 * 1.25)

    resizer = ImageResizer(root_dir, dst_dir, min_dim=min_dim, max_dim=max_dim, target_pixels=target_pixels,
                           keep_hierarchy=False, exist_ok=True)
    resizer.resizer_sketch()

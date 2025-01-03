from __future__ import annotations


from doctest import debug
from pathlib import Path
from typing import Union, List, Dict, Any

from .utils.uni_loader import UniLoader, concurrent_loads
from .utils.uni_logger import UniLogger
from .utils.uni_saver import UniSaver
from .utils.uni_traverser import UniTraverser
from .utils.uni_traverser import traverses as _onestep_traverse
from .utils.uni_resizer import UniResizer
from .utils.uni_merger import UniMerger
from .utils.uni_peeker import UniPeeker
from .utils.utils import is_s3_uri, is_url
from .utils import constants    # from unibox.constants import IMG_FILES
from .utils.constants import *  # import unibox.IMG_FILES

# global s3 client
from .utils.s3_client import S3Client
s3_client = S3Client()

# from .utils.ipython_utils import gallery
try:
    from .utils.ipython_utils import gallery
    from .utils.ipython_utils import label_gallery
except (ImportError, ModuleNotFoundError):
    print("IPython is not available. Gallery function will not work.")

    def gallery(paths: list[str], labels: list[str] = [], 
                row_height='300px', num_workers=32, debug_print=True, thumbnail_size: int = 512):
        print("IPython is not available. Gallery function will not work.")

    def label_gallery(paths: list[str], labels: list[str] = [], 
                                row_height='150px', num_workers=32, debug_print=True, thumbnail_size: int = 512):
        print("IPython is not available. Gallery function will not work.")


def loads(file_path: str | Path, debug_print=True) -> any:
    """
    Loads arbitrary data from the given file path, using UniLoader.loads() method.
    :param file_path: Path to the file to load.
    :param debug_print: Whether to print debug messages. (advised to turn off if loading many files)

    example:
    >>> df = unibox.loads("data.csv")
    >>> json_dict_list = unibox.loads("data.jsonl")
    >>> pil_iimage = unibox.loads("image.png")
    """
    loader = UniLoader(debug_print=debug_print)
    return loader.loads(file_path)


def saves(data: Any, file_path: Path | str, debug_print=True) -> None:
    """
    Saves arbitrary data to the given file path, using the UniSaver.saves() method.
    :param data: The data to saves.
    :param file_path: Path to the file to saves.

    example:
    >>> json_dict = {"name": "John", "age": 30}
    >>> unibox.saves(json_dict, "data.json")
    >>> json_dict_list = [{"name": "John", "age": 30}, {"name": "Doe", "age": 40}]
    >>> unibox.saves(json_dict_list, "data.jsonl")
    >>> df = pd.DataFrame({'A': [1, 2], 'B': [3, 4]})
    >>> unibox.saves(df, "data.parquet")
    >>> pil_image = Image.new('RGB', (60, 30), color='red')
    >>> unibox.saves(pil_image, "image.png")
    """
    saver = UniSaver(debug_print=debug_print)
    saver.saves(data, str(file_path))


def traverses(root_dir: str, include_extensions: List[str] = None,
              exclude_extensions: List[str] = None, relative_unix=False, debug_print=True) -> List[str]:
    """

    Args:
        root_dir: the root s3_uri to traverse
        include_extensions: list of extensions that will be included in the traversal (.txt .jpg .webp)
        exclude_extensions: list of extensions that will be excluded in the traversal (.txt .jpg .webp)
        relative_unix: whether to give a relative path or not (default False gives absolute path)

    Returns:
        list of files that were traversed
    """

    if is_s3_uri(root_dir):
        # either files or folders
        all_entries = s3_client.traverse(root_dir, include_extensions, exclude_extensions, relative_unix, debug_print)
    else:
        all_entries = _onestep_traverse(root_dir, include_extensions, exclude_extensions, relative_unix, debug_print)

    return all_entries


def ls(root_dir: str, exts: List[str] = None,
              excludes: List[str] = None, relative=False, debug_print=True) -> List[str]:
    """
    Wrapper function that calls ub.traverses() function

    Args:
        root_dir: the root s3_uri to traverse
        exts: list of extensions that will be included in the traversal (.txt .jpg .webp)
        excludes: list of extensions that will be excluded in the traversal (.txt .jpg .webp)
        relative: whether to give a relative path or not (default False gives absolute path)

    Returns:
        list of files that were traversed
    """
    return traverses(root_dir=root_dir, include_extensions=exts, exclude_extensions=excludes, 
                     relative_unix=relative, debug_print=debug_print)


def merges(*data: Union[str, Dict, List[Any], Any]) -> Any:
    """
    Merges arbitrary data using UniMerger.merges() method.
    :param data: A variable number of data entries to merge. Each entry can be a dictionary, a list, a dataframe, or a string representing a file path.
    :param debug_print: Whether to print debug messages. (advised to turn off if merging many data entries)
    :return: Merged data
    example:
    >>> merged_dict = merges(dict1, dict2, dict3)
    >>> merged_df = merges(df1, df2, df3)
    >>> merged_data_from_files = merges("data1.csv", "data2.json", "data3.parquet")
    """
    merger = UniMerger()
    return merger.merges(*data)


def peeks(data: Any, n=3, console_print=False) -> Dict[str, Any]:
    """
    Peeks into arbitrary data using UniPeeker.peeks() method.
    :param data: The data to peek into.
    :param n: The number of entries to peek into.
    :param console_print: Whether to print the peeked information to the console.
    :return: A dictionary containing the metadata and the preview of the data.
    example:
    >>> json_dict = {"name": "John", "age": 30}
    >>> peeked_dict = peeks(json_dict)
    >>> json_dict_list = [{"name": "John", "age": 30}, {"name": "Doe", "age": 40}]
    >>> peeked_dict_list = peeks(json_dict_list)
    >>> df = pd.DataFrame({'A': [1, 2], 'B': [3, 4]})
    >>> peeked_df = peeks(df)
    """
    peeker = UniPeeker(n, console_print)
    return peeker.peeks(data)


def presigns(s3_uri: str, expiration: Union[int, str] = "1d") -> str:
    """
    Generate a presigned URL from a given S3 URI.
    :param s3_uri: S3 URI (e.g., 's3://bucket-name/object-key')
        :param expiration: Time in seconds for the presigned URL to remain valid (default: 1 day).
                        Accepts either an integer (seconds) or human-readable strings like "1d", "1mo", "1y".
    :return: Presigned URL as string. If error, returns None.
    """
    return s3_client.generate_presigned_uri(s3_uri, expiration=expiration)
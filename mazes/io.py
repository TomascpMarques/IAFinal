from enum import Enum

from fs import open_fs
from fs.osfs import OSFS
from option import Result, Err, Ok


class MazeFileExtensions(Enum):
    LONG = ".maze"
    SHORT = ".mz"

    def __str__(self):
        return str(self)


class MazeFileIOErrors(Enum):
    NotAMazeFile = "The given file is not a maze: {path}"

    # def to_str(self, **kwargs) -> str:
    #     return str(self).format(kwargs)


def read_from_file(file_name: str, folder_path: str) -> Result[list[list[str]], str]:
    if not (file_name.endswith(".maze") or file_name.endswith(".mz")):
        return Err(str(MazeFileIOErrors.NotAMazeFile))

    content: str = ""
    cwd_fs = OSFS(folder_path)
    with cwd_fs.open(path=file_name, mode="r") as maze_file:
        content = maze_file.read()
        rows = content.splitlines()
        final = [i.split(" ") for i in rows]
        return Ok(final)


if __name__ == "__main__":
    c = read_from_file("test_1.mz", "/home/ninbo/ws/python/ai/final_project/resources")
    print(c)
